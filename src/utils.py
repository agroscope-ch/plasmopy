"""
Collection of generic-purpose functions to extract and manipulate timeseries data.

"""

from datetime import datetime
from pathlib import Path
from statistics import mean

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
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
        infection_datetimes,
        pdf_graph,
        html_graph,
    ):
        self.logfile = logfile
        self.processed_file_meteo = processed_file_meteo
        self.model_params = model_params
        self.events_dict = events_dict
        self.events_text = events_text
        self.infection_datetimes = infection_datetimes
        self.pdf_graph = pdf_graph
        self.html_graph = html_graph


def create_output_filenames(input_file_meteo, input_spore_counts):
    basename = Path(input_file_meteo).stem
    output_folder = "data/output/" + basename
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    output_basename = output_folder + "/" + basename

    logfile = Path(output_basename + ".log").resolve()
    processed_file_meteo = Path(output_basename + ".processed.csv").resolve()
    model_params = Path(output_basename + ".model_params.obj").resolve()
    events_dict = Path(output_basename + ".events.obj").resolve()
    events_text = Path(output_basename + ".events.csv").resolve()
    infection_datetimes = Path(output_basename + ".infection_datetimes.csv").resolve()
    pdf_graph = Path(output_basename + ".pdf").resolve()
    html_graph = Path(output_basename + ".html").resolve()

    output_filenames = output_files(
        logfile,
        processed_file_meteo,
        model_params,
        events_dict,
        events_text,
        infection_datetimes,
        pdf_graph,
        html_graph,
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
        spore_counts.iloc[:, 0] = pd.to_datetime(
            spore_counts.iloc[:, 0],
            format=model_parameters["format_columns"][0],
        )
        spore_counts.iloc[:, 1] = [np.log10(x + 1) for x in spore_counts.iloc[:, 1]]
        scatter_height_factor = max(spore_counts.iloc[:, 1]) / n_events

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
    plt.title(model_parameters["input_data"]["meteo"])
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
            label="spore counts (log10)",
        )

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
                name="spore counts (log10)",
                opacity=1,
                hovertext=spore_counts["Counts"],
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
        title="Input data: " + model_parameters["input_data"]["meteo"],
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
