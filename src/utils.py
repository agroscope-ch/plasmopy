"""
Generic utility functions for data extraction and manipulation.

Plotting functions have been moved to plots.py.
"""

from datetime import datetime
from pathlib import Path
from statistics import mean

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
