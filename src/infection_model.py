"""
Script calling the specific infection algorithm submodules and functions.

"""
import sys

import pandas as pd
from infection_functions import (
    incubation,
    oospore_maturation,
    primary_infection,
    secondary_infection,
    sporangia_density,
    spore_lifespan,
    sporulation,
)

# Global variable, defining the number of infection events that we will store and print as output.
number_of_infection_events = 10


""" Returning list of infection events' datetimes and properties """


def get_infection_events_dictionary(
    oospore_maturation_date,
    oospore_germination_datetime,
    oospore_dispersion_datetime,
    oospore_infection_datetime,
    incubation_days,
    end_incubation_datetime,
    sporulation_datetimes,
    sporangia_densities,
    spore_lifespan_days,
    secondary_infections_datetimes,
    # collateral_incubation_days,
    # collateral_sporulation_datetime,
    # collateral_sporangia_counts,
    # collateral_spore_lifespan_days,
    # collateral_secondary_infections_datetimes
):
    """
    Function building a dictionary of infection event datetimes and properties, such as oospore dispersion date and final sporangia densities.
    Used to print out major information from each InfectionEvent object.

    """
    infection_events = {
        "oospore_maturation": oospore_maturation_date,
        "oospore_germination": oospore_germination_datetime,
        "oospore_dispersion": oospore_dispersion_datetime,
        "oospore_infection": oospore_infection_datetime,
        "incubation_days": incubation_days,
        "completed_incubation": end_incubation_datetime,
        "sporulations": sporulation_datetimes,
        "sporangia_densities": sporangia_densities,
        "spore_lifespan_days": spore_lifespan_days,
        "secondary_infections": secondary_infections_datetimes,
        # "collateral_incubation_days": collateral_incubation_days,
        # "collateral_sporulations": collateral_sporulation_datetimes,
        # "collateral_sporangia_counts": collateral_sporangia_counts,
        # "collateral_spore_lifespan_days": collateral_spore_lifespan_days,
        # "collateral_secondary_infections": collateral_secondary_infections_datetimes,
    }
    return infection_events


def get_oospore_maturation_date(
    processed_data,
    model_parameters,
    standard_colformats,
    timezone,
    daily_temperatures,
    daily_mean_temperatures,
    logfile,
):
    """
    Function directing the determination of oospore maturation date, a unique date per season, thus only computed once or manually inserted.

    """

    """ Determine oospore maturation date (aka date of readiness) """

    try:
        oospore_maturation_date = model_parameters["oospore_maturation_date"]
        oospore_maturation_base_temperature = model_parameters[
            "oospore_maturation_base_temperature"
        ]
        oospore_sum_degree_days_maturation_threshold = model_parameters[
            "oospore_maturation_sum_degree_days_threshold"
        ]
    except TypeError:
        with open(logfile, "a") as logf:
            logf.write(
                "\nRun Infection Model Error: could not correctly read or send parameters from config file to oospore maturation date determination function.\n"
            )
    if oospore_maturation_date is None:
        with open(logfile, "a") as logf:
            logf.write("\nNo pre-set oospore maturation date.")
        (
            oospore_maturation_date,
            oospore_maturation_datetime_rowindex,
        ) = oospore_maturation.oospore_maturation(
            processed_data,
            oospore_maturation_base_temperature,
            oospore_sum_degree_days_maturation_threshold,
            daily_temperatures,
            daily_mean_temperatures,
        )
    else:
        oospore_maturation_date = pd.to_datetime(
            oospore_maturation_date, format=standard_colformats[0]
        ).tz_localize(timezone)
        oospore_maturation_datetime_rowindex = processed_data.index.get_loc(
            processed_data[processed_data["datetime"] == oospore_maturation_date].index[
                0
            ]
        )
        with open(logfile, "a") as logf:
            logf.write(
                f"\nLoading oospore maturation date from config file: {oospore_maturation_date}\n"
            )

    if oospore_maturation_date is None:
        log_message = "\nWARNING: threshold conditions for oospore maturation not reached. Date of oospore maturation could not be determined. Model run interrupted.\n"
        with open(logfile, "a") as logf:
            logf.write(log_message)
        print(log_message)
        sys.exit()
    else:
        with open(logfile, "a") as logf:
            logf.write(
                f"\nOospore maturation date computationally determined on day: {oospore_maturation_date}\n"
            )

    return oospore_maturation_date, oospore_maturation_datetime_rowindex


