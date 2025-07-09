"""
Sporangia density algorithms.

"""

from math import ceil
from statistics import mean

import utils


def get_sporangia_density(
    processed_data,
    measurement_time_interval,
    longitude,
    latitude,
    elevation,
    sporulation_datetime_rowindex,
    sporulation_datetime,
    sporangia_latency,
    sporangia_min_temperature,
    sporangia_max_temperature,
    sporangia_max_density,
    algorithmic_time_steps,
):
    """
    Function to compute the temperature-dependent sporangia density after oilspot
    sporulation on infected leaves. The matemathical formula was adapted from
    (Hill G.K., 1989).

    """

    sporangia_density = None

    sporulation_date = sporulation_datetime.date()
    suntimes = utils.get_suntimes(longitude, latitude, elevation, sporulation_date)
    sunset_t = suntimes["sunset"]

    start_sporangia_latency_rowindex = None

    for i in range(
        sporulation_datetime_rowindex, len(processed_data.index), algorithmic_time_steps
    ):
        start_sporangia_latency_datetime = processed_data["datetime"][i]
        if start_sporangia_latency_datetime >= sunset_t:
            start_sporangia_latency_rowindex = i
            break

    if start_sporangia_latency_rowindex is None:
        # print(
        #     "WARNING: starting datetime for sporangia latency period after sporulation could not be determined."
        # )
        return sporangia_density

    stop_sporangia_latency_rowindex = ceil(
        start_sporangia_latency_rowindex
        + sporangia_latency
        * 60  # hours to minutes conversion
        / measurement_time_interval  # minutes to measurement interval conversion ##### NOT THE BEST SOLUTION
    )

    stop_sporangia_latency_rowindex = min(
        stop_sporangia_latency_rowindex, len(processed_data.index) - 1
    )

    sporangia_latency_temperatures = []

    for i in range(
        start_sporangia_latency_rowindex,
        stop_sporangia_latency_rowindex + 1,
        algorithmic_time_steps,
    ):
        if processed_data["temperature"][i] is not None:
            sporangia_latency_temperatures.append(processed_data["temperature"][i])

    avg_latency_temperature = mean(sporangia_latency_temperatures)

    if avg_latency_temperature > sporangia_max_temperature:
        sporangia_density = sporangia_max_density
    elif avg_latency_temperature < sporangia_min_temperature:
        sporangia_density = 0
    else:
        sporangia_density = (
            sporangia_max_density
            * (avg_latency_temperature - sporangia_min_temperature)
            / (sporangia_max_temperature - sporangia_min_temperature)
        )

    return sporangia_density


def launch_sporangia_densities(
    processed_data,
    measurement_time_interval,
    longitude,
    latitude,
    elevation,
    sporulation_datetime_rowindexes,
    sporangia_latency,
    sporangia_min_temperature,
    sporangia_max_temperature,
    sporangia_max_density,
    algorithmic_time_steps,
):
    """
    Function to launch sporangia density counting.

    """

    sporangia_densities = []

    for sporulation_datetime_rowindex in sporulation_datetime_rowindexes:
        sporulation_datetime = processed_data["datetime"][sporulation_datetime_rowindex]
        sporangia_density = get_sporangia_density(
            processed_data,
            measurement_time_interval,
            longitude,
            latitude,
            elevation,
            sporulation_datetime_rowindex,
            sporulation_datetime,
            sporangia_latency,
            sporangia_min_temperature,
            sporangia_max_temperature,
            sporangia_max_density,
            algorithmic_time_steps,
        )
        sporangia_densities.append(sporangia_density)

    return sporangia_densities
