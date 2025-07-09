"""
Primary infection algorithms.

"""
from math import ceil

""" Stage 1: oospore germination """


def oospore_germination(  # noqa: C901
    processed_data,
    start_event_rowindex,
    oospore_germination_relative_humidity_threshold,
    oospore_germination_base_temperature,
    oospore_germination_base_duration,
    oospore_germination_leaf_wetness_threshold,
    oospore_germination_algorithm,
    moisturization_temperature_threshold,
    moisturization_rainfall_threshold,
    moisturization_rainfall_period,
    measurement_time_interval,
    algorithmic_time_steps,
    logfile,
):
    """
    Function returning the datetime (datetime and row index) at which activation
    conditions for oospore germination in soil are met.

    return
    : oospore_germination_datetime, oospore_germination_datetime_rowindex

    """
    oospore_germination_datetime = None
    oospore_germination_datetime_rowindex = None

    cumulative_datetime = 0
    start_conditions_datetime = processed_data["datetime"][start_event_rowindex]

    # If specified, use algorithm 1, oospore development
    if oospore_germination_algorithm == 1:
        for i in range(
            start_event_rowindex, len(processed_data.index) - 1, algorithmic_time_steps
        ):
            if processed_data["temperature"][i] > oospore_germination_base_temperature:
                if (
                    processed_data["humidity"][i]
                    > oospore_germination_relative_humidity_threshold
                    or processed_data["leaf_wetness"][i]
                    >= oospore_germination_leaf_wetness_threshold
                ):
                    cumulative_datetime = (
                        processed_data["datetime"][i] - start_conditions_datetime
                    )
                    cumulative_datetime = cumulative_datetime.total_seconds()
                    if (
                        cumulative_datetime >= oospore_germination_base_duration * 3600
                    ):  # hours to seconds conversion
                        oospore_germination_datetime = processed_data["datetime"][i]
                        oospore_germination_datetime_rowindex = i
                        break
                else:
                    start_conditions_datetime = processed_data["datetime"][i]

    ## If specified, use algorithm 2, moisture penetration

    elif oospore_germination_algorithm == 2:
        ## Algorithm implemented so that the cumulative rainfall check is validated before the temperature check.

        #     # Define the start of the time window in which temperature and rainfall conditions must be met.
        #     # This first index will dynamically shift forward with the time window as long as we don't meet the conditions.
        #     timewindow_start_rowindex = start_event_rowindex
        #     for i in range(start_event_rowindex, len(processed_data.index), algorithmic_time_steps):
        #         # Compute the time difference within the selected time window while the for loop runs through the full dataset.
        #         rainfall_period = processed_data["datetime"][i] - processed_data["datetime"][timewindow_start_rowindex]
        #         # If the time window is still within the time period limit defined in the config file,
        #         # then check if the rainfall accumulation and temperature conditions are met.
        #         if rainfall_period <= timedelta(hours = moisturization_rainfall_period):
        #             # Compute the total cumulated rainfall within the considered time window
        #             cumulated_rainfall = sum(processed_data["rainfall"][timewindow_start_rowindex:i]) * measurement_time_interval / 60
        #             # If we obtained as much rainfall as needed by the conditions, then check the temperature.
        #             if cumulated_rainfall >= moisturization_rainfall_threshold:
        #                 temperature_check = True
        #                 # Run a for loop throughout the full time window at the defined algorithmic time step,
        #                 # temperature must be always be above threshold,
        #                 # otherwise we break the loop and continue to next iteration.
        #                 for j in range(timewindow_start_rowindex, i, algorithmic_time_steps):
        #                     if processed_data["temperature"][j] <= moisturization_temperature_threshold:
        #                         temperature_check = False
        #                         break
        #                 if temperature_check is False:
        #                     continue
        #                 # If the temperature check is passed, we found our datetimes and pass them to the function return.
        #                 # If the conditions are not met, then we simply continue to the next iteration in the initial for loop.
        #                 else:
        #                     oospore_germination_datetime = processed_data["datetime"][i]
        #                     oospore_germination_datetime_rowindex = i
        #                     break
        #         # We get to this point if the temperature and rainfall accumulation conditions are never met
        #         # and if we already reached the end of the allowed time window, as defined in the config file.
        #         # In this case, we must update our time window range by updating the first time windows index.
        #         else:
        #             timewindow_start_rowindex += algorithmic_time_steps

        # Define number of row indexes corresponding to the required time period of rainfall
        rainfall_period_range = int(
            moisturization_rainfall_period * 60 / measurement_time_interval
        )
        # Start the search for the datetimes where we obtain the required cumulative rainfall
        for i in range(
            start_event_rowindex, len(processed_data.index), algorithmic_time_steps
        ):
            # Allow the possibility that the required cumulative rainfall is obtained in less than
            # the allowed period, so to reach all the rows even approaching the end of the dataset.
            rainfall_period_index = min(
                i + rainfall_period_range, len(processed_data.index) - 1
            )
            # Extract the hourly rainfall intensities values and correct them by the sampling interval factor.
            # i.e. convert the measurement time interval from minutes to hours and multiply it by the
            # hourly rainfall intensity values, so to obtain an effective cumulative rainfall list of values
            # corresponding to the effective sampling interval.
            rainfalls = tuple(
                (measurement_time_interval / 60) * rainfall
                for rainfall in processed_data["rainfall"][i:rainfall_period_index]
            )
            # If the sum is equal or exceeds the required threshold, then continue to find the exact row index at
            # which we reached the condition, so to capture the earlist datetime also when this happens
            # earlier than the maximum allowed time period.
            if sum(rainfalls) >= moisturization_rainfall_threshold:
                running_sum = 0
                j = 0
                for index, value in enumerate(rainfalls):
                    running_sum += value
                    # When the running sum reaches the threshold, we store the latest row index and we break the loop.
                    if running_sum >= moisturization_rainfall_threshold:
                        j = index
                        break
                successful_cumulative_rainfall_index = i + j
                # We extract the temperatures on the given subset of indexes.
                temperatures = tuple(
                    processed_data["temperature"][
                        i:successful_cumulative_rainfall_index
                    ]
                )
                # We check that the temperature never drops below the allowed threshold across the whole period of
                # successful cumulative rainfall.
                if any(
                    temperature <= moisturization_temperature_threshold
                    for temperature in temperatures
                ):
                    # If this happens, we move onto the next iteration, starting all over again.
                    continue
                # If the temperature check is successful, then we store the row index at the end of the
                # rainfall accumulation period as our germination datetime.
                else:
                    oospore_germination_datetime = processed_data["datetime"][
                        successful_cumulative_rainfall_index
                    ]
                    oospore_germination_datetime_rowindex = (
                        successful_cumulative_rainfall_index
                    )
                    break

        # rainfall_period_range = int(moisturization_rainfall_period * 60 / measurement_time_interval)
        # for i in range(
        #     start_event_rowindex, len(processed_data.index) - rainfall_period_range, algorithmic_time_steps
        # ):
        #     rainfall_period_index = int(i + rainfall_period_range)
        #     temperatures = tuple(processed_data["temperature"][i:rainfall_period_index])
        #     # Checking that the temperature condition is met throughout the required rainfall period.
        #     if any(temperature <= moisturization_temperature_threshold for temperature in temperatures):
        #         continue
        #     else:
        #         # Cumulative rainfall is computed as the sum within the interval, then converted to mm/hr depending on the sampling interval.
        #         cumulative_rainfall = sum(processed_data["rainfall"][i:rainfall_period_index]) * measurement_time_interval / 60
        #     # If temperature conditions are always met in the range, then we check that the needed rainfall has been accumulated.
        #     if cumulative_rainfall >= moisturization_rainfall_threshold:
        #         # If yes, then we have found the germination datetime, and we break the loop.
        #         # If no, we do nothing, and the loop continues adding rainfall to the next iteration.
        #         oospore_germination_datetime = processed_data["datetime"][rainfall_period_index]
        #         oospore_germination_datetime_rowindex = rainfall_period_index
        #         break
        #     else:
        #         continue

        ## Algorithm implemented so that the temperature check is validated first, makes the algorithm faster.
        # cumulative_rainfall = 0
        # for i in range(
        #     start_event_rowindex, len(processed_data.index), algorithmic_time_steps
        # ):
        #     # We run the whole dataset checking for temperature, as soon as T is > threshold, we start
        #     # counting the cumulative rainfall.
        #     if processed_data["temperature"][i] > moisturization_temperature_threshold:
        #         # Converting the rainfall intensity per hour into rainfall intensity per measurement interval in minutes
        #         cumulative_rainfall += (
        #             processed_data["rainfall"][i] * measurement_time_interval / 60
        #         )  # conversion from hours to minutes
        #         cumulative_datetime = (
        #             processed_data["datetime"][i] - start_conditions_datetime
        #         )
        #         # We calculate the elapsed time in seconds
        #         cumulative_datetime = cumulative_datetime.total_seconds()
        #         # We check that the required elapsed time for the cumulative rainfall has not been exceeded.
        #         if (
        #             cumulative_datetime <= moisturization_rainfall_period * 3600
        #         ):  # hours to seconds conversion
        #             # If yes, then we check that the needed rainfall has been accumulated.
        #             if cumulative_rainfall >= moisturization_rainfall_threshold:
        #                 # If yes, then we have found the dispersion datetime, and we break the loop.
        #                 # If no, we do nothing, and the loop continues adding rainfall to the next iteration.
        #                 oospore_germination_datetime = processed_data["datetime"][i]
        #                 oospore_germination_datetime_rowindex = i
        #                 break
        #     else:
        #         start_conditions_datetime = processed_data["datetime"][i]
        #         cumulative_rainfall = 0

    else:
        with open(logfile, "a") as logf:
            logf.write(
                "\nWARNING: could not read a valid oospore germination algorithm number from the config file.\n"
            )
    return (oospore_germination_datetime, oospore_germination_datetime_rowindex)


