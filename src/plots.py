"""
Plotting functions for Plasmopy.

Three distinct visualisations are produced at the end of each model run:

plot_infection_events_pdf
    Matplotlib PDF — scatter plot of every infection-stage datetime across the
    full season.  Quick overview for developers; not mobile-optimised.

plot_model_infection_chains
    Plotly interactive HTML — detailed chain view linking all infection stages
    per event (germination → dispersion → infection → incubation → sporulation
    → secondary infection).  Chains triggered by the spore-driven model
    shortcut are drawn in red.

plot_spore_driven_model_overview
    Plotly interactive HTML — daily spore-count bars with colour-coded day
    backgrounds that reflect the INTEGRATED model outcome.  Background colour
    is set by the combination of spore-count conditions AND mechanistic model
    infection events (red = both; yellow = one; green = neither; grey =
    missing spore data).  This plot is the visual output of the spore_driven_model
    algorithm: spore counts are actively fed into the model to trigger shortcuts.

plot_risk_heatmap
    Plotly interactive HTML (smartphone-optimised) — three independent rows:
      Modèle   – mechanistic model infection strength per day (°C·h)
      Mildiou  – spore trap count per day
      Risque   – display-only product of the two; NOT used in the algorithm
    Colour thresholds come from config.risk_heatmap so they can be tuned
    without touching code.

write_combined_html
    Combines plot_risk_heatmap (primary view) and plot_model_infection_chains
    (secondary view) into a single mobile-friendly HTML with a toggle button.
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# PDF — infection event scatter (matplotlib)
# ---------------------------------------------------------------------------


def plot_infection_events_pdf(infection_events, model_parameters, pdf_path):
    """
    Matplotlib PDF scatter plot of all infection-stage datetimes across the season.

    Each stage is shown at a fixed y-level; optional spore counts are overlaid
    on a secondary right-hand axis.
    """
    # Stages in model order: (event key, legend label, colour, y-rank)
    STAGES = [
        ("oospore_germination", "germination", "lightgreen", 1),
        ("oospore_dispersion", "dispersion", "orange", 2),
        ("oospore_infection", "primary infection", "red", 3),
        ("completed_incubation", "completed incubation", "green", 4),
        ("sporulations", "sporulation", "violet", 5),
        ("secondary_infections", "secondary infection", "purple", 6),
    ]

    # --- optional spore counts ---
    spore_df = _load_daily_spore_counts(model_parameters)

    # y-scale: align event markers with spore count magnitude when available
    y_scale = (spore_df["count"].max() / len(STAGES)) if spore_df is not None else 1.0

    # --- collect unique datetimes per stage ---
    stage_dates: dict = {key: set() for key, *_ in STAGES}
    for event in infection_events:
        for key, *_ in STAGES:
            value = event.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                stage_dates[key].update(value)
            else:
                stage_dates[key].add(value)

    # --- build figure ---
    fig, ax = plt.subplots(figsize=(14, 6))

    for key, label, colour, rank in STAGES:
        dates = sorted(stage_dates[key])
        ax.plot(
            dates,
            [rank * y_scale] * len(dates),
            marker="o",
            linestyle="",
            alpha=0.4,
            color=colour,
            label=label,
        )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    ax.tick_params(axis="x", labelsize=5)
    ax.tick_params(left=False, right=False, labelleft=False)
    ax.set_title(model_parameters["input_data"]["meteo"] or "automated pull")
    ax.grid(True)
    fig.autofmt_xdate()

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.4, -0.01),
        bbox_transform=fig.transFigure,
        ncol=3,
    )

    if spore_df is not None:
        ax2 = ax.twinx()
        ax2.plot(
            spore_df["date"],
            spore_df["count"],
            linestyle="--",
            alpha=0.4,
            color="steelblue",
            label="spore counts",
        )
        ax2.tick_params(right=True, labelright=True)
        ax2.legend(
            loc="lower center",
            bbox_to_anchor=(0.8, -0.01),
            bbox_transform=fig.transFigure,
        )

    fig.savefig(pdf_path)
    plt.close(fig)


def _load_daily_spore_counts(model_parameters):
    """Load and aggregate spore counts to daily totals. Returns a DataFrame or None."""
    path = model_parameters["input_data"]["spore_counts"]
    if path is None:
        return None
    try:
        sc = pd.read_csv(path, sep=";")
        date_col, count_col = sc.columns[0], sc.columns[1]
        sc[date_col] = pd.to_datetime(
            sc[date_col],
            format=model_parameters["data_columns"]["format_columns"][0],
        )
        daily = (
            sc.groupby(sc[date_col].dt.date)[count_col]
            .sum()
            .reset_index()
            .rename(columns={date_col: "date", count_col: "count"})
        )
        daily["date"] = pd.to_datetime(daily["date"])
        return daily
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Plotly — detailed infection chain view (model output, developer view)
# ---------------------------------------------------------------------------


def plot_model_infection_chains(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_path=None,
    title="Infection analysis",
):
    """
    Interactive HTML plot reproducing the Rplot.R visualisation.

    Layout:
      - Dark-blue vertical bars for sporangia density at each sporulation datetime.
      - Green square at oospore maturation (y=0).
      - Per-infection-chain dotted lines connecting event stages.
      - Chains triggered by the spore-driven model shortcut are drawn in red.
      - Daily spore counts as light-blue bars on the right y-axis.
    """
    df = pd.read_csv(events_dataframe_path)

    dt_cols = [
        "start",
        "oospore_maturation",
        "oospore_germination",
        "oospore_dispersion",
        "oospore_infection",
        "completed_incubation",
        "sporulations",
        "secondary_infections",
    ]
    for col in dt_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    if "sporangia_densities" in df.columns:
        df["sporangia_densities"] = pd.to_numeric(
            df["sporangia_densities"], errors="coerce"
        )

    # Spore-driven model shortcut detection:
    # skip_to_dispersion : germination=NaN, dispersion=not NaN
    # skip_to_sporulation: germination=NaN, sporulations=not NaN
    df["_shortcut"] = df["oospore_germination"].isna() & (
        df["oospore_dispersion"].notna() | df["sporulations"].notna()
    )

    max_density = (
        float(model_parameters["sporangia"]["max_density"])
        if model_parameters is not None
        else 360_000
    )

    _event_keys = [
        "oospore_germination",
        "oospore_dispersion",
        "oospore_infection",
        "completed_incubation",
        "sporulations",
        "secondary_infections",
    ]
    _step = max_density / (len(_event_keys) - 1)
    event_y = {col: round(i * _step) for i, col in enumerate(_event_keys)}
    event_symbols = {
        "oospore_germination": "circle",
        "oospore_dispersion": "triangle-up",
        "oospore_infection": "cross",
        "completed_incubation": "x",
        "sporulations": "triangle-down",
        "secondary_infections": "diamond",
    }
    event_labels = {
        "oospore_germination": "germination",
        "oospore_dispersion": "dispersion",
        "oospore_infection": "primary infection",
        "completed_incubation": "completed incubation",
        "sporulations": "sporulation",
        "secondary_infections": "secondary infection",
    }

    fig = go.Figure()

    if model_parameters is not None:
        spore_path = spore_counts_path or model_parameters["input_data"]["spore_counts"]
        if spore_path:
            try:
                sc = pd.read_csv(spore_path, sep=";")
                _dc, _cc = sc.columns[0], sc.columns[1]
                fmt = model_parameters["data_columns"]["format_columns"][0]
                sc[_dc] = pd.to_datetime(sc[_dc], format=fmt, errors="coerce")
                sc = sc.groupby(sc[_dc].dt.date)[_cc].sum().reset_index()
                sc.columns = [_dc, _cc]
                sc[_dc] = pd.to_datetime(sc[_dc])
                fig.add_trace(
                    go.Bar(
                        x=sc[_dc],
                        y=sc[_cc],
                        name="daily spore counts",
                        marker_color="lightsteelblue",
                        opacity=0.45,
                        yaxis="y2",
                    )
                )
            except Exception:
                pass

    spor = df[df["sporangia_densities"].notna() & df["sporulations"].notna()]
    if not spor.empty:
        x_bars, y_bars = [], []
        for _, row in spor.iterrows():
            x_bars += [row["sporulations"], row["sporulations"], None]
            y_bars += [0, row["sporangia_densities"], None]
        fig.add_trace(
            go.Scatter(
                x=x_bars,
                y=y_bars,
                mode="lines",
                line={"color": "darkblue", "width": 2},
                name="sporangia density",
                yaxis="y3",
            )
        )

    mat = df["oospore_maturation"].dropna()
    if not mat.empty:
        fig.add_trace(
            go.Scatter(
                x=[mat.iloc[0]],
                y=[0],
                mode="markers",
                marker={
                    "symbol": "arrow-down",
                    "color": "#3cb371",
                    "size": 18,
                    "opacity": 1,
                },
                name="maturation",
            )
        )

    event_cols_ordered = list(event_y.keys())
    _chain_legend = {
        False: "normal model event",
        True: "spore count condition (shortcut)",
    }
    for shortcut_flag, color in [(False, "black"), (True, "red")]:
        group = df[df["_shortcut"] == shortcut_flag]
        if group.empty:
            continue
        x_lines, y_lines = [], []
        for _, row in group.iterrows():
            for col in event_cols_ordered:
                val = row.get(col)
                if pd.notna(val):
                    x_lines.append(val)
                    y_lines.append(event_y[col])
            x_lines.append(None)
            y_lines.append(None)
        fig.add_trace(
            go.Scatter(
                x=x_lines,
                y=y_lines,
                mode="lines",
                line={"color": color, "width": 0.5, "dash": "dot"},
                name=_chain_legend[shortcut_flag],
                legendgroup=_chain_legend[shortcut_flag],
                hoverinfo="skip",
            )
        )

    for col in event_cols_ordered:
        for shortcut_flag, color in [(False, "black"), (True, "red")]:
            col_df = df[df[col].notna() & (df["_shortcut"] == shortcut_flag)]
            if col_df.empty:
                continue
            label = event_labels[col]
            fig.add_trace(
                go.Scatter(
                    x=col_df[col],
                    y=[event_y[col]] * len(col_df),
                    mode="markers",
                    marker={"symbol": event_symbols[col], "size": 8, "color": color},
                    name=label,
                    legendgroup=_chain_legend[shortcut_flag],
                    showlegend=False,
                    hovertemplate="%{x}<extra>" + label + "</extra>",
                )
            )

    fig.update_layout(
        title=title,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"title": "", "tickformat": "%b %d", "tickangle": -90, "showgrid": True},
        yaxis={
            "title": "",
            "range": [-max_density * 0.04, max_density * 1.08],
            "showticklabels": False,
            "showgrid": True,
        },
        yaxis2={
            "title": "Daily spore counts",
            "overlaying": "y",
            "side": "right",
            "showticklabels": True,
            "showgrid": False,
        },
        yaxis3={
            "title": {
                "text": "Leaf sporangia density [sporangia / cm²]",
                "font": {"color": "darkblue"},
            },
            "overlaying": "y",
            "side": "left",
            "autoshift": True,
            "range": [-max_density * 0.04, max_density * 1.08],
            "tickcolor": "darkblue",
            "tickfont": {"color": "darkblue"},
            "showgrid": False,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        bargroupgap=0,
    )
    fig.update_xaxes(rangeslider_visible=True)
    fig.write_html(output_html_path)
    return fig


# ---------------------------------------------------------------------------
# Plotly — spore-driven model overview (integrated model output)
# ---------------------------------------------------------------------------


def plot_spore_driven_model_overview(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_result=None,
    spore_counts_path=None,
    title="Spore counts & infection overview",
):
    """
    Interactive HTML overview showing daily spore counts with day-level
    background colours that reflect the INTEGRATED (spore-driven) model outcome.

    This plot is the visual companion to the spore_driven_model algorithm:
    spore counts are fed into the model as algorithmic shortcuts.  Background
    colour encodes the combined state of spore-count conditions AND mechanistic
    model infection events:
      Red    – both a spore-count condition AND a model infection event on that day.
      Yellow – one of the two conditions met, but not both.
      Green  – spore data present, neither condition met.
      Grey   – spore data missing for that day.
    """
    import datetime as _dt

    df = pd.read_csv(events_dataframe_path)

    dt_cols = [
        "start",
        "oospore_dispersion",
        "oospore_infection",
        "sporulations",
        "secondary_infections",
    ]
    for col in dt_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    sc_x, sc_y = [], []
    sc_days: set = set()
    spore_path = spore_counts_path or (
        model_parameters["input_data"]["spore_counts"]
        if model_parameters is not None
        else None
    )
    if spore_path:
        try:
            sc = pd.read_csv(spore_path, sep=";")
            _dc, _cc = sc.columns[0], sc.columns[1]
            fmt = (
                model_parameters["data_columns"]["format_columns"][0]
                if model_parameters is not None
                else "%d.%m.%Y %H:%M"
            )
            sc[_dc] = pd.to_datetime(sc[_dc], format=fmt, errors="coerce")
            sc = sc.groupby(sc[_dc].dt.date)[_cc].sum().reset_index()
            sc.columns = [_dc, _cc]
            sc[_dc] = pd.to_datetime(sc[_dc]) + pd.Timedelta(hours=12)
            sc_x = sc[_dc].tolist()
            sc_y = sc[_cc].tolist()
            sc_days = {ts.date() for ts in sc_x}
        except Exception:
            pass

    infection_dates: set = set()
    for col in ("oospore_infection", "secondary_infections"):
        if col in df.columns:
            infection_dates |= {ts.date() for ts in df[col].dropna()}

    condition_dates: set = set()
    if spore_counts_result:
        for raw in spore_counts_result.get("dispersion_datetimes", []):
            condition_dates.add(pd.Timestamp(raw).date())
        for raw in spore_counts_result.get("sporulation_datetimes", []):
            condition_dates.add(pd.Timestamp(raw).date())

    grey_days: set = set()
    if sc_days:
        range_start = min(sc_days)
        if "start" in df.columns and df["start"].notna().any():
            col_start = df["start"].dropna().min().date()
            range_start = min(range_start, col_start)
        df_dates = []
        for col in dt_cols:
            if col in df.columns:
                df_dates += [ts.date() for ts in df[col].dropna()]
        all_endpoint_dates = (
            list(infection_dates) + [ts.date() for ts in sc_x] + df_dates
        )
        range_end = max(all_endpoint_dates) if all_endpoint_dates else max(sc_days)
        cur = range_start
        while cur <= range_end:
            if cur not in sc_days:
                grey_days.add(cur)
            cur += _dt.timedelta(days=1)

    red_days = infection_dates & condition_dates
    yellow_days = (infection_dates | condition_dates) - red_days
    effective_grey = grey_days - red_days - yellow_days
    green_days = sc_days - red_days - yellow_days

    today = _dt.date.today()
    _color_opacity_hist = {"red": 0.6, "yellow": 0.45, "grey": 0.35, "green": 0.45}
    _color_opacity_fcst = {"red": 0.35, "yellow": 0.25, "grey": 0.2, "green": 0.25}
    day_color = (
        {d: "red" for d in red_days}
        | {d: "yellow" for d in yellow_days}
        | {d: "grey" for d in effective_grey}
        | {d: "green" for d in green_days}
    )

    fig = go.Figure()

    if day_color:
        sorted_days = sorted(day_color)
        group_start = sorted_days[0]
        group_col = day_color[sorted_days[0]]
        group_is_fcst = sorted_days[0] > today
        for day in sorted_days[1:] + [None]:
            next_col = day_color.get(day) if day is not None else None
            next_is_fcst = (day > today) if day is not None else None
            idx = sorted_days.index(day) if day is not None else len(sorted_days)
            consecutive = (
                day is not None
                and (day - sorted_days[idx - 1]) == _dt.timedelta(days=1)
                and next_col == group_col
                and next_is_fcst == group_is_fcst
            )
            if not consecutive:
                end_day = sorted_days[idx - 1] if day is not None else sorted_days[-1]
                opacity_map = (
                    _color_opacity_fcst if group_is_fcst else _color_opacity_hist
                )
                fig.add_vrect(
                    x0=pd.Timestamp(group_start),
                    x1=pd.Timestamp(end_day) + pd.Timedelta(days=1),
                    fillcolor=group_col,
                    opacity=opacity_map.get(group_col, 0.35),
                    layer="below",
                    line_width=0,
                )
                if day is not None:
                    group_start = day
                    group_col = next_col
                    group_is_fcst = next_is_fcst

    if sc_x:
        fig.add_trace(
            go.Bar(
                x=sc_x,
                y=sc_y,
                name="daily spore counts",
                marker_color="steelblue",
                opacity=0.8,
                width=86400000,
            )
        )

    for color, opacity, label in [
        ("red", 0.4, "high risk"),
        ("yellow", 0.35, "medium risk"),
        ("green", 0.35, "low risk"),
        ("grey", 0.3, "spore counts data missing"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker={
                    "symbol": "square",
                    "size": 14,
                    "color": color,
                    "opacity": opacity,
                },
                name=label,
                showlegend=True,
            )
        )

    fig.update_layout(
        title=title,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"title": "", "tickformat": "%b %d", "tickangle": -90, "showgrid": True},
        yaxis={"title": "Daily spore counts", "showgrid": True},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        bargroupgap=0,
    )
    fig.update_xaxes(rangeslider_visible=True)
    fig.write_html(output_html_path)
    return fig


# ---------------------------------------------------------------------------
# Plotly — risk heatmap (independent rows, visual only, smartphone-optimised)
# ---------------------------------------------------------------------------


def plot_risk_heatmap(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_path=None,
    title="Risk heatmap",
):
    """
    Smartphone-optimised three-row heatmap saved to *output_html_path*.

    The three rows are INDEPENDENT — spore counts are never fed into the
    mechanistic model here; this is a purely visual / informative tool:
      Modèle  – daily infection strength from the mechanistic model (°C·h)
      Mildiou – daily spore trap count
      Risque  – display-only product of the two (strength × count); not
                used algorithmically in any way

    Colour-category thresholds are read from config.risk_heatmap so they
    can be adjusted without touching code:
      model_thresholds:   lower boundaries of light-pink / salmon / red bands (°C·h)
      mildiou_thresholds: same for the Mildiou row (counts)
      Risque thresholds:  auto-derived as pair-wise products of the above
    """
    import datetime as _dt

    # ------------------------------------------------------------------ #
    # Read thresholds from config (fall back to defaults if absent)       #
    # ------------------------------------------------------------------ #
    _hm = {}
    if model_parameters is not None:
        _hm = dict(model_parameters.get("risk_heatmap", {}) or {})
    _mt = list(_hm.get("model_thresholds", [50, 100, 200]))
    _st = list(_hm.get("mildiou_thresholds", [10, 20, 30]))
    _rt = [_mt[i] * _st[i] for i in range(3)]  # pair-wise products for Risque

    # ------------------------------------------------------------------ #
    # Load events dataframe                                               #
    # ------------------------------------------------------------------ #
    df = pd.read_csv(events_dataframe_path)
    for col in ("oospore_infection", "secondary_infections"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    for col in ("oospore_infection_strength", "secondary_infection_strengths"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    model_strength_by_day: dict = {}
    if "oospore_infection" in df.columns:
        for _, row in df.iterrows():
            dt = row.get("oospore_infection")
            s = row.get("oospore_infection_strength")
            if pd.notna(dt) and pd.notna(s):
                d = dt.date()
                model_strength_by_day[d] = max(
                    model_strength_by_day.get(d, 0.0), float(s)
                )
    if "secondary_infections" in df.columns:
        for _, row in df.iterrows():
            dt = row.get("secondary_infections")
            s = row.get("secondary_infection_strengths")
            if pd.notna(dt) and pd.notna(s):
                d = dt.date()
                model_strength_by_day[d] = max(
                    model_strength_by_day.get(d, 0.0), float(s)
                )

    # ------------------------------------------------------------------ #
    # Load and aggregate daily spore counts                               #
    # ------------------------------------------------------------------ #
    spore_count_by_day: dict = {}
    spore_path = spore_counts_path or (
        model_parameters["input_data"]["spore_counts"]
        if model_parameters is not None
        else None
    )
    if spore_path:
        try:
            sc = pd.read_csv(spore_path, sep=";")
            _dc, _cc = sc.columns[0], sc.columns[1]
            fmt = (
                model_parameters["data_columns"]["format_columns"][0]
                if model_parameters is not None
                else "%d.%m.%Y %H:%M"
            )
            sc[_dc] = pd.to_datetime(sc[_dc], format=fmt, errors="coerce")
            sc = sc.groupby(sc[_dc].dt.date)[_cc].sum().reset_index()
            sc.columns = [_dc, _cc]
            for _, row in sc.iterrows():
                spore_count_by_day[row[_dc]] = float(row[_cc])
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Determine full date range                                           #
    # ------------------------------------------------------------------ #
    all_dates = set(model_strength_by_day.keys()) | set(spore_count_by_day.keys())
    if not all_dates:
        fig = go.Figure()
        fig.write_html(output_html_path)
        return fig

    dates = []
    cur = min(all_dates)
    while cur <= max(all_dates):
        dates.append(cur)
        cur += _dt.timedelta(days=1)

    # ------------------------------------------------------------------ #
    # Category assignment  0=grey  1=green  2=light pink  3=salmon  4=red
    # ------------------------------------------------------------------ #
    def _model_cat(d):
        s = model_strength_by_day.get(d, 0.0)
        if s < _mt[0]:
            return 1
        elif s < _mt[1]:
            return 2
        elif s < _mt[2]:
            return 3
        return 4

    def _spore_cat(d):
        c = spore_count_by_day.get(d)
        if c is None:
            return 0
        if c < _st[0]:
            return 1
        elif c < _st[1]:
            return 2
        elif c < _st[2]:
            return 3
        return 4

    def _risk_cat(d):
        c = spore_count_by_day.get(d)
        if c is None:
            return 0
        product = model_strength_by_day.get(d, 0.0) * c
        if product < _rt[0]:
            return 1
        elif product < _rt[1]:
            return 2
        elif product < _rt[2]:
            return 3
        return 4

    model_cats = [_model_cat(d) for d in dates]
    spore_cats = [_spore_cat(d) for d in dates]
    risk_cats = [_risk_cat(d) for d in dates]

    # ------------------------------------------------------------------ #
    # Hover text                                                          #
    # ------------------------------------------------------------------ #
    def _fmt_s(d):
        s = model_strength_by_day.get(d)
        return f"{s:.1f} °C·h" if s is not None else "0 °C·h"

    def _fmt_c(d):
        c = spore_count_by_day.get(d)
        return str(int(c)) if c is not None else "—"

    def _fmt_r(d):
        c = spore_count_by_day.get(d)
        if c is None:
            return "—"
        return f"{model_strength_by_day.get(d, 0.0) * c:.1f}"

    hover_model = [
        f"<b>{d.strftime('%Y-%m-%d')}</b><br>Infection strength: {_fmt_s(d)}"
        for d in dates
    ]
    hover_spore = [
        f"<b>{d.strftime('%Y-%m-%d')}</b><br>Spore count: {_fmt_c(d)}" for d in dates
    ]
    hover_risk = [
        f"<b>{d.strftime('%Y-%m-%d')}</b><br>Risk index: {_fmt_r(d)}" for d in dates
    ]

    # ------------------------------------------------------------------ #
    # Build figure                                                        #
    # ------------------------------------------------------------------ #
    z = [risk_cats, spore_cats, model_cats]
    customdata = [hover_risk, hover_spore, hover_model]
    x_ts = [pd.Timestamp(d) + pd.Timedelta(hours=12) for d in dates]

    _cs = [
        [0.00, "#D4D4D4"],
        [0.20, "#D4D4D4"],  # 0 grey  (missing)
        [0.20, "#90EE90"],
        [0.40, "#90EE90"],  # 1 green
        [0.40, "#FFB0C4"],
        [0.60, "#FFB0C4"],  # 2 medium pink
        [0.60, "#FA8072"],
        [0.80, "#FA8072"],  # 3 salmon
        [0.80, "#CC0000"],
        [1.00, "#CC0000"],  # 4 red
    ]

    fig = go.Figure(
        go.Heatmap(
            x=x_ts,
            y=["Risk", "Mildiou", "Model"],
            z=z,
            customdata=customdata,
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=_cs,
            zmin=0,
            zmax=4,
            showscale=False,
            xgap=1,
            ygap=2,
        )
    )

    for color, label in [
        ("#D4D4D4", "Données manquantes"),
        ("#90EE90", "Faible"),
        ("#FFB0C4", "Modéré"),
        ("#FA8072", "Élevé"),
        ("#CC0000", "Très élevé"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker={"symbol": "square", "size": 14, "color": color},
                name=label,
                showlegend=True,
            )
        )

    last_date = max(dates)
    range_start = pd.Timestamp(last_date - _dt.timedelta(days=9))
    range_end = pd.Timestamp(last_date + _dt.timedelta(days=1))

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        autosize=True,
        margin={"l": 60, "r": 10, "t": 10, "b": 110},
        xaxis={
            "tickangle": -45,
            "tickformat": "%d %b",
            "showgrid": False,
            "type": "date",
            "range": [range_start, range_end],
        },
        yaxis={
            "showgrid": False,
            "tickfont": {"size": 13},
            "tickmode": "array",
            "ticktext": ["<b>RISQUE</b>", "Mildiou", "Modèle"],
            "tickvals": ["Risk", "Mildiou", "Model"],
        },
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.35,
            "xanchor": "center",
            "x": 0.5,
        },
        height=280,
    )

    fig.add_shape(
        type="rect",
        xref="paper",
        yref="y",
        x0=0,
        x1=1,
        y0=0.48,
        y1=0.52,
        fillcolor="white",
        line={"width": 0},
        layer="above",
    )

    fig.write_html(output_html_path)
    return fig


# ---------------------------------------------------------------------------
# Combined mobile HTML (risk heatmap primary + infection chains secondary)
# ---------------------------------------------------------------------------


def write_combined_html(
    primary_fig,
    secondary_fig,
    output_path,
    primary_label="Aide à la décision",
    secondary_label="Modèle détaillé",
    spore_counts_graph_url=None,
):
    """
    Write a single mobile-friendly HTML file with *primary_fig* as the default
    view and a toggle button at the bottom that switches to *secondary_fig*.

    If *spore_counts_graph_url* is provided a second button labelled
    "Spores Mildiou" is added below the toggle, opening that URL in a new tab.
    """
    primary_div = primary_fig.to_html(full_html=False, include_plotlyjs=False)
    secondary_div = secondary_fig.to_html(full_html=False, include_plotlyjs=False)

    spore_btn_html = ""
    if spore_counts_graph_url:
        spore_btn_html = (
            f'  <button class="nav-btn" '
            f"onclick=\"window.open('{spore_counts_graph_url}','_blank')\">"
            f"Graphique spores</button>\n"
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 100%; font-family: sans-serif; background: white; }}
    .plot-view {{ display: none; width: 100%; }}
    .plot-view.active {{ display: block; }}
    .js-plotly-plot, .plotly, .plot-container {{ width: 100% !important; }}
    .nav-btn {{
      display: block;
      width: calc(100% - 24px);
      margin: 4px 12px;
      padding: 10px 14px;
      background: #2c7bb6;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      text-align: center;
    }}
    .nav-btn:hover {{ background: #1a5276; }}
    .modebar-container {{
      position: fixed !important;
      bottom: 0 !important;
      top: auto !important;
      right: 0 !important;
      left: auto !important;
      background: rgba(255,255,255,0.85);
      z-index: 999;
    }}
  </style>
</head>
<body>
  <div id="primary-view" class="plot-view active">
    {primary_div}
  </div>
  <div id="secondary-view" class="plot-view">
    {secondary_div}
  </div>
  <button id="toggle-btn" class="nav-btn" onclick="toggleView()">{secondary_label}</button>
{spore_btn_html}  <p style="text-align:center;color:grey;font-size:12px;margin:4px 0 2px;">Double-cliquez pour dézoomer</p>
  <script>
    function resizeActivePlots() {{
      document.querySelectorAll('.plot-view.active .js-plotly-plot').forEach(function(el) {{
        Plotly.Plots.resize(el);
      }});
    }}
    function toggleView() {{
      var pv = document.getElementById('primary-view');
      var sv = document.getElementById('secondary-view');
      var btn = document.getElementById('toggle-btn');
      if (pv.classList.contains('active')) {{
        pv.classList.remove('active');
        sv.classList.add('active');
        btn.textContent = '{primary_label}';
      }} else {{
        sv.classList.remove('active');
        pv.classList.add('active');
        btn.textContent = '{secondary_label}';
      }}
      resizeActivePlots();
    }}
    window.addEventListener('resize', resizeActivePlots);
    window.addEventListener('load', resizeActivePlots);
  </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
