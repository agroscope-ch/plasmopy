"""
Sporulation algorithms.

"""

from datetime import timedelta
from math import ceil
from statistics import mean

import utils


def sporulation(
    processed_data,
    start_sporulation_datetime_rowindex,
    sporulation_leaf_wetness_threshold,
    sporulation_min_humidity,
    sporulation_min_temperature,
    sporulation_min_darkness_hours,
    measurement_time_interval,
    longitude,
    latitude,
    elevation,
    algorithmic_time_steps,
):
    """
    Function returning the datetime (datetime and row index) at which activation
    conditions for sporulation in plant are met.

    return
    : sporulation_datetime, sporulation_datetime_rowindex

    """

    sporulation_datetime = None
    sporulation_datetime_rowindex = None

    start_sporulation_datetime = processed_data["datetime"][
        start_sporulation_datetime_rowindex
    ]
    start_sporulation_date = start_sporulation_datetime.date()
    suntimes = utils.get_suntimes(
        longitude, latitude, elevation, start_sporulation_date
    )
    sunrise_t = suntimes["sunrise"]
    sunset_t = suntimes["sunset"]
    max_sporulation_datetime = sunrise_t - timedelta(
        hours=sporulation_min_darkness_hours
    )

    # If sporulation is found to start not within the minimum amount of hours of darkness, sporulation cannot happen.
    if (
        start_sporulation_datetime < sunset_t
        and start_sporulation_datetime > max_sporulation_datetime
    ):
        return sporulation_datetime, sporulation_datetime_rowindex

    # Finding max rowindex at which conditions must be met for succesful sporulation.
    # Last row index + 1 hour in minutes (60) times the number of hours divided by the measurement interval in minutes.
    stop_sporulation_datetime_rowindex = ceil(
        start_sporulation_datetime_rowindex
        + (
            60
            * sporulation_min_darkness_hours  # minutes to hours conversion
            / measurement_time_interval
        )  # minutes to measurement interval conversion ##### NOT THE BEST SOLUTION
    )

    sporulation_humidities = []
    sporulation_temperatures = []

    # Check if minimal relative humidity and temperature conditions are never reached
    # within the moving average measurements during the darkness period required for sporulation.
    for i in range(
        start_sporulation_datetime_rowindex,
        min(stop_sporulation_datetime_rowindex + 1, len(processed_data.index)),
        algorithmic_time_steps,
    ):
        leaf_wetness = processed_data["leaf_wetness"][i]
        humidity = processed_data["humidity"][i]
        sporulation_humidities.append(humidity)
        avg_humidity = mean(sporulation_humidities)
        temperature = processed_data["temperature"][i]
        sporulation_temperatures.append(temperature)
        avg_temperature = mean(sporulation_temperatures)
        if (
            leaf_wetness <= sporulation_leaf_wetness_threshold
            and avg_humidity < sporulation_min_humidity
        ) or avg_temperature < sporulation_min_temperature:
            return sporulation_datetime, sporulation_datetime_rowindex

    sporulation_datetime = processed_data["datetime"][i]
    sporulation_datetime_rowindex = i

    return sporulation_datetime, sporulation_datetime_rowindex


def launch_sporulation(
    processed_data,
    infection_datetime_rowindex,
    end_incubation_datetime_rowindex,
    sporulation_leaf_wetness_threshold,
    sporulation_min_humidity,
    sporulation_min_temperature,
    sporulation_min_darkness_hours,
    measurement_time_interval,
    longitude,
    latitude,
    elevation,
    algorithmic_time_steps,
):
    """
    Function that launches sporulation events.

    """

    sporulation_datetimes = []
    sporulation_datetime_rowindexes = []

    for i in range(
        end_incubation_datetime_rowindex,
        len(processed_data.index),
        algorithmic_time_steps,
    ):
        (
            sporulation_datetime,
            sporulation_datetime_rowindex,
        ) = sporulation(
            processed_data,
            i,
            sporulation_leaf_wetness_threshold,
            sporulation_min_humidity,
            sporulation_min_temperature,
            sporulation_min_darkness_hours,
            measurement_time_interval,
            longitude,
            latitude,
            elevation,
            algorithmic_time_steps,
        )
        if sporulation_datetime is not None:
            sporulation_datetimes.append(sporulation_datetime)
            sporulation_datetime_rowindexes.append(sporulation_datetime_rowindex)

    return sporulation_datetimes, sporulation_datetime_rowindexes