""" Stage 2: oospore dispersion """


def oospore_dispersion(
    processed_data,
    measurement_time_interval,
    oospore_germination_datetime_rowindex,
    oospore_dispersion_rainfall_threshold,
    oospore_dispersion_latency,
    algorithmic_time_steps,
    rerun_stop_oospore_dispersion_latency_rowindex=None,
):
    """
    Function returning the datetime (datetime and row index) at which activation
    conditions for oospore dispersion from soil to vegetation (via rain splashing
    modelled as rainfall intensity) are met.

    return
    : oospore_dispersion_datetime, oospore_dispersion_datetime_rowindex, stop_dispersion_latency_rowindex

    """

    # Stage 2 can only happen within a certain number of hours of latency (argument: "splashing latency" [oospore_dispersion_latency], in hours) after oospore germination is complete.
    # The maximum row for calculation then can be found at:
    # starting_index (completed oospore germination) + splashing latency (* 60 for hours-to-minutes conversion) / time inverval between measurements (in minutes).

    if rerun_stop_oospore_dispersion_latency_rowindex is not None:
        stop_oospore_dispersion_latency_rowindex = (
            rerun_stop_oospore_dispersion_latency_rowindex
        )
    else:
        stop_oospore_dispersion_latency_rowindex = ceil(
            oospore_germination_datetime_rowindex
            + oospore_dispersion_latency
            * 60
            / measurement_time_interval  # hours to minutes conversion
            # minutes to measurement interval conversion ##### NOT THE BEST SOLUTION
        )

    # Making sure that we do not go beyond the maximum dataset size
    stop_oospore_dispersion_latency_rowindex = min(
        stop_oospore_dispersion_latency_rowindex, len(processed_data.index) - 1
    )

    oospore_dispersion_datetime = None
    oospore_dispersion_datetime_rowindex = None
    for i in range(
        oospore_germination_datetime_rowindex,
        stop_oospore_dispersion_latency_rowindex
        + 1,  # we need to add +1 for Python's range function to actually loop through the last index in the for loop
        algorithmic_time_steps,
    ):
        # The oospore_dispersion_rainfall_threshold is provided in mm per hours, however
        # for the comparison to be meaningful, we need to adjust the threshold relatively
        # to the rainfall values per measurement interval. So we divide the hour-threshold by 60 minutes,
        # and we multiply it by the minutes span of the measurement interval.
        adjusted_oospore_dispersion_rainfall_threshold = (
            oospore_dispersion_rainfall_threshold * measurement_time_interval / 60
        )
        if (
            processed_data["rainfall"][i]
            >= adjusted_oospore_dispersion_rainfall_threshold
        ):
            oospore_dispersion_datetime = processed_data["datetime"][i]
            oospore_dispersion_datetime_rowindex = i
            break
    return (
        oospore_dispersion_datetime,
        oospore_dispersion_datetime_rowindex,
        stop_oospore_dispersion_latency_rowindex,
    )


