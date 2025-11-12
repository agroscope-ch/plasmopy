"""
Secondary infection algorithms.

"""

from math import ceil, floor
from statistics import mean


def secondary_infection(
    processed_data,
    sporulation_datetime_rowindex,
    spore_lifespan,
    secondary_infection_min_temperature,
    secondary_infection_max_temperature,
    secondary_infection_leaf_wetness_latency,
    secondary_infection_sum_degree_hours_threshold,
    measurement_time_interval,
    algorithmic_time_steps,
):
    """
    Algorithm to calculate whether secondary infections can occure given current
    meteorological conditions and the previously computed spore lifespans.

    """

    secondary_infection_datetimes = []
    secondary_infection_datetime_rowindexes = []

    # Finding rowindex for end of spore lifespan, from the lifespan in days computed in the spore death algorithm.
    # We need to convert from days to hours (* 24) and to minutes (* 60) and
    # then consider the measurement time interval (by divinding by the measurement_time_interval in minutes).
    end_of_lifespan_rowindex = ceil(
        sporulation_datetime_rowindex
        + spore_lifespan * 24 * 60 / measurement_time_interval
    )

    # We make sure that the estimated rowindex does not go over the length of the dataframe.
    end_of_lifespan_rowindex = min(
        end_of_lifespan_rowindex, len(processed_data.index) - 1
    )
    no_leaf_wetness_minutes_counter = 0
    sum_degree_hours = 0
    sum_degree_hours_minutes_counter = 0

    for i in range(
        sporulation_datetime_rowindex,
        end_of_lifespan_rowindex
        + 1,  # we need to add +1 for Python's range function to actually loop through the last index in the foor loop
        algorithmic_time_steps,
    ):
        temperature = processed_data["temperature"][i]
        leaf_wetness = processed_data["leaf_wetness"][i]

        # Temperature thresholds
        if (
            temperature < secondary_infection_min_temperature
            or temperature > secondary_infection_max_temperature
        ):
            continue

        # Sum degree hours threshold
        if leaf_wetness == 0:
            no_leaf_wetness_minutes_counter += (
                measurement_time_interval * algorithmic_time_steps
            )
            if (
                no_leaf_wetness_minutes_counter
                > secondary_infection_leaf_wetness_latency
            ):
                break
        else:
            no_leaf_wetness_minutes_counter = 0
            sum_degree_hours_minutes_counter += (
                measurement_time_interval * algorithmic_time_steps
            )
            if sum_degree_hours_minutes_counter >= 60:
                start_hourly_rowindex = max(
                    0, i - floor(60 / measurement_time_interval)
                )
                stop_hourly_rowindex = min(i + 1, len(processed_data.index))
                mean_hourly_temperature = mean(
                    processed_data["temperature"][
                        start_hourly_rowindex:stop_hourly_rowindex
                    ]
                )
                sum_degree_hours += mean_hourly_temperature
                if sum_degree_hours >= secondary_infection_sum_degree_hours_threshold:
                    secondary_infection_datetime = processed_data["datetime"][i]
                    secondary_infection_datetime_rowindex = i
                    secondary_infection_datetimes.append(secondary_infection_datetime)
                    secondary_infection_datetime_rowindexes.append(
                        secondary_infection_datetime_rowindex
                    )

    return (
        secondary_infection_datetimes,
        secondary_infection_datetime_rowindexes,
    )


def launch_secondary_infections(
    processed_data,
    sporulation_datetime_rowindexes,
    spore_lifespan_days,
    secondary_infection_min_temperature,
    secondary_infection_max_temperature,
    secondary_infection_leaf_wetness_latency,
    secondary_infection_sum_degree_hours_threshold,
    measurement_time_interval,
    fast_mode,
    algorithmic_time_steps,
):
    """
    Launch secondary infection events from all succesful sporulation events.

    """
    secondary_infections_datetimes = []
    secondary_infections_datetimes_rowindexes = []

    for i, sporulation_datetime_rowindex in enumerate(sporulation_datetime_rowindexes):
        (
            local_secondary_infection_datetimes,
            local_secondary_infection_datetime_rowindexes,
        ) = secondary_infection(
            processed_data,
            sporulation_datetime_rowindex,
            spore_lifespan_days[i],
            secondary_infection_min_temperature,
            secondary_infection_max_temperature,
            secondary_infection_leaf_wetness_latency,
            secondary_infection_sum_degree_hours_threshold,
            measurement_time_interval,
            algorithmic_time_steps,
        )
        if local_secondary_infection_datetimes:  # Check if list is not empty
            secondary_infections_datetimes.extend(local_secondary_infection_datetimes)
            secondary_infections_datetimes_rowindexes.extend(
                local_secondary_infection_datetime_rowindexes
            )
            if fast_mode:
                break

    return secondary_infections_datetimes, secondary_infections_datetimes_rowindexes
