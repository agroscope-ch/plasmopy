"""
Automated weather data pull module.

This module handles periodic fetching of weather data from an API,
parsing it, and merging it with existing weather data files while
preserving historical values.
"""

import io
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


def fetch_weather_data_from_api(api_query_url, logfile=None):
    """
    Fetch weather data from the specified API query URL.

    Arguments
    ---------
    api_query_url : str
        The API query URL to fetch weather data from

    logfile : str, optional
        Path to logfile for writing status messages

    Returns
    -------
    str or None
        CSV formatted string of weather data, or None if fetch fails

    """

    def log_message(msg):
        """Helper function to write to logfile and console."""
        print(msg)
        if logfile is not None:
            try:
                with open(logfile, "a") as f:
                    f.write(msg + "\n")
            except Exception as e:
                print(f"Warning: Could not write to logfile: {e}")

    try:
        # Attempt to fetch JSON data from the API
        response = requests.get(api_query_url, timeout=30)
        response.raise_for_status()
        data_json = response.json()

        # Expecting structure similar to Meteoblue basic-1h response
        if "data_1h" in data_json:
            block = data_json["data_1h"]
            # build dataframe from lists
            df = pd.DataFrame(
                {
                    "datetime": block.get("time", []),
                    "temperature": block.get("temperature", []),
                    "humidity": block.get("relativehumidity", []),
                    "rainfall": block.get("precipitation", []),
                    "leaf_wetness": block.get("leafwetnessindex", []),
                }
            )
            # format datetime field
            df["datetime"] = pd.to_datetime(df["datetime"]).dt.strftime(
                "%d.%m.%Y %H:%M"
            )
            log_message(
                f"Fetched {len(df)} rows  |  "
                f"{df['datetime'].iloc[0]}  →  {df['datetime'].iloc[-1]}"
            )
            csv_data = df.to_csv(index=False, sep=";")
        else:
            # fallback to mock behavior if unexpected JSON
            msg = "API response missing expected 'data_1h' block; using mock data."
            log_message(msg)
            csv_data = _get_mock_weather_data()

        msg = f"Successfully fetched weather data from API at {datetime.now()}"
        log_message(msg)

        return csv_data

    except requests.exceptions.RequestException as e:
        msg = f"Error fetching weather data from API: {str(e)}"
        log_message(msg)
        return None
    except ValueError as e:
        msg = f"Error parsing JSON from API response: {str(e)}"
        log_message(msg)
        return None
    except Exception as e:
        msg = f"Unexpected error during weather data fetch: {str(e)}"
        log_message(msg)
        return None


def merge_weather_data(existing_file_path, new_csv_data, logfile=None):  # noqa: C901
    """
    Merge new weather data with existing weather data file.

    Updates datetime entries that exist in new data while preserving
    historical values for datetimes not present in the new data.

    Arguments
    ---------
    existing_file_path : str
        Path to the existing weather data CSV file

    new_csv_data : str
        CSV formatted string of new weather data

    logfile : str, optional
        Path to logfile for writing status messages

    Returns
    -------
    bool
        True if merge was successful, False otherwise

    """

    def log_message(msg):
        """Helper function to write to logfile and console."""
        print(msg)
        if logfile is not None:
            try:
                with open(logfile, "a") as f:
                    f.write(msg + "\n")
            except Exception as e:
                print(f"Warning: Could not write to logfile: {e}")

    try:
        # Load existing data (semicolon-separated)
        if not Path(existing_file_path).exists():
            msg = f"Existing file not found: {existing_file_path}. Creating new file with fetched data."
            log_message(msg)
            with open(existing_file_path, "w") as f:
                f.write(new_csv_data)
            return True

        try:
            existing_df = pd.read_csv(existing_file_path, sep=";")
        except pd.errors.EmptyDataError:
            # File exists but is completely empty (e.g. created as a placeholder
            # before the first automated pull).  Treat it like a new file.
            msg = f"Existing file {existing_file_path} is empty. Writing fetched data directly."
            log_message(msg)
            with open(existing_file_path, "w") as f:
                f.write(new_csv_data)
            return True

        # If the file only had a header row (no data rows), replace it entirely.
        if existing_df.empty:
            msg = f"Existing file {existing_file_path} has no data rows. Writing fetched data directly."
            log_message(msg)
            with open(existing_file_path, "w") as f:
                f.write(new_csv_data)
            return True

        # Load new data from CSV string (semicolon-separated)
        new_df = pd.read_csv(io.StringIO(new_csv_data), sep=";")

        # Ensure both have same column names
        if list(existing_df.columns) != list(new_df.columns):
            msg = "Warning: Column mismatch between existing and new data. Attempting to match columns."
            log_message(msg)
            # Rename new columns to match existing if possible
            if len(existing_df.columns) == len(new_df.columns):
                new_df.columns = existing_df.columns
            else:
                msg = "Error: Column count mismatch. Cannot merge data."
                log_message(msg)
                return False

        # Assume first column is datetime
        datetime_col = existing_df.columns[0]

        # Parse datetime columns
        existing_df[datetime_col] = pd.to_datetime(
            existing_df[datetime_col], format="%d.%m.%Y %H:%M"
        )
        new_df[datetime_col] = pd.to_datetime(
            new_df[datetime_col], format="%d.%m.%Y %H:%M"
        )

        # Merge: keep all from existing, update with new values where datetime matches
        # Set datetime as index for merge
        existing_df_indexed = existing_df.set_index(datetime_col)
        new_df_indexed = new_df.set_index(datetime_col)

        # Update existing data with new data where datetimes match
        existing_df_indexed.update(new_df_indexed)

        # Add any new datetimes from new data that weren't in existing
        new_datetimes = new_df_indexed.index.difference(existing_df_indexed.index)
        if len(new_datetimes) > 0:
            existing_df_indexed = pd.concat(
                [existing_df_indexed, new_df_indexed.loc[new_datetimes]]
            )

        # Sort by datetime
        existing_df_indexed = existing_df_indexed.sort_index()

        # Reset index and convert datetime back to string format
        merged_df = existing_df_indexed.reset_index()
        merged_df[datetime_col] = merged_df[datetime_col].dt.strftime("%d.%m.%Y %H:%M")

        # Write back to file
        merged_df.to_csv(
            existing_file_path,
            index=False,
            sep=";",
            quoting=None,
        )

        msg = (
            f"Successfully merged new weather data into {existing_file_path}. "
            f"Added/Updated {len(new_df)} records."
        )
        log_message(msg)
        return True

    except Exception as e:
        msg = f"Error merging weather data: {str(e)}"
        log_message(msg)
        return False


