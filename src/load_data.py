"""
Data loading functions.

"""

import sys

import pandas as pd


def load_data(raw_data_path, logfile):
    """
    **Load raw data: vitimeteo timeseries.**

    argument1
    : path to raw data

    The function takes as an argument the
    path to the raw data as specified in the main configuration file config/main.yaml


    """

    logf = open(logfile, "a")
    logf.write(f"\nLoading timeseries data from: {raw_data_path}\n")
    try:
        data = pd.read_csv(raw_data_path, sep=";")
        nrows = len(data.index)
        logf.write(f"\nNumber of rows: {nrows}\n")
        for i in range(1, len(data.columns)):
            logf.write(
                f"\t{data.columns.values[i]}: min={min(data.iloc[:,i])}; max={max(data.iloc[:,i])}\n"
            )
        logf.close()
        return data
    except IOError:
        error_msg = f"\nLoad Data Error: could not read {raw_data_path} file as pandas dataframe.\n"
        logf.write(error_msg)
        logf.close()
        print(error_msg)
        sys.exit()
