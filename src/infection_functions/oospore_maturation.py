"""
Oospore maturation algorithms.

"""


def oospore_maturation(
    processed_data,
    oospore_maturation_base_temperature,
    oospore_maturation_sum_degree_days_threshold,
    daily_temperatures,
    daily_mean_temperatures,
):
    """
    Function returning the datetime (datetime and row index) at which activation
    conditions for oospore maturation are met, in case this was not manually
    inserted in the model's config file. Input arguments: processed timeseries data,
    maturation base temperature above which SumDegreeDays (sdd) can be added up,
    and sdd maturation threshold.

    argument1
    : processed data

    argument2
    : maturation_base_temp

    argument3
    : sdd_maturation_threshold

    return
    : maturation_date, maturation_datetime_rowindex

    """

    oospore_maturation_date = None
    oospore_maturation_datetime_rowindex = None
    sum_degree_days = 0
    # temps_per_days = utils.get_measurements_per_days(processed_data, "temperature")
    # avg_temps_per_days = utils.get_average_measurements_per_days(
    #     processed_data, "temperature"
    # )
    for day in daily_mean_temperatures.keys():
        daily_mean_temperature = daily_mean_temperatures[day]
        if daily_mean_temperature > oospore_maturation_base_temperature:
            sum_degree_days = (
                sum_degree_days
                + daily_mean_temperature
                - oospore_maturation_base_temperature
            )
        if sum_degree_days >= oospore_maturation_sum_degree_days_threshold:
            oospore_maturation_date = day
            # Extracting the first datetime row index corresponding to the maturation day. Needed for quicker access to row index for data splicing in next algorithm.
            oospore_maturation_datetime_rowindex = sorted(
                daily_temperatures[day].keys()
            )[0]
            break
    # Returning the row index considerably speeds up the program, as no matching search needs to be performed to find the starting datetime for the following steps of the model.
    return oospore_maturation_date, oospore_maturation_datetime_rowindex