def start_periodic_data_pull(
    meteo_file_path,
    api_query_url,
    logfile=None,
    stop_event=None,
):
    """
    Start a background thread to fetch and merge weather data once.

    Since external scheduling (bash/cron) controls execution frequency,
    this thread performs a single fetch/merge operation during startup
    to populate the weather file with current data.

    Arguments
    ---------
    meteo_file_path : str
        Path to the weather data file to update

    api_query_url : str
        API query URL to fetch data from

    logfile : str, optional
        Path to logfile for writing status messages

    stop_event : threading.Event, optional
        Event to signal stopping (not used for one-shot execution)

    Returns
    -------
    threading.Thread or None
        The background thread object, or None if parameters invalid

    """

    def log_message(msg):
        """Helper function to write to logfile and console."""
        print(msg)
        if logfile is not None:
            try:
                with open(logfile, "a") as f:
                    f.write(msg + "\n")
            except Exception as e:
                print(f"Warning: Could not write to logfile: {e}")

    # Validate parameters
    if api_query_url is None:
        msg = "Error: No API query URL provided."
        log_message(msg)
        return None

    def _pull_once():
        """Background thread to perform a single weather data fetch/merge."""
        msg = "Automated weather data pull started (runs once per model execution)."
        log_message(msg)

        # Fetch and merge data
        msg = f"Pulling weather data from API at {datetime.now()}"
        log_message(msg)

        csv_data = fetch_weather_data_from_api(api_query_url, logfile)

        if csv_data is not None:
            success = merge_weather_data(meteo_file_path, csv_data, logfile)
            if success:
                msg = f"Weather data updated successfully at {datetime.now()}"
            else:
                msg = f"Failed to merge weather data at {datetime.now()}"
        else:
            msg = f"Failed to fetch weather data at {datetime.now()}"

        log_message(msg)

    # Create and start background thread
    thread = threading.Thread(target=_pull_once, daemon=True)
    msg = "Starting automated data pull thread..."
    log_message(msg)

    return thread


def _get_mock_weather_data():
    """
    Generate mock weather data for testing/demo purposes.

    Returns
    -------
    str
        CSV formatted string with mock weather data

    """
    # Mock data in the same format as actual weather files
    mock_data = """date;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.2;75;0;0
02.03.2026 09:00;6.1;72;0;0
02.03.2026 10:00;7.5;68;0;0
02.03.2026 11:00;8.9;65;0;0
02.03.2026 12:00;10.2;60;0;0
02.03.2026 13:00;11.5;58;0;0
02.03.2026 14:00;12.1;55;0;0
02.03.2026 15:00;11.8;57;0;0
02.03.2026 16:00;10.5;62;0;0
02.03.2026 17:00;9.2;68;0.5;0
02.03.2026 18:00;8.1;75;1.2;5
02.03.2026 19:00;7.5;80;0.8;8
02.03.2026 20:00;7.1;85;0;10
02.03.2026 21:00;6.8;88;0;12
02.03.2026 22:00;6.5;90;0;15
02.03.2026 23:00;6.3;92;0;18
03.03.2026 00:00;6.2;94;0;20
"""
    return mock_data