def launch_dispersion_loop(
    processed_data,
    start_event_rowindex,
    oospore_germination_datetime_rowindex,
    oospore_germination_relative_humidity_threshold,
    oospore_germination_base_temperature,
    oospore_germination_base_duration,
    oospore_germination_leaf_wetness_threshold,
    oospore_germination_algorithm,
    moisturization_temperature_threshold,
    moisturization_rainfall_threshold,
    moisturization_rainfall_period,
    oospore_dispersion_rainfall_threshold,
    oospore_dispersion_latency,
    measurement_time_interval,
    algorithmic_time_steps,
    logfile,
):
    """
    Function that launches a loop for dispersion datetime search, in case the first run did not succeed.

    """
    new_start_event_rowindex = start_event_rowindex + algorithmic_time_steps

    oospore_dispersion_datetime = None
    oospore_dispersion_datetime_rowindex = None
    new_oospore_germination_datetime_rowindex = (
        oospore_germination_datetime_rowindex + algorithmic_time_steps
    )

    while (
        oospore_dispersion_datetime is None
        and new_start_event_rowindex < len(processed_data.index)
        and new_oospore_germination_datetime_rowindex < len(processed_data.index)
    ):
        new_oospore_germination_datetime_rowindex += algorithmic_time_steps
        new_oospore_germination_datetime = processed_data["datetime"][
            new_oospore_germination_datetime_rowindex
        ]
        # (
        #     new_oospore_germination_datetime,
        #     new_oospore_germination_datetime_rowindex,
        # ) = oospore_germination(
        #     processed_data,
        #     new_start_event_rowindex,
        #     oospore_germination_relative_humidity_threshold,
        #     oospore_germination_base_temperature,
        #     oospore_germination_base_duration,
        #     oospore_germination_leaf_wetness_threshold,
        #     oospore_germination_algorithm,
        #     moisturization_temperature_threshold,
        #     moisturization_rainfall_threshold,
        #     moisturization_rainfall_period,
        #     measurement_time_interval,
        #     algorithmic_time_steps,
        #     logfile,
        # )
        if (
            new_oospore_germination_datetime is None
            or new_oospore_germination_datetime_rowindex
            == oospore_germination_datetime_rowindex
        ):
            new_start_event_rowindex += algorithmic_time_steps
            # new_oospore_germination_datetime_rowindex += algorithmic_time_steps
            continue
        # elif new_oospore_germination_datetime_rowindex == oospore_germination_datetime_rowindex:
        #     new_start_event_rowindex = oospore_germination_datetime_rowindex + algorithmic_time_steps
        #     continue
        else:
            oospore_germination_datetime_rowindex = (
                new_oospore_germination_datetime_rowindex
            )
            (
                oospore_dispersion_datetime,
                oospore_dispersion_datetime_rowindex,
                stop_oospore_dispersion_latency_rowindex,
            ) = oospore_dispersion(
                processed_data,
                measurement_time_interval,
                oospore_germination_datetime_rowindex,
                oospore_dispersion_rainfall_threshold,
                oospore_dispersion_latency,
                algorithmic_time_steps,
            )
            break

    return oospore_dispersion_datetime, oospore_dispersion_datetime_rowindex