""" Main function coordinating the call of infection algorithms """


def run_infection_model(  # noqa: C901
    processed_data,
    model_parameters,
    start_event_rowindex,
    oospore_maturation_date,
    daily_mean_temperatures,
    algorithmic_time_steps,
    logfile,
    oospore_infection_datetimes,
):
    """
    Main function directing the steps of the full infection prediction model.

    argument1
    : processed time series pandas dataframe

    argument2
    : dictionary of model parameters

    argument3
    : timeseries row index from which computation will start

    arguemnt4
    : computational time steps to be used in successive runs of datetime search loops

    return
    : dicionary of infection events' datetimes and properties

    """
    measurement_time_interval = model_parameters["measurement_time_interval"]

    """ Determine primary infections (aka oospore infections) """
    try:
        oospore_germination_algorithm = model_parameters[
            "oospore_germination_algorithm"
        ]
        oospore_germination_relative_humidity_threshold = model_parameters[
            "oospore_germination_relative_humidity_threshold"
        ]
        oospore_germination_base_temperature = model_parameters[
            "oospore_germination_base_temperature"
        ]
        oospore_germination_base_duration = model_parameters[
            "oospore_germination_base_duration"
        ]
        oospore_germination_leaf_wetness_threshold = model_parameters[
            "oospore_germination_leaf_wetness_threshold"
        ]
        moisturization_temperature_threshold = model_parameters[
            "moisturization_temperature_threshold"
        ]
        moisturization_rainfall_threshold = model_parameters[
            "moisturization_rainfall_threshold"
        ]
        moisturization_rainfall_period = model_parameters[
            "moisturization_rainfall_period"
        ]
    except TypeError:
        with open(logfile, "a") as logf:
            logf.write(
                "\nRun Infection Model Error: could not correctly read or send parameters from config file to soil infection determination functions.\n"
            )

    """ Oospore germination """

    (
        oospore_germination_datetime,
        oospore_germination_datetime_rowindex,
    ) = primary_infection.oospore_germination(
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
    )
    if oospore_germination_datetime is None:
        events = get_infection_events_dictionary(
            oospore_maturation_date,
            *[None] * (number_of_infection_events - 1),
        )
        return events

    """ Oospore dispersion (rain splashing) """

    oospore_dispersion_rainfall_threshold = model_parameters[
        "oospore_dispersion_rainfall_threshold"
    ]
    oospore_dispersion_latency = model_parameters["oospore_dispersion_latency"]

    (
        oospore_dispersion_datetime,
        oospore_dispersion_datetime_rowindex,
        stop_oospore_dispersion_latency_rowindex,
    ) = primary_infection.oospore_dispersion(  ## IS IT REDUNDANT GIVEN THAT WE LAUNCH THE LOOP AFTER ANYWAYS IF NO RESULT?
        processed_data,
        measurement_time_interval,
        oospore_germination_datetime_rowindex,
        oospore_dispersion_rainfall_threshold,
        oospore_dispersion_latency,
        algorithmic_time_steps,
    )

    if oospore_dispersion_datetime is None:
        (
            oospore_dispersion_datetime,
            oospore_dispersion_datetime_rowindex,
        ) = primary_infection.launch_dispersion_loop(
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
        )

    if oospore_dispersion_datetime is None:
        events = get_infection_events_dictionary(
            oospore_maturation_date,
            oospore_germination_datetime,
            *[None] * (number_of_infection_events - 2),
        )
        return events

    """ Oospore infection """

    oospore_infection_leaf_wetness_latency = model_parameters[
        "oospore_infection_leaf_wetness_latency"
    ]
    oospore_infection_base_temperature = model_parameters[
        "oospore_infection_base_temperature"
    ]
    oospore_infection_sum_degree_hours_threshold = model_parameters[
        "oospore_infection_sum_degree_hours_threshold"
    ]
    (
        oospore_infection_datetime,
        oospore_infection_datetime_rowindex,
    ) = primary_infection.oospore_infection(
        processed_data,
        measurement_time_interval,
        oospore_dispersion_datetime_rowindex,
        oospore_infection_leaf_wetness_latency,
        oospore_infection_base_temperature,
        oospore_infection_sum_degree_hours_threshold,
        algorithmic_time_steps,
    )

    if oospore_infection_datetime is None:
        (
            oospore_infection_datetime,
            oospore_infection_datetime_rowindex,
        ) = primary_infection.launch_infection_loop(
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
        )

    if oospore_infection_datetime is None:
        events = get_infection_events_dictionary(
            oospore_maturation_date,
            oospore_germination_datetime,
            oospore_dispersion_datetime,
            *[None] * (number_of_infection_events - 3),
        )
        return events
    # Cheking whether the oospore_infection_datetime has already been found, so that only one incubation event is launched per same datetime.
    else:
        is_already_found = False
        with open(oospore_infection_datetimes, "r") as f:
            lines = f.readlines()
        if len(lines) == 0:
            with open(oospore_infection_datetimes, "a") as f:
                f.write(str(oospore_infection_datetime) + "\n")
        else:
            for line in lines:
                if str(oospore_infection_datetime) in line:
                    is_already_found = True
            if is_already_found:
                events = get_infection_events_dictionary(
                    oospore_maturation_date,
                    oospore_germination_datetime,
                    oospore_dispersion_datetime,
                    *[None] * (number_of_infection_events - 3),
                )
                return events
            else:
                with open(oospore_infection_datetimes, "a") as f:
                    f.write(str(oospore_infection_datetime) + "\n")

    """ Incubation """
    incubation_days, end_incubation_datetime, end_incubation_datetime_rowindex = incubation.launch_incubation(
        processed_data,
        oospore_infection_datetime,
        oospore_infection_datetime_rowindex,
        daily_mean_temperatures,
        measurement_time_interval,
    )

    if incubation_days is None:
        events = get_infection_events_dictionary(
            oospore_maturation_date,
            oospore_germination_datetime,
            oospore_dispersion_datetime,
            oospore_infection_datetime,
            *[None] * (number_of_infection_events - 4),
        )
        return events

    """ Sporulation """

    sporulation_leaf_wetness_threshold = model_parameters[
        "sporulation_leaf_wetness_threshold"
    ]
    sporulation_min_humidity = model_parameters["sporulation_min_humidity"]
    sporulation_min_temperature = model_parameters["sporulation_min_temperature"]
    sporulation_min_darkness_hours = model_parameters["sporulation_min_darkness_hours"]
    longitude = model_parameters["longitude"]
    latitude = model_parameters["latitude"]
    elevation = model_parameters["elevation"]

    (
        sporulation_datetimes,
        sporulation_datetime_rowindexes,
    ) = sporulation.launch_sporulation(
        processed_data,
        oospore_infection_datetime_rowindex,
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
    )

    if not sporulation_datetimes:  # check if sporulation_datetimes list is empty
        events = get_infection_events_dictionary(
            oospore_maturation_date,
            oospore_germination_datetime,
            oospore_dispersion_datetime,
            oospore_infection_datetime,
            incubation_days,
            end_incubation_datetime,
            *[None] * (number_of_infection_events - 6),
        )
        return events

    """ Sporangia density """

    # In counts of sporangia per square centimeter of leaf

    sporangia_latency = model_parameters["sporangia_latency"]
    sporangia_min_temperature = model_parameters["sporangia_min_temperature"]
    sporangia_max_temperature = model_parameters["sporangia_max_temperature"]
    sporangia_max_density = model_parameters["sporangia_max_density"]

    sporangia_densities = sporangia_density.launch_sporangia_densities(
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
    )

    """ Spore lifespan """

    saturation_vapor_pressure = model_parameters["saturation_vapor_pressure"]
    spore_lifespan_constant = model_parameters["spore_lifespan_constant"]

    spore_lifespan_days = spore_lifespan.launch_spore_lifespans(
        processed_data,
        saturation_vapor_pressure,
        spore_lifespan_constant,
        sporulation_datetime_rowindexes,
    )

    """ Secondary infections """

    secondary_infection_min_temperature = model_parameters[
        "secondary_infection_min_temperature"
    ]
    secondary_infection_max_temperature = model_parameters[
        "secondary_infection_max_temperature"
    ]
    secondary_infection_leaf_wetness_latency = model_parameters[
        "secondary_infection_leaf_wetness_latency"
    ]
    secondary_infection_sum_degree_hours_threshold = model_parameters[
        "secondary_infection_sum_degree_hours_threshold"
    ]

    (
        secondary_infections_datetimes,
        secondary_infections_datetimes_rowindexes,
    ) = secondary_infection.launch_secondary_infections(
        processed_data,
        sporulation_datetime_rowindexes,
        spore_lifespan_days,
        secondary_infection_min_temperature,
        secondary_infection_max_temperature,
        secondary_infection_leaf_wetness_latency,
        secondary_infection_sum_degree_hours_threshold,
        measurement_time_interval,
        algorithmic_time_steps,
    )

    # """ Collateral secondary infections """
    #
    # # Re-launching incubation algorithm and start over infection as long as secondary infections are found
    # collateral_incubation_days = None
    # collateral_sporulation_datetime = None
    # collateral_sporangia_counts = None
    # collateral_spore_lifespan_days = None
    # collateral_secondary_infections_datetimes = None
    #
    # for (
    #     secondary_infection_datetime_rowindex
    # ) in secondary_infections_datetimes_rowindexes:
    #     secondary_infection_datetime = processed_data["datetime"][
    #         secondary_infection_datetime_rowindex
    #     ]
    #     (
    #         collateral_incubation_days,
    #         end_incubation_datetime_rowindex,
    #     ) = incubation.launch_incubation(
    #         secondary_infection_datetime,
    #         secondary_infection_datetime_rowindex,
    #         daily_mean_temperatures,
    #         measurement_time_interval,
    #     )
    #
    #     if collateral_incubation_days is not None:
    #         (
    #             collateral_sporulation_datetime,
    #             collateral_sporulation_datetime_rowindex,
    #         ) = sporulation.launch_sporulation(
    #             processed_data,
    #             secondary_infection_datetime_rowindex,
    #             end_incubation_datetime_rowindex,
    #             sporulation_leaf_wetness_threshold,
    #             sporulation_min_humidity,
    #             sporulation_min_temperature,
    #             sporulation_min_darkness_hours,
    #             measurement_time_interval,
    #             longitude,
    #             latitude,
    #             elevation,
    #             algorithmic_time_steps,
    #         )
    #
    #         if collateral_sporulation_datetime_rowindex is not None:
    #             if collateral_sporulation_datetime_rowindex <= len(processed_data.index) - 1:
    #                 collateral_sporangia_counts = sporangia_density.launch_sporangia_counts(
    #                     processed_data,
    #                     measurement_time_interval,
    #                     longitude,
    #                     latitude,
    #                     elevation,
    #                     collateral_sporulation_datetime_rowindex,
    #                     sporangia_latency,
    #                     sporangia_min_temperature,
    #                     sporangia_max_temperature,
    #                     sporangia_max_density,
    #                     algorithmic_time_steps,
    #                 )
    #
    #                 collateral_spore_lifespan_days = spore_death.launch_spore_lifespans(
    #                     processed_data,
    #                     saturation_vapor_pressure,
    #                     spore_lifespan_constant,
    #                     collateral_sporangia_counts,
    #                 )
    #
    #                 (
    #                     collateral_secondary_infections_datetimes,
    #                     collateral_secondary_infections_datetimes_rowindexes,
    #                 ) = secondary_infection.launch_secondary_infections(
    #                     processed_data,
    #                     collateral_spore_lifespan_days,
    #                     secondary_infection_min_temperature,
    #                     secondary_infection_max_temperature,
    #                     secondary_infection_leaf_wetness_latency,
    #                     secondary_infection_sum_degree_hours_threshold,
    #                     measurement_time_interval,
    #                     algorithmic_time_steps,
    #                 )

    """ Returning list of infection events' datetimes and properties """
    events = get_infection_events_dictionary(
        oospore_maturation_date,
        oospore_germination_datetime,
        oospore_dispersion_datetime,
        oospore_infection_datetime,
        incubation_days,
        end_incubation_datetime,
        sporulation_datetimes,
        sporangia_densities,
        spore_lifespan_days,
        secondary_infections_datetimes,
        # collateral_incubation_days,
        # collateral_sporulation_datetime,
        # collateral_sporangia_counts,
        # collateral_spore_lifespan_days,
        # collateral_secondary_infections_datetimes,
    )

    return events
