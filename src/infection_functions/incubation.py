"""
Incubation algorithm after successful primary or secondary infection events.

"""

import datetime
from math import ceil


def get_incubation_days(mean_daily_temperature):
    """
    Function to return the estimated incubation period in days after a successful infection event.

    """

    incubation_days = (
        132.2684985
        - 22.75371914 * mean_daily_temperature
        + 1.608549159 * mean_daily_temperature**2
        - 0.05257104866 * mean_daily_temperature**3
        + 0.0006564062872 * mean_daily_temperature**4
    )

    return incubation_days


def launch_incubation(
    processed_data,
    infection_datetime,
    infection_datetime_rowindex,
    mean_daily_temperatures,
    measurement_time_interval,
):
    """
    Function to launch incubation event.

    """
    incubation_progress = 0
    is_incubation_complete = False
    first_incubation_day = infection_datetime.date()
    incubation_day = first_incubation_day

    while incubation_progress < 1 and incubation_day in mean_daily_temperatures.keys():
        mean_daily_temperature = mean_daily_temperatures[incubation_day]
        incubation_days = get_incubation_days(mean_daily_temperature)
        incubation_progress_step = 1 / incubation_days
        incubation_progress += incubation_progress_step
        incubation_day += datetime.timedelta(days=1)

    if incubation_progress >= 1:
        is_incubation_complete = True

    if is_incubation_complete:
        last_incubation_day = incubation_day
        total_incubation_days = (last_incubation_day - first_incubation_day).days

        # Calculating the rowindex at which incubation ends, i.e. converting days into numbers of rows (defined by measurement interval in minutes):
        # i.e. we convert the number of days into number of index rows by:
        # converting the incubation days into minutes (days * 24hours * 60minutes) and then dividing by the measurement interval in minutes.
        # We finally round up with ceil() to get the highest rounded integer value, as we're dealing with row indices.
        end_incubation_datetime_rowindex = infection_datetime_rowindex + ceil(
            total_incubation_days
            * 24  # days to hours conversion
            * 60  # hours to minutes conversion
            / measurement_time_interval  # minutes to measurement interval conversion
        )
        end_incubation_datetime = processed_data["datetime"][end_incubation_datetime_rowindex]
    else:
        return None, None, None

    return incubation_days, end_incubation_datetime, end_incubation_datetime_rowindex
