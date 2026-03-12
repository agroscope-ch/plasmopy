"""
Collection of generic-purpose functions to extract and manipulate timeseries data.

"""

from datetime import datetime
from pathlib import Path
from statistics import mean

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from suntimes import SunTimes


class output_files:
    def __init__(
        self,
        logfile,
        processed_file_meteo,
        model_params,
        events_dict,
        events_text,
        events_dataframe,
        infection_datetimes,
        pdf_graph,
        html_graph,
        analysis_html,
        overview_html,
        decision_support_html,
    ):
        self.logfile = logfile
        self.processed_file_meteo = processed_file_meteo
        self.model_params = model_params
        self.events_dict = events_dict
        self.events_text = events_text
        self.events_dataframe = events_dataframe
        self.infection_datetimes = infection_datetimes
        self.pdf_graph = pdf_graph
        self.html_graph = html_graph
        self.analysis_html = analysis_html
        self.overview_html = overview_html
        self.decision_support_html = decision_support_html


def create_output_filenames(
    input_file_meteo,
    input_spore_counts,
    output_dir=None,
    run_name=None,
):
    """Return an ``output_files`` object configured for this run.

    ``basename`` is chosen according to the following precedence:

    1. ``run_name`` if provided and nonempty.
    2. ``Path(input_file_meteo).stem`` if a meteo path is given.
    3. Fallback to a timestamp string when neither value is available.

    ``output_dir`` may be supplied to override the default ``data/output``
    directory; it can be an absolute or relative path.

    Raises a :class:`ValueError` if both ``run_name`` and ``input_file_meteo`` are
    missing and a reasonable timestamp cannot be generated (which should never
    happen).
    """
    # determine base name for files
    if run_name and str(run_name).strip():
        basename = str(run_name).strip()
    elif input_file_meteo:
        basename = Path(input_file_meteo).stem
    else:
        # no meteo and no explicit name: use timestamp so we can still run
        basename = datetime.now().strftime("%Y%m%d_%H%M%S")

    # decide output directory
    if output_dir and str(output_dir).strip():
        output_folder = Path(output_dir) / basename
    else:
        output_folder = Path("data/output") / basename

    output_folder.mkdir(parents=True, exist_ok=True)
    output_basename = output_folder / basename

    # build full paths using pathlib to keep semantics clear
    logfile = output_basename.with_suffix(".log").resolve()
    processed_file_meteo = output_basename.with_suffix(".processed.csv").resolve()
    model_params = output_basename.with_suffix(".model_params.obj").resolve()
    events_dict = output_basename.with_suffix(".events.obj").resolve()
    events_text = output_basename.with_suffix(".events.csv").resolve()
    events_dataframe = output_basename.with_suffix(".events_dataframe.csv").resolve()
    infection_datetimes = output_basename.with_suffix(
        ".infection_datetimes.csv"
    ).resolve()
    pdf_graph = Path(str(output_basename) + ".basic.pdf").resolve()
    html_graph = output_basename.with_suffix(".html").resolve()
    analysis_html = output_basename.with_suffix(".analysis.html").resolve()
    overview_html = output_basename.with_suffix(".overview.html").resolve()
    decision_support_html = Path(
        str(output_basename) + ".decision_support_tool.html"
    ).resolve()

    output_filenames = output_files(
        logfile,
        processed_file_meteo,
        model_params,
        events_dict,
        events_text,
        events_dataframe,
        infection_datetimes,
        pdf_graph,
        html_graph,
        analysis_html,
        overview_html,
        decision_support_html,
    )
    return output_filenames


def get_suntimes(longitude, latitude, elevation, date):
    """
    Returns a dictionary with sunrise and sunset times necessary for determining whether sporulation
    can occur. Required inputs are the site coordinates and date.

    """
    sun = SunTimes(longitude, latitude, elevation)
    date = datetime(date.year, date.month, date.day)
    sunrise_t = sun.riselocal(date)
    sunset_t = sun.setlocal(date)
    suntimes = {"sunrise": sunrise_t, "sunset": sunset_t}
    return suntimes


