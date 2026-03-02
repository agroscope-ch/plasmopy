"""
Support Decision Tool for continuing model simulation from sporulation stage.

This module provides functionality to check spore count data and determine
if the infection model simulation should continue from the sporulation stage
based on spore count thresholds and trends.
"""

from datetime import datetime

import pandas as pd


def fetch_spore_counts(api_query_url, logfile=None):
    """
    Fetch spore counts from an online API and return as CSV string.

    The API returns a JSON object with a ``datetime_str_list`` array whose
    entries (format ``YYYYMMDD_HHMMSS``) each represent one spore-detection
    event recorded by the trap camera.  The function aggregates these events
    into daily totals and returns a semicolon-delimited CSV with columns
    ``Date;Counts`` (date format ``DD.MM.YYYY HH:MM``) compatible with
    ``check_spore_counts``.  Returns None if the request or parsing fails.
    """

    def log_message(msg):
        print(msg)
        if logfile is not None:
            try:
                with open(logfile, "a") as f:
                    f.write(msg + "\n")
            except Exception as e:
                print(f"Warning: Could not write to logfile: {e}")

    import requests

    try:
        resp = requests.get(api_query_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        datetime_list = data.get("datetime_str_list", [])
        if not datetime_list:
            log_message("No datetime_str_list found in spore counts API response.")
            return None

        # Parse YYYYMMDD_HHMMSS timestamps; skip malformed entries.
        parsed = []
        for dt_str in datetime_list:
            try:
                parsed.append(datetime.strptime(dt_str, "%Y%m%d_%H%M%S"))
            except ValueError:
                continue

        if not parsed:
            log_message("No valid datetimes parsed from spore counts API response.")
            return None

        # Aggregate: count detection events per calendar day.
        df = pd.DataFrame({"datetime": parsed})
        df["date"] = df["datetime"].dt.date
        daily = df.groupby("date").size().reset_index(name="Counts")
        daily["Date"] = pd.to_datetime(daily["date"]).dt.strftime("%d.%m.%Y") + " 00:00"
        result_df = daily[["Date", "Counts"]]

        log_message(
            f"Fetched spore counts: {len(result_df)} days, "
            f"{result_df['Counts'].sum()} total events."
        )
        return result_df.to_csv(index=False, sep=";")

    except Exception as e:
        log_message(f"Error fetching spore counts from API: {e}")
        return None


def check_spore_counts(  # noqa: C901
    spore_counts_filepath,
    logfile=None,
    spore_count_threshold=10,
    spore_count_lookback_days=3,
    spore_count_percent_increase=20,
):
    """
    Check spore counts file and determine if model should continue from sporulation stage.

    The function scans the **entire** spore counts file (historical or current) and
    checks whether either condition is met at any point in time:

    1. Any single day's total surpasses ``spore_count_threshold`` spores.
       → records the **first** day that exceeds the threshold as
       ``dispersion_datetime``.
    2. Within any consecutive ``spore_count_lookback_days``-day window, the count
       rises by at least ``spore_count_percent_increase`` % from the first to the
       last day of the window.
       → records the last day of the **first** triggering window as
       ``sporulation_datetime``.

    Both conditions are evaluated independently; both can be True simultaneously.

    Arguments
    ---------
    spore_counts_filepath : str
        Path to the spore counts CSV file with columns 'Date' and 'Counts'
        Date format: "DD.MM.YYYY HH:MM"
        Delimiter: semicolon (;)

    logfile : str, optional
        Path to logfile for writing status messages

    spore_count_threshold : int or float, optional
        Flat daily count threshold; if any day exceeds this value condition 1 is met.
        Default: 10.

    spore_count_lookback_days : int, optional
        Size of the sliding window (in days) for the percent-increase condition.
        Default: 3.

    spore_count_percent_increase : float, optional
        Minimum percent increase from the first to the last day of the window
        required to meet condition 2.  Default: 20.

    Returns
    -------
    dict
        Dictionary containing:
        - 'skip_to_dispersion': bool
            True when condition 1 (flat threshold) is met.
        - 'dispersion_datetime': datetime or None
            Datetime of the first day that exceeded the flat threshold.
        - 'skip_to_sporulation': bool
            True when condition 2 (percent increase) is met.
        - 'sporulation_datetime': datetime or None
            Datetime of the last day in the first triggering window.
        - 'last_n_days_counts': list
            Daily counts for the triggering window (condition 2) or an empty list.
        - 'analysis_message': str
            Message describing the analysis results.
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
        # Read and sort the full spore counts file (no date cutoff)
        df = pd.read_csv(spore_counts_filepath, delimiter=";")
        df["Date"] = pd.to_datetime(df["Date"], format="%d.%m.%Y %H:%M")
        df = df.sort_values("Date")

        if df.empty:
            msg = "Spore counts file is empty. No model shortcut will be triggered."
            log_message(msg)
            return {
                "skip_to_dispersion": False,
                "dispersion_datetimes": [],
                "skip_to_sporulation": False,
                "sporulation_datetimes": [],
                "analysis_message": msg,
            }

        # Aggregate to one row per calendar day
        daily = (
            df.groupby(df["Date"].dt.date)
            .agg(total=("Counts", "sum"), last_dt=("Date", "last"))
            .reset_index()
            .rename(columns={"Date": "date"})
            .sort_values("date")
        )

        if daily.empty:
            msg = "Spore counts file has no valid dates."
            log_message(msg)
            return {
                "skip_to_dispersion": False,
                "dispersion_datetimes": [],
                "skip_to_sporulation": False,
                "sporulation_datetimes": [],
                "analysis_message": msg,
            }

        totals = daily["total"].tolist()
        datetimes = daily["last_dt"].tolist()
        n = int(spore_count_lookback_days)

        # ------------------------------------------------------------------ #
        # Condition 1: flat threshold                                          #
        # Scan all days; record the first day of every contiguous surge       #
        # (consecutive days all exceeding the threshold count as one event).  #
        # ------------------------------------------------------------------ #
        dispersion_datetimes: list = []
        _prev_above = False
        for count, dt in zip(totals, datetimes, strict=False):
            if count > spore_count_threshold:
                if not _prev_above:
                    dispersion_datetimes.append(dt)
                _prev_above = True
            else:
                _prev_above = False
        skip_to_dispersion = len(dispersion_datetimes) > 0

        # ------------------------------------------------------------------ #
        # Condition 2: percent increase over non-overlapping N-day windows    #
        # After a window triggers, advance by N days before the next check    #
        # so that each surge contributes at most one sporulation event.       #
        # ------------------------------------------------------------------ #
        sporulation_datetimes: list = []
        i = 0
        while i <= len(totals) - n:
            window = totals[i : i + n]
            if window[0] > 0:
                pct = (window[-1] - window[0]) / window[0] * 100
                if pct >= spore_count_percent_increase:
                    sporulation_datetimes.append(datetimes[i + n - 1])
                    i += n  # skip ahead to avoid overlapping surges
                    continue
            i += 1
        skip_to_sporulation = len(sporulation_datetimes) > 0

        # Build analysis message
        analysis_msg = (
            f"\nSpore count analysis (full dataset, {len(totals)} days):\n"
            f"Condition 1 – flat threshold (any day > {spore_count_threshold}): "
            f"{skip_to_dispersion} → {len(dispersion_datetimes)} surge(s) detected\n"
            f"Condition 2 – percent increase ({spore_count_percent_increase}%+ over {n}-day window): "
            f"{skip_to_sporulation} → {len(sporulation_datetimes)} triggering window(s) detected"
        )

        log_message(analysis_msg)

        return {
            "skip_to_dispersion": skip_to_dispersion,
            "dispersion_datetimes": dispersion_datetimes,
            "skip_to_sporulation": skip_to_sporulation,
            "sporulation_datetimes": sporulation_datetimes,
            "analysis_message": analysis_msg,
        }

    except FileNotFoundError:
        msg = f"Spore counts file not found: {spore_counts_filepath}"
        log_message(msg)
        return {
            "skip_to_dispersion": False,
            "dispersion_datetimes": [],
            "skip_to_sporulation": False,
            "sporulation_datetimes": [],
            "analysis_message": msg,
        }

    except Exception as e:
        msg = f"Error reading spore counts file: {str(e)}"
        log_message(msg)
        return {
            "skip_to_dispersion": False,
            "dispersion_datetimes": [],
            "skip_to_sporulation": False,
            "sporulation_datetimes": [],
            "analysis_message": msg,
        }