""" Stage 3: oospore infection, i.e. successful primary infection """


def oospore_infection(
    processed_data,
    measurement_time_interval,
    oospore_dispersion_datetime_rowindex,
    oospore_infection_leaf_wetness_latency,
    oospore_infection_base_temperature,
    oospore_infection_sum_degree_hours_threshold,
    algorithmic_time_steps,
):
    """
    Function returning the datetime (datetime and row index) at which activation
    conditions for oospore infection to vegetation are met.

    return
    : oospore_infection_datetime, oospore_infection_datetime_rowindex

    """

    # Finding max rowindex at which conditions must be met for succesful sporulation.
    stop_oospore_infection_latency_rowindex = ceil(
        oospore_dispersion_datetime_rowindex
        + oospore_infection_leaf_wetness_latency
        * 60  # hours to minutes conversion
        / measurement_time_interval  # minutes to measurement interval conversion ##### NOT THE BEST SOLUTION
    )

    # Making sure that we do not go beyond the maximum dataset size
    stop_oospore_infection_latency_rowindex = min(
        stop_oospore_infection_latency_rowindex, len(processed_data.index) - 1
    )

    oospore_infection_datetime = None
    oospore_infection_datetime_rowindex = None
    sum_degree_hours = 0
    no_leaf_wetness_minutes_counter = 0

    for i in range(
        oospore_dispersion_datetime_rowindex,
        len(processed_data.index),
        algorithmic_time_steps,
    ):
        if processed_data["leaf_wetness"][i] == 0:
            no_leaf_wetness_minutes_counter += (
                measurement_time_interval * algorithmic_time_steps
            )
            if no_leaf_wetness_minutes_counter > oospore_infection_leaf_wetness_latency:
                break
        else:
            no_leaf_wetness_minutes_counter = 0
            # The sum_degree_hours is provided in degrees per hour, however
            # for the comparison to be meaningful, we need to adjust the sum relatively
            # to the temeprature values per measurement interval. So we divide the hour-threshold by 60 minutes,
            # and we multiply it by the minutes span of the measurement interval.

            if processed_data["temperature"][i] > oospore_infection_base_temperature:
                sum_degree_hours += (
                    processed_data["temperature"][i] * measurement_time_interval / 60
                )

                if sum_degree_hours >= oospore_infection_sum_degree_hours_threshold:
                    oospore_infection_datetime = processed_data["datetime"][i]
                    oospore_infection_datetime_rowindex = i

                    return (
                        oospore_infection_datetime,
                        oospore_infection_datetime_rowindex,
                    )

    return (
        oospore_infection_datetime,
        oospore_infection_datetime_rowindex,
    )