def get_daily_measurements(processed_data, variable):
    """
    Returns a nested dictionary of any measurement variable per day, with day as
    first key and the row index as second key.

    """
    daily_measurements = {}
    for i in processed_data.index:
        try:
            day = processed_data["datetime"][i].date()
        except TypeError:
            continue
        try:
            measurement = processed_data[variable][i]
        except ValueError:
            continue
        if day in daily_measurements.keys():
            daily_measurements[day][i] = measurement
        else:
            daily_measurements[day] = {i: measurement}
    return daily_measurements


def get_daily_mean_measurements(processed_data, variable):
    """
    Returns a dictionary with the averages per day of a specific measurement variable.

    """
    daily_measurements = get_daily_measurements(processed_data, variable)
    daily_mean_measurements = {}
    for day in daily_measurements.keys():
        daily_mean = mean(daily_measurements[day].values())
        daily_mean_measurements[day] = daily_mean
    return daily_mean_measurements


def compute_daily_infection_strength(processed_data, date, measurement_time_interval):
    """
    Returns the daily infection strength index for a given date:
    sum of (temperature * measurement_time_interval / 60) for all timesteps
    where leaf_wetness > 0.  Units: degree-hours.
    """
    mask = (processed_data["datetime"].dt.date == date) & (
        processed_data["leaf_wetness"] > 0
    )
    temps = processed_data.loc[mask, "temperature"].dropna()
    return float(temps.sum() * measurement_time_interval / 60)


def plot_events(infection_events, model_parameters, pdf_path):  # noqa: C901
    # Sample data: Dates and corresponding events for multiple categories

    graphs = {"pdf": pdf_path}

    scatter_height_factor = 1
    n_events = 6
    if model_parameters["input_data"]["spore_counts"] is not None:
        spore_counts = pd.read_csv(
            model_parameters["input_data"]["spore_counts"], sep=";"
        )
        _date_col = spore_counts.columns[0]
        _counts_col = spore_counts.columns[1]
        spore_counts[_date_col] = pd.to_datetime(
            spore_counts[_date_col],
            format=model_parameters["data_columns"]["format_columns"][0],
        )
        spore_counts = (
            spore_counts.groupby(spore_counts[_date_col].dt.date)[_counts_col]
            .sum()
            .reset_index()
        )
        spore_counts.columns = [_date_col, _counts_col]
        spore_counts[_date_col] = pd.to_datetime(spore_counts[_date_col])
        scatter_height_factor = max(spore_counts[_counts_col]) / n_events

    oospore_germinations = []
    oospore_dispersions = []
    oospore_infections = []
    completed_incubations = []
    sporulations = []
    secondary_infections = []

    # Adding infection events datetimes to tuples for plotting, while removing duplicate events issuing from different
    # infection events starting points, so to make plotting faster.
    for infection_event in infection_events:
        if (
            infection_event["oospore_germination"] is not None
            and infection_event["oospore_germination"] not in oospore_germinations
        ):
            oospore_germinations.append(infection_event["oospore_germination"])
        if (
            infection_event["oospore_dispersion"] is not None
            and infection_event["oospore_dispersion"] not in oospore_dispersions
        ):
            oospore_dispersions.append(infection_event["oospore_dispersion"])
        if (
            infection_event["oospore_infection"] is not None
            and infection_event["oospore_infection"] not in oospore_infections
        ):
            oospore_infections.append(infection_event["oospore_infection"])
        if (
            infection_event["completed_incubation"] is not None
            and infection_event["completed_incubation"] not in completed_incubations
        ):
            completed_incubations.append(infection_event["completed_incubation"])
        if (
            infection_event["sporulations"] is not None
            and infection_event["sporulations"] not in sporulations
        ):
            sporulations.extend(infection_event["sporulations"])
        if (
            infection_event["secondary_infections"] is not None
            and infection_event["secondary_infections"] not in secondary_infections
        ):
            secondary_infections.extend(infection_event["secondary_infections"])

    oospore_germinations_tuple = {
        (element, 1 * scatter_height_factor) for element in oospore_germinations
    }
    oospore_dispersions_tuple = [
        (element, 2 * scatter_height_factor) for element in oospore_dispersions
    ]
    oospore_infections_tuple = {
        (element, 3 * scatter_height_factor) for element in oospore_infections
    }
    completed_incubations_tuple = {
        (element, 4 * scatter_height_factor) for element in completed_incubations
    }
    sporulations_tuple = {
        (element, 5 * scatter_height_factor) for element in sporulations
    }
    secondary_infections_tuple = {
        (element, 6 * scatter_height_factor) for element in secondary_infections
    }

    category_data = {
        "oospore germinations": oospore_germinations_tuple,
        "oospore dispersions": oospore_dispersions_tuple,
        "oospore infections": oospore_infections_tuple,
        "completed incubations": completed_incubations_tuple,
        "sporulations": sporulations_tuple,
        "secondary infections": secondary_infections_tuple,
    }

    # Convert date strings to datetime objects for each category
    category_datetimes = {
        category: [date for date, _ in data] for category, data in category_data.items()
    }
    category_events = {
        category: [events for _, events in data]
        for category, data in category_data.items()
    }

    # Create a plot
    plt.rcParams["figure.figsize"] = [14, 6]
    fig, ax = plt.subplots()

    # Plot events over dates for each category
    event_colours = ["lightgreen", "orange", "red", "green", "violet", "purple"]
    colour_n = 0
    for category in category_data.keys():
        ax.plot(
            category_datetimes[category],
            category_events[category],
            marker="o",
            alpha=0.4,
            linestyle="",
            color=event_colours[colour_n],
            label=category,
        )
        colour_n += 1

    # Format the x-axis as dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
    plt.rc("xtick", labelsize=5)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.gcf().autofmt_xdate()  # Rotate date labels for better visibility

    # Add 1st legend
    plt.legend(
        bbox_to_anchor=(0.4, -0.01),
        loc="lower center",
        bbox_transform=fig.transFigure,
        ncol=3,
    )

    # Set labels, title and grid
    plt.title(model_parameters["input_data"]["meteo"] or "automated pull")
    plt.tick_params(
        left=False, right=False, labelleft=False, labelbottom=True, bottom=True
    )
    plt.grid()

    if model_parameters["input_data"]["spore_counts"] is not None:
        ax_2 = ax.twinx()
        ax_2.plot(
            spore_counts.iloc[:, 0],
            spore_counts.iloc[:, 1],
            alpha=0.4,
            linestyle="--",
            label="spore counts",
        )
        ax_2.tick_params(right=True, labelright=True)

    # plt.tight_layout()

    # Add 2nd legend
    plt.legend(
        bbox_to_anchor=(0.8, -0.01),
        loc="lower center",
        bbox_transform=fig.transFigure,
        ncol=1,
    )

    # Store the plot
    plt.savefig(graphs["pdf"])
    plt.close()


