"""
Data processing functions.

"""

import numpy as np
import pandas as pd


def map_to_timegrid(data):
    """
    **Create a complete time grid at selected time interval to which measurement
    data will be mapped onto, in order to avoid missing rows and uneven time intervals
    due to missing data.**
    """


def process_data(  # noqa: C901
    data,
    selected_columns,
    standard_colnames,
    standard_colformats,
    timezone,
    model_parameters,
    logfile,
    outfile,
):
    """
    **Process data columns and check that measurements fall within the torelated ranges.**

    argument1
    : raw pandas dataframe

    argument2
    : indices of selected columns

    argument3
    : standardised column names for renaming

    argument4
    : column formats for data type check and quality filtering

    argument5
    : path to process data output file


    The function takes the following parameters: the loaded timeseries data, and
    three elements taken from the specific processing configuration file
    (config/process/processX.yaml). These correspond to the indices of the selected
    columns of interest (starting from 0, where 0 must be the datetime column),
    the standard names to be used for renaming them, and ranges of tolerated
    min-max values for their measurements. The last argument is the pathfile to
    store the processed data in a '.csv' file.

    """

    len(data.index)
    colnames = data.iloc[:, selected_columns].columns
    colnames_str = "\n\t".join(colnames)
    processed_data = data
    logf = open(logfile, "a")
    logf.write(
        f"\nUsing selected columns as specified in config file: \n\t{colnames_str}\n"
    )
    logf.write(f"\nRenaming columns to: {standard_colnames}\n")
    logf.write(f"\nFormatting columns to: {standard_colformats}\n")
    for key, value in standard_colnames.items():
        processed_data = processed_data.rename(
            columns={processed_data.columns[key]: value}
        )
    try:
        # datetime column must always be placed as first column in dataset, as here it is hardcoded to the first index 0.
        processed_data[standard_colnames[0]] = pd.to_datetime(
            processed_data[standard_colnames[0]], format=standard_colformats[0]
        ).dt.tz_localize(timezone)
    except ValueError:
        logf.write(
            "\nFORMAT DATA ERROR: could not parse datetime column as datetime format.\n"
        )

    # Creating time grid to which meteorological measurement data will be mapped onto.
    # This way, we can deal with missing values and not have subsequent rows with different
    # time intervals. Rows with missing values will copy the values from the previous line.
    try:
        start_timegrid = processed_data.iloc[0, 0]
        end_timegrid = processed_data.iloc[-1, 0]
        timegrid_range = end_timegrid - start_timegrid
    except TypeError:
        logf.write(
            "\nTIME GRID CREATION ERROR: check first and last datetimes in the input data file.\n"
        )
    freq_timegrid = str(model_parameters["measurement_time_interval"]) + "min"
    timegrid = pd.date_range(
        start=start_timegrid, end=end_timegrid, freq=freq_timegrid, tz=timezone
    )
    timegrid = pd.DataFrame({standard_colnames[0]: timegrid})
    logf.write(
        f"\nMeterological timeseries range of provided input data: {timegrid_range}.\
        \nStart: {start_timegrid}. End: {end_timegrid}.\n"
    )

    processed_data = pd.merge(
        timegrid, processed_data, on=standard_colnames[0], how="left"
    )

    logf.write("\nSetting non-numeric values to NaN (datetime not considered).\n")
    outofrange_counter = 0
    for i in range(1, len(processed_data.columns)):  # skipping datetime column 0
        try:
            processed_data.iloc[:, i] = pd.to_numeric(
                processed_data.iloc[:, i], errors="coerce"
            )  # Setting non-numeric values to NaN.
            for row in range(0, len(processed_data)):
                if processed_data.iloc[row, i] < min(
                    standard_colformats[i]
                ) or processed_data.iloc[row, i] > max(standard_colformats[i]):
                    # Custom processing for max values of leaf wetness, as when sampled in longer times, its maximum
                    # value can be over the user-defined max value, thus bringing it back to max allowed values.
                    # This serves to fix a bug which can occur when mixing differently sampled time ranges, as leaf wetness
                    # is measured on the duration of the sampled interval. If the tolerated range is fixed to its maximum
                    # possible value already in the config files, then the following fix does not change the result anyways.
                    if i == 4 and processed_data.iloc[row, i] > max(
                        standard_colformats[i]
                    ):
                        if standard_colnames[4] != "leaf_wetness":
                            logf.write(
                                "\nWARNING: leaf_wetness column name has changed from default name. Make sure that leaf_wetness data is placed at the 5th column in the input dataset. Proceeding to formatting.'.\n"
                            )
                        rangemax = max(standard_colformats[i])
                        logf.write(
                            f"\nWARNING: detected higher than allowed leaf_wetness value at {processed_data.iloc[row,0]}. Changed to {rangemax}."
                        )
                        processed_data.iloc[row, i] = pd.to_numeric(
                            max(standard_colformats[i])
                        )
                    # Setting out-of-range values to NaN. All other variables' out-of-range values are treated as
                    # normal outliers.
                    else:
                        logf.write(
                            f"\nWARNING: detected out-of-range values in '{standard_colnames[i]}'."
                        )
                        printrow = str(processed_data.iloc[row])
                        logf.write(f"\n{printrow}\n")
                        processed_data.iloc[row, i] = np.nan
                        outofrange_counter += 1
        except ValueError:
            logf.write(
                f"\nData Formatting ValueError: could not parse values of '{standard_colnames[i]}'.\n"
            )
    # Filling NaN values (from missing data or from out-range-values) by interpolation between previous and following values.
    nan_count = processed_data.isnull().sum().sum()
    processed_data = processed_data.interpolate(method="linear")
    actual_missing_values_count = nan_count - outofrange_counter
    logf.write(
        f"\n\n{outofrange_counter} out-of-range and {actual_missing_values_count} missing values replaced by interpolated values.\n"
    )

    try:
        processed_data.to_csv(outfile, index=False)
        logf.write(f"\nFormatted data stored in: {outfile}\n")
        logf.close()
    except IOError:
        logf.write(
            f"\nDATA FORMATTING ERROR: cannot save formatted dataset to {outfile}\n"
        )
        logf.close()

    return processed_data