def launch_infection_loop(
    processed_data,
    measurement_time_interval,
    start_event_rowindex,
    oospore_germination_datetime,
    oospore_germination_datetime_rowindex,
    oospore_germination_relative_humidity_threshold,
    oospore_germination_base_temperature,
    oospore_germination_base_duration,
    oospore_germination_leaf_wetness_threshold,
    oospore_germination_algorithm,
    moisturization_temperature_threshold,
    moisturization_rainfall_threshold,
    moisturization_rainfall_period,
    oospore_dispersion_rainfall_threshold,
    oospore_dispersion_latency,
    oospore_dispersion_datetime_rowindex,
    oospore_infection_leaf_wetness_latency,
    oospore_infection_base_temperature,
    oospore_infection_sum_degree_hours_threshold,
    algorithmic_time_steps,
    logfile,
):
    """
    Function that launches a loop for primary (oospore) infection datetime search, in case the first run did not succeed.

    """

    new_oospore_germination_datetime_rowindex = (
        oospore_germination_datetime_rowindex + algorithmic_time_steps
    )

    oospore_infection_datetime = None
    oospore_infection_datetime_rowindex = None

    while (
        oospore_infection_datetime is None
        and new_oospore_germination_datetime_rowindex < len(processed_data.index)
    ):
        (
            new_oospore_dispersion_datetime,
            new_oospore_dispersion_datetime_rowindex,
            stop_oospore_dispersion_latency_rowindex,
        ) = oospore_dispersion(
            processed_data,
            measurement_time_interval,
            new_oospore_germination_datetime_rowindex,
            oospore_dispersion_rainfall_threshold,
            oospore_dispersion_latency,
            algorithmic_time_steps,
        )
        if new_oospore_dispersion_datetime is None:
            new_oospore_germination_datetime_rowindex += algorithmic_time_steps
            continue
        # if new_oospore_dispersion_datetime is None:
        #     (
        #         oospore_dispersion_datetime,
        #         oospore_dispersion_datetimerowindex,
        #     ) = launch_dispersion_loop(
        #         processed_data,
        #         start_event_rowindex,
        #         oospore_germination_datetime,
        #         oospore_germination_relative_humidity_threshold,
        #         oospore_germination_base_temperature,
        #         oospore_germination_base_duration,
        #         oospore_germination_leaf_wetness_threshold,
        #         oospore_germination_algorithm,
        #         moisturization_temperature_threshold,
        #         moisturization_rainfall_threshold,
        #         moisturization_rainfall_period,
        #         oospore_dispersion_rainfall_threshold,
        #         oospore_dispersion_latency,
        #         measurement_time_interval,
        #         algorithmic_time_steps,
        #         logfile,
        #     )
        #
        #     if oospore_dispersion_datetime is None:
        #         break
        # elif new_oospore_dispersion_datetime == oospore_dispersion_datetime:
        #     new_oospore_germination_datetime_rowindex += algorithmic_time_steps
        #     continue
        else:
            oospore_dispersion_datetime_rowindex = (
                new_oospore_dispersion_datetime_rowindex
            )
            (
                oospore_infection_datetime,
                oospore_infection_datetime_rowindex,
            ) = oospore_infection(
                processed_data,
                measurement_time_interval,
                oospore_dispersion_datetime_rowindex,
                oospore_infection_leaf_wetness_latency,
                oospore_infection_base_temperature,
                oospore_infection_sum_degree_hours_threshold,
                algorithmic_time_steps,
            )
            break

    return oospore_infection_datetime, oospore_infection_datetime_rowindex