def plot_infection_analysis(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_path=None,
    title="Infection analysis",
):
    """
    Interactive HTML plot reproducing the Rplot.R visualisation.

    Layout (matching the R script):
      - Dark-blue vertical bars from y=0 to sporangia density at each sporulation datetime.
      - Green square at oospore maturation (y=0).
      - Per-infection-chain dotted lines connecting event stages at fixed y-positions,
        with a distinct marker shape per stage.
      - Chains triggered by the support decision tool shortcut (oospore_germination is
        None while dispersion or sporulation is not None) are drawn in red.
      - Daily spore counts as light-blue bars on the right y-axis (background).

    Fixed y-positions (matching Rplot.R):
      germination=0, dispersion=75 000, infection=150 000,
      completed incubation=225 000, sporulation=300 000, secondary infection=325 000.
    """
    # ------------------------------------------------------------------ #
    # Load and parse events dataframe                                     #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Support-decision-tool shortcut detection                            #
    # skip_to_dispersion : germination=NaN, dispersion=not NaN           #
    # skip_to_sporulation: germination=NaN, sporulations=not NaN         #
    # ------------------------------------------------------------------ #
    df["_shortcut"] = df["oospore_germination"].isna() & (
        df["oospore_dispersion"].notna() | df["sporulations"].notna()
    )

    # Read max sporangia density from config (fallback 360 000)
    max_density = (
        float(model_parameters["sporangia"]["max_density"])
        if model_parameters is not None
        else 360_000
    )

    # Evenly-spaced y positions: germination at 0, secondary infection at max_density
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

    # ------------------------------------------------------------------ #
    # Background: daily spore counts (right y-axis)                      #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Sporangia density vertical bars (type='h' equivalent)              #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Oospore maturation single point (down-arrow at y=0)                #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Infection-chain dotted lines (one trace per shortcut group)        #
    # ------------------------------------------------------------------ #
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
        # First segment of each group doubles as the legend entry
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

    # ------------------------------------------------------------------ #
    # Event-stage markers (one trace per stage, split by shortcut so     #
    # both colours appear clearly in the legend                          #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Layout                                                              #
    # ------------------------------------------------------------------ #
    fig.update_layout(
        title=title,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={
            "title": "",
            "tickformat": "%b %d",
            "tickangle": -90,
            "showgrid": True,
        },
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


def plot_spore_infection_overview(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_result=None,
    spore_counts_path=None,
    title="Spore counts & infection overview",
):
    """
    Interactive HTML overview plot showing daily spore counts with day-level
    background colours and top-of-chart markers.

    Background colour per day:
      Grey   – spore counts data are missing for that day.
      Yellow – spore counts condition met (either) OR model predicts infection,
               but not both simultaneously.
      Red    – spore counts condition met AND model predicts infection.
      None   – no relevant event or condition on that day.

    Top markers (on a hidden y-axis pinned to the top of the chart):
      circle  – infection model event (oospore_infection or secondary_infection)
      diamond – spore count condition triggered (threshold or % increase)
    """
    import datetime as _dt

    # ------------------------------------------------------------------ #
    # Load and parse events dataframe                                     #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Load and aggregate daily spore counts                               #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Build event and condition date sets                                 #
    # ------------------------------------------------------------------ #
    # Model infection events
    infection_dates: set = set()
    for col in ("oospore_infection", "secondary_infections"):
        if col in df.columns:
            infection_dates |= {ts.date() for ts in df[col].dropna()}

    # Spore count condition trigger dates (all of them across the full dataset)
    condition_dates: set = set()
    if spore_counts_result:
        for raw in spore_counts_result.get("dispersion_datetimes", []):
            condition_dates.add(pd.Timestamp(raw).date())
        for raw in spore_counts_result.get("sporulation_datetimes", []):
            condition_dates.add(pd.Timestamp(raw).date())

    # ------------------------------------------------------------------ #
    # Grey days: within the full plotted range but missing spore data    #
    # ------------------------------------------------------------------ #
    grey_days: set = set()
    if sc_days:
        # Start from the earliest available sc_day (covers the whole x-range
        # of the plot), optionally extending back to the simulation start if
        # that is even earlier.
        range_start = min(sc_days)
        if "start" in df.columns and df["start"].notna().any():
            col_start = df["start"].dropna().min().date()
            range_start = min(range_start, col_start)
        # Also include all df datetime columns (start, dispersion, sporulation,
        # infection events) so the range extends to the latest processed/forecast date
        # even when no spore counts data is available beyond that point.
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

    # ------------------------------------------------------------------ #
    # Assign background colour per day                                    #
    # ------------------------------------------------------------------ #
    red_days = infection_dates & condition_dates
    yellow_days = (infection_dates | condition_dates) - red_days
    # Grey only on days not already coloured by an event/condition
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

    # ------------------------------------------------------------------ #
    # Build figure                                                        #
    # ------------------------------------------------------------------ #
    fig = go.Figure()

    # Background colour rectangles (grouped by consecutive same-colour + same-period days)
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

    # Spore counts bars (primary y-axis)
    if sc_x:
        fig.add_trace(
            go.Bar(
                x=sc_x,
                y=sc_y,
                name="daily spore counts",
                marker_color="steelblue",
                opacity=0.8,
                width=86400000,  # exactly 1 day in ms, matches vrect width
            )
        )

    # Invisible legend swatches for background colours
    legend_items = [
        ("red", 0.4, "high risk"),
        ("yellow", 0.35, "medium risk"),
        ("green", 0.35, "low risk"),
        ("grey", 0.3, "spore counts data missing"),
    ]
    for color, opacity, label in legend_items:
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
        xaxis={
            "title": "",
            "tickformat": "%b %d",
            "tickangle": -90,
            "showgrid": True,
        },
        yaxis={
            "title": "Daily spore counts",
            "showgrid": True,
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


def plot_decision_support_tool(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_path=None,
    title="Decision support tool",
):
    """
    Generate a three-row heatmap (Model / Spores / Risk) saved to
    *output_html_path*.

    Colour categories
    -----------------
    Model (daily infection strength, °C·h):
        green          : strength < 50   (or no infection event that day)
        very light pink: 50  <= strength < 100
        salmon         : 100 <= strength < 200
        red            : strength >= 200

    Spores (daily spore count):
        grey           : data missing
        green          : count < 10
        very light pink: 10 <= count < 20
        salmon         : 20 <= count < 30
        red            : count >= 30

    Risk (infection_strength × daily_spore_count):
        grey           : spore data missing
        green          : product < 500   (50 × 10)
        very light pink: 500  <= product < 2000  (100 × 20)
        salmon         : 2000 <= product < 6000  (200 × 30)
        red            : product >= 6000
    """
    import datetime as _dt

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

    # Build model_strength_by_day: date -> max infection strength across events
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
    # Category assignment  0=grey  1=green  2=v.light pink  3=salmon  4=red
    # ------------------------------------------------------------------ #
    def _model_cat(d):
        s = model_strength_by_day.get(d, 0.0)
        if s < 50:
            return 1
        elif s < 100:
            return 2
        elif s < 200:
            return 3
        return 4

    def _spore_cat(d):
        c = spore_count_by_day.get(d)
        if c is None:
            return 0
        if c < 10:
            return 1
        elif c < 20:
            return 2
        elif c < 30:
            return 3
        return 4

    def _risk_cat(d):
        c = spore_count_by_day.get(d)
        if c is None:
            return 0
        product = model_strength_by_day.get(d, 0.0) * c
        if product < 500:
            return 1
        elif product < 2000:
            return 2
        elif product < 6000:
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
    # z rows in Plotly heatmap are bottom→top: Risk, Spores, Model
    z = [risk_cats, spore_cats, model_cats]
    customdata = [hover_risk, hover_spore, hover_model]
    x_ts = [pd.Timestamp(d) + pd.Timedelta(hours=12) for d in dates]

    # Discrete colorscale: 5 bands for categories 0–4
    _cs = [
        [0.00, "#C0C0C0"],
        [0.20, "#C0C0C0"],  # 0 grey  (missing)
        [0.20, "#90EE90"],
        [0.40, "#90EE90"],  # 1 green
        [0.40, "#FFD1DC"],
        [0.60, "#FFD1DC"],  # 2 very light pink
        [0.60, "#FA8072"],
        [0.80, "#FA8072"],  # 3 salmon
        [0.80, "#CC0000"],
        [1.00, "#CC0000"],  # 4 red
    ]

    fig = go.Figure(
        go.Heatmap(
            x=x_ts,
            y=["Risk", "Spores", "Model"],
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

    # Legend swatches
    for color, label in [
        ("#C0C0C0", "Data missing"),
        ("#90EE90", "Low"),
        ("#FFD1DC", "Moderate"),
        ("#FA8072", "High"),
        ("#CC0000", "Very high"),
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

    fig.update_layout(
        title=title,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={
            "tickangle": -90,
            "tickformat": "%b %d",
            "showgrid": False,
            "type": "date",
        },
        yaxis={
            "showgrid": False,
            "tickfont": {"size": 13},
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.05,
            "xanchor": "left",
            "x": 0,
        },
        height=300,
    )

    fig.write_html(output_html_path)
    return fig


def write_combined_html(
    primary_fig,
    secondary_fig,
    output_path,
    primary_label="Decision Support",
    secondary_label="Analysis",
):
    """
    Write a single HTML file with *primary_fig* as the default view and a
    toggle button (top-left) that switches to *secondary_fig*.
    """
    primary_div = primary_fig.to_html(full_html=False, include_plotlyjs=False)
    secondary_div = secondary_fig.to_html(full_html=False, include_plotlyjs=False)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ margin: 0; padding: 0; font-family: sans-serif; }}
    #toggle-btn {{
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 1000;
      padding: 6px 14px;
      background: #2c7bb6;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 13px;
    }}
    #toggle-btn:hover {{ background: #1a5276; }}
    .plot-view {{ display: none; width: 100%; }}
    .plot-view.active {{ display: block; }}
  </style>
</head>
<body>
  <button id="toggle-btn" onclick="toggleView()">Show {secondary_label}</button>
  <div id="primary-view" class="plot-view active">
    {primary_div}
  </div>
  <div id="secondary-view" class="plot-view">
    {secondary_div}
  </div>
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
        btn.textContent = 'Show {primary_label}';
      }} else {{
        sv.classList.remove('active');
        pv.classList.add('active');
        btn.textContent = 'Show {secondary_label}';
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
