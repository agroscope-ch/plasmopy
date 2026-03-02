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
    pdf_graph = output_basename.with_suffix(".pdf").resolve()
    html_graph = output_basename.with_suffix(".html").resolve()
    analysis_html = output_basename.with_suffix(".analysis.html").resolve()
    overview_html = output_basename.with_suffix(".overview.html").resolve()

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


def plot_events(infection_events, model_parameters, graphs):  # noqa: C901
    # Sample data: Dates and corresponding events for multiple categories

    graphs = {"pdf": graphs[0], "html": graphs[1]}

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

    # Create the Plotly figure
    fig = go.Figure()

    # Add the line plot
    colour_n = 0
    for category in category_data.keys():
        fig.add_trace(
            go.Scatter(
                x=category_datetimes[category],
                y=category_events[category],
                mode="markers",
                marker={"size": 10, "color": event_colours[colour_n]},
                name=category,
                opacity=1,
                hovertext=category_events[category],
            )
        )
        colour_n += 1

    if model_parameters["input_data"]["spore_counts"] is not None:
        fig.add_trace(
            go.Scatter(
                x=spore_counts.iloc[:, 0],
                y=spore_counts.iloc[:, 1],
                line={"color": "royalblue", "width": 1, "dash": "dot"},
                name="spore counts",
                opacity=1,
                hovertext=spore_counts.iloc[:, 1],
                yaxis="y2",
            )
        )

    fig.update_layout(
        width=1600,
        height=600,
        paper_bgcolor="white",
        plot_bgcolor="white",
        yaxis={"visible": True, "showticklabels": False},
        yaxis2={
            "visible": True,
            "showticklabels": True,
            "overlaying": "y",
            "side": "right",
        },
        xaxis={"tickformat": "%d/%m/%y %H:%M"},
        title="Input data: "
        + (model_parameters["input_data"]["meteo"] or "automated pull"),
        legend={
            "orientation": "h",
            "entrywidthmode": "fraction",
            "entrywidth": 0.2,
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "auto",
            "x": 0,
        },
    )

    fig.update_yaxes(showline=False, linewidth=2, linecolor="black", showgrid=True)
    fig.update_xaxes(
        showline=False, linewidth=2, linecolor="black", tickangle=-90, showgrid=True
    )
    fig.update_xaxes(rangeslider_visible=True)

    fig.write_html(graphs["html"])

    return fig


