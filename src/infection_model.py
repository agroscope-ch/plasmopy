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
        oospore_maturation_date = model_parameters["oospore_maturation"]["date"]
        oospore_maturation_base_temperature = model_parameters["oospore_maturation"][
            "base_temperature"
        ]
        oospore_sum_degree_days_maturation_threshold = model_parameters[
            "oospore_maturation"
        ]["sum_degree_days_threshold"]
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
    spore_counts_result=None,
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

    argument5
    : optional spore counts analysis result dictionary for continuing from sporulation stage

    return
    : dicionary of infection events' datetimes and properties

    """
    measurement_time_interval = model_parameters["run_settings"][
        "measurement_time_interval"
    ]

    # Initialise all primary-stage outputs to None so the events dictionary
    # is always fully populated regardless of which execution path is taken.
    oospore_germination_datetime = None
    oospore_dispersion_datetime = None
    oospore_infection_datetime = None
    oospore_infection_datetime_rowindex = None
    incubation_days = None
    end_incubation_datetime = None
    end_incubation_datetime_rowindex = None

    # ------------------------------------------------------------------ #
    # Determine execution path from spore counts result.                  #
    # skip_to_sporulation takes precedence over skip_to_dispersion.       #
    # ------------------------------------------------------------------ #
    skip_to_sporulation = spore_counts_result is not None and spore_counts_result.get(
        "skip_to_sporulation"
    )
    skip_to_dispersion = (
        spore_counts_result is not None
        and spore_counts_result.get("skip_to_dispersion")
        and not skip_to_sporulation
    )

    if skip_to_sporulation:
        # -------------------------------------------------------------- #
        # SPORULATION SHORTCUT (condition 2 – percent increase)           #
        # Skip germination / dispersion / infection / incubation and jump #
        # directly to sporulation using the spore-trap datetime.          #
        # -------------------------------------------------------------- #
        with open(logfile, "a") as logf:
            logf.write(
                "\nPercent-increase condition met: "
                "skipping directly to sporulation stage.\n"
            )

        raw_spore_dt = spore_counts_result.get("sporulation_datetime")
        if raw_spore_dt is None:
            with open(logfile, "a") as logf:
                logf.write(
                    "ERROR: sporulation_datetime missing from spore counts result.\n"
                )
            return get_infection_events_dictionary(
                oospore_maturation_date, *[None] * (number_of_infection_events - 1)
            )

        spore_dt = pd.to_datetime(raw_spore_dt)
        if processed_data["datetime"].dt.tz is not None and spore_dt.tzinfo is None:
            spore_dt = spore_dt.tz_localize(processed_data["datetime"].dt.tz)

        closest_idx = (processed_data["datetime"] - spore_dt).abs().argmin()
        shortcut_rowindex = processed_data.index.get_loc(
            processed_data.index[closest_idx]
        )
        end_incubation_datetime = processed_data["datetime"][shortcut_rowindex]
        end_incubation_datetime_rowindex = shortcut_rowindex
        oospore_infection_datetime_rowindex = shortcut_rowindex

        with open(logfile, "a") as logf:
            logf.write(f"Sporulation stage start datetime: {end_incubation_datetime}\n")

    else:
        # -------------------------------------------------------------- #
        # DISPERSION SHORTCUT (condition 1 – flat threshold)              #
        #   or                                                             #
        # NORMAL PATH (no shortcut)                                       #
        #                                                                  #
        # For the dispersion shortcut, germination is skipped and         #
        # oospore_dispersion_datetime is anchored to the spore-trap date. #
        # For the normal path, all primary stages run from scratch.       #
        # Both paths then share the infection and incubation stages.      #
        # -------------------------------------------------------------- #

        if skip_to_dispersion:
            # ---------------------------------------------------------- #
            # DISPERSION SHORTCUT                                         #
            # ---------------------------------------------------------- #
            with open(logfile, "a") as logf:
                logf.write(
                    "\nFlat-threshold condition met: "
                    "skipping to oospore dispersion stage.\n"
                )

            raw_disp_dt = spore_counts_result.get("dispersion_datetime")
            if raw_disp_dt is None:
                with open(logfile, "a") as logf:
                    logf.write(
                        "ERROR: dispersion_datetime missing from spore counts result.\n"
                    )
                return get_infection_events_dictionary(
                    oospore_maturation_date, *[None] * (number_of_infection_events - 1)
                )

            disp_dt = pd.to_datetime(raw_disp_dt)
            if processed_data["datetime"].dt.tz is not None and disp_dt.tzinfo is None:
                disp_dt = disp_dt.tz_localize(processed_data["datetime"].dt.tz)

            closest_idx = (processed_data["datetime"] - disp_dt).abs().argmin()
            oospore_dispersion_datetime_rowindex = processed_data.index.get_loc(
                processed_data.index[closest_idx]
            )
            oospore_dispersion_datetime = processed_data["datetime"][
                oospore_dispersion_datetime_rowindex
            ]

            with open(logfile, "a") as logf:
                logf.write(
                    f"Dispersion stage anchored at datetime: {oospore_dispersion_datetime}\n"
                )

        else:
            # ---------------------------------------------------------- #
            # NORMAL PATH                                                  #
            # ---------------------------------------------------------- #

            """Determine primary infections (aka oospore infections)"""
            try:
                oospore_germination_algorithm = model_parameters["oospore_germination"][
                    "algorithm"
                ]
                oospore_germination_relative_humidity_threshold = model_parameters[
                    "oospore_germination"
                ]["relative_humidity_threshold"]
                oospore_germination_base_temperature = model_parameters[
                    "oospore_germination"
                ]["base_temperature"]
                oospore_germination_base_duration = model_parameters[
                    "oospore_germination"
                ]["base_duration"]
                oospore_germination_leaf_wetness_threshold = model_parameters[
                    "oospore_germination"
                ]["leaf_wetness_threshold"]
                moisturization_temperature_threshold = model_parameters[
                    "oospore_germination"
                ]["moisturization_temperature_threshold"]
                moisturization_rainfall_threshold = model_parameters[
                    "oospore_germination"
                ]["moisturization_rainfall_threshold"]
                moisturization_rainfall_period = model_parameters[
                    "oospore_germination"
                ]["moisturization_rainfall_period"]
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
                return get_infection_events_dictionary(
                    oospore_maturation_date,
                    *[None] * (number_of_infection_events - 1),
                )

            """ Oospore dispersion (rain splashing) """

            oospore_dispersion_rainfall_threshold = model_parameters[
                "oospore_dispersion"
            ]["rainfall_threshold"]
            oospore_dispersion_latency = model_parameters["oospore_dispersion"][
                "latency"
            ]

            (
                oospore_dispersion_datetime,
                oospore_dispersion_datetime_rowindex,
                stop_oospore_dispersion_latency_rowindex,
            ) = primary_infection.oospore_dispersion(
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
                return get_infection_events_dictionary(
                    oospore_maturation_date,
                    oospore_germination_datetime,
                    *[None] * (number_of_infection_events - 2),
                )

        # -------------------------------------------------------------- #
        # Both dispersion-shortcut and normal paths: run infection then   #
        # incubation.  oospore_dispersion_datetime_rowindex is set above. #
        # -------------------------------------------------------------- #

        """ Oospore infection """

        oospore_infection_leaf_wetness_latency = model_parameters["primary_infection"][
            "leaf_wetness_latency"
        ]
        oospore_infection_base_temperature = model_parameters["primary_infection"][
            "base_temperature"
        ]
        oospore_infection_sum_degree_hours_threshold = model_parameters[
            "primary_infection"
        ]["sum_degree_hours_threshold"]

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

        # On the normal path only, fall back to the full re-search loop if
        # the initial infection check returned nothing.
        if oospore_infection_datetime is None and not skip_to_dispersion:
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
            return get_infection_events_dictionary(
                oospore_maturation_date,
                oospore_germination_datetime,
                oospore_dispersion_datetime,
                *[None] * (number_of_infection_events - 3),
            )
        else:
            # Checking whether the oospore_infection_datetime has already been found,
            # so that only one incubation event is launched per same datetime.
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
                    return get_infection_events_dictionary(
                        oospore_maturation_date,
                        oospore_germination_datetime,
                        oospore_dispersion_datetime,
                        *[None] * (number_of_infection_events - 3),
                    )
                else:
                    with open(oospore_infection_datetimes, "a") as f:
                        f.write(str(oospore_infection_datetime) + "\n")

        """ Incubation """
        (
            incubation_days,
            end_incubation_datetime,
            end_incubation_datetime_rowindex,
        ) = incubation.launch_incubation(
            processed_data,
            oospore_infection_datetime,
            oospore_infection_datetime_rowindex,
            daily_mean_temperatures,
            measurement_time_interval,
        )

        if incubation_days is None:
            return get_infection_events_dictionary(
                oospore_maturation_date,
                oospore_germination_datetime,
                oospore_dispersion_datetime,
                oospore_infection_datetime,
                *[None] * (number_of_infection_events - 4),
            )

    # ------------------------------------------------------------------ #
    # All three paths converge here: sporulation and secondary infection. #
    # ------------------------------------------------------------------ #

    """ Sporulation """

    sporulation_leaf_wetness_threshold = model_parameters["sporulation"][
        "leaf_wetness_threshold"
    ]
    sporulation_min_humidity = model_parameters["sporulation"]["min_humidity"]
    sporulation_min_temperature = model_parameters["sporulation"]["min_temperature"]
    sporulation_min_darkness_hours = model_parameters["sporulation"][
        "min_darkness_hours"
    ]
    longitude = model_parameters["site"]["longitude"]
    latitude = model_parameters["site"]["latitude"]
    elevation = model_parameters["site"]["elevation"]
    fast_mode = model_parameters["run_settings"]["fast_mode"]

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
        fast_mode,
        algorithmic_time_steps,
    )

    if not sporulation_datetimes:  # check if sporulation_datetimes list is empty
        return get_infection_events_dictionary(
            oospore_maturation_date,
            oospore_germination_datetime,
            oospore_dispersion_datetime,
            oospore_infection_datetime,
            incubation_days,
            end_incubation_datetime,
            *[None] * (number_of_infection_events - 6),
        )

    """ Sporangia density """

    # In counts of sporangia per square centimeter of leaf

    sporangia_latency = model_parameters["sporangia"]["latency"]
    sporangia_min_temperature = model_parameters["sporangia"]["min_temperature"]
    sporangia_max_temperature = model_parameters["sporangia"]["max_temperature"]
    sporangia_max_density = model_parameters["sporangia"]["max_density"]

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

    saturation_vapor_pressure = model_parameters["spore_lifespan"][
        "saturation_vapor_pressure"
    ]
    spore_lifespan_constant = model_parameters["spore_lifespan"]["constant"]

    spore_lifespan_days = spore_lifespan.launch_spore_lifespans(
        processed_data,
        saturation_vapor_pressure,
        spore_lifespan_constant,
        sporulation_datetime_rowindexes,
    )

    """ Secondary infections """

    secondary_infection_min_temperature = model_parameters["secondary_infection"][
        "min_temperature"
    ]
    secondary_infection_max_temperature = model_parameters["secondary_infection"][
        "max_temperature"
    ]
    secondary_infection_leaf_wetness_latency = model_parameters["secondary_infection"][
        "leaf_wetness_latency"
    ]
    secondary_infection_sum_degree_hours_threshold = model_parameters[
        "secondary_infection"
    ]["sum_degree_hours_threshold"]

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
        fast_mode,
        algorithmic_time_steps,
    )

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
    )

    return events