def plot_infection_analysis(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
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
            df[col] = pd.to_datetime(df[col], errors="coerce")

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

    # Fixed y positions (matching Rplot.R yvalues)
    event_y = {
        "oospore_germination": 0,
        "oospore_dispersion": 75_000,
        "oospore_infection": 150_000,
        "completed_incubation": 225_000,
        "sporulations": 300_000,
        "secondary_infections": 325_000,
    }
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
        spore_path = model_parameters["input_data"]["spore_counts"]
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
            )
        )

    # ------------------------------------------------------------------ #
    # Oospore maturation single point (green square at y=0)              #
    # ------------------------------------------------------------------ #
    mat = df["oospore_maturation"].dropna()
    if not mat.empty:
        fig.add_trace(
            go.Scatter(
                x=[mat.iloc[0]],
                y=[0],
                mode="markers",
                marker={"symbol": "square", "color": "darkgreen", "size": 12},
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
                    showlegend=False,  # chain line trace already owns this legend entry
                    hovertemplate="%{x}<extra>" + label + "</extra>",
                )
            )

    # ------------------------------------------------------------------ #
    # Layout                                                              #
    # ------------------------------------------------------------------ #
    y_tick_vals = list(event_y.values())
    y_tick_text = [event_labels[c] for c in event_y]

    fig.update_layout(
        title=title,
        width=1600,
        height=700,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={
            "title": "",
            "tickformat": "%b %d",
            "tickangle": -90,
            "showgrid": True,
        },
        yaxis={
            "title": "Leaf sporangia density [sporangia / cm²]",
            "range": [0, 360_000],
            "tickvals": y_tick_vals,
            "ticktext": y_tick_text,
            "showgrid": True,
        },
        yaxis2={
            "title": "Daily spore counts",
            "overlaying": "y",
            "side": "right",
            "showticklabels": True,
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


def plot_spore_infection_overview(  # noqa: C901
    events_dataframe_path,
    output_html_path,
    model_parameters=None,
    spore_counts_result=None,
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
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # ------------------------------------------------------------------ #
    # Load and aggregate daily spore counts                               #
    # ------------------------------------------------------------------ #
    sc_x, sc_y = [], []
    sc_days: set = set()
    if model_parameters is not None:
        spore_path = model_parameters["input_data"]["spore_counts"]
        if spore_path:
            try:
                sc = pd.read_csv(spore_path, sep=";")
                _dc, _cc = sc.columns[0], sc.columns[1]
                fmt = model_parameters["data_columns"]["format_columns"][0]
                sc[_dc] = pd.to_datetime(sc[_dc], format=fmt, errors="coerce")
                sc = sc.groupby(sc[_dc].dt.date)[_cc].sum().reset_index()
                sc.columns = [_dc, _cc]
                sc[_dc] = pd.to_datetime(sc[_dc])
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
    # Grey days: within simulation period but missing spore count data    #
    # ------------------------------------------------------------------ #
    grey_days: set = set()
    if sc_days:
        sim_start = None
        if "start" in df.columns and df["start"].notna().any():
            sim_start = df["start"].dropna().min().date()
        all_endpoint_dates = list(infection_dates) + [ts.date() for ts in sc_x]
        sim_end = max(all_endpoint_dates) if all_endpoint_dates else None
        if sim_start and sim_end:
            cur = sim_start
            while cur <= sim_end:
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

    _color_opacity = {"red": 0.35, "yellow": 0.25, "grey": 0.2}
    day_color = (
        {d: "red" for d in red_days}
        | {d: "yellow" for d in yellow_days}
        | {d: "grey" for d in effective_grey}
    )

    # ------------------------------------------------------------------ #
    # Build figure                                                        #
    # ------------------------------------------------------------------ #
    fig = go.Figure()

    # Background colour rectangles (grouped by consecutive same-colour days)
    if day_color:
        sorted_days = sorted(day_color)
        group_start = sorted_days[0]
        group_col = day_color[sorted_days[0]]
        for day in sorted_days[1:] + [None]:
            next_col = day_color.get(day) if day is not None else None
            idx = sorted_days.index(day) if day is not None else len(sorted_days)
            consecutive = (
                day is not None
                and (day - sorted_days[idx - 1]) == _dt.timedelta(days=1)
                and next_col == group_col
            )
            if not consecutive:
                end_day = sorted_days[idx - 1] if day is not None else sorted_days[-1]
                fig.add_vrect(
                    x0=pd.Timestamp(group_start),
                    x1=pd.Timestamp(end_day) + pd.Timedelta(days=1),
                    fillcolor=group_col,
                    opacity=_color_opacity.get(group_col, 0.25),
                    layer="below",
                    line_width=0,
                )
                if day is not None:
                    group_start = day
                    group_col = next_col

    # Spore counts bars (primary y-axis)
    if sc_x:
        fig.add_trace(
            go.Bar(
                x=sc_x,
                y=sc_y,
                name="daily spore counts",
                marker_color="steelblue",
                opacity=0.8,
            )
        )

    # Top-of-chart markers on hidden secondary y-axis ([0, 1] range)
    # Circle = infection model event; diamond = spore count condition
    model_marker_days = [pd.Timestamp(d) for d in sorted(infection_dates)]
    cond_marker_days = [pd.Timestamp(d) for d in sorted(condition_dates)]

    if model_marker_days:
        fig.add_trace(
            go.Scatter(
                x=model_marker_days,
                y=[1.0] * len(model_marker_days),
                mode="markers",
                marker={"symbol": "circle", "size": 10, "color": "darkred"},
                name="infection model event",
                yaxis="y2",
            )
        )
    if cond_marker_days:
        fig.add_trace(
            go.Scatter(
                x=cond_marker_days,
                y=[0.88] * len(cond_marker_days),
                mode="markers",
                marker={"symbol": "diamond", "size": 10, "color": "darkorange"},
                name="spore count condition",
                yaxis="y2",
            )
        )

    # Invisible legend swatches for background colours
    legend_items = [
        ("red", 0.4, "infection AND spore count condition"),
        ("yellow", 0.35, "infection OR spore count condition (not both)"),
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
        width=1600,
        height=500,
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
        yaxis2={
            "range": [0, 1.15],
            "overlaying": "y",
            "showticklabels": False,
            "showgrid": False,
            "zeroline": False,
            "fixedrange": True,
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
