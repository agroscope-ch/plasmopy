"""
Main script orchestrating all modeling steps and launching specific submodules.

"""

import csv
import pickle
import sys
import threading
from datetime import datetime

import automated_weather_pull
import hydra
import infection_event
import infection_model
import load_data
import pandas as pd
import process_data
import support_decision_tool
import utils
from omegaconf import DictConfig
from tqdm import tqdm


@hydra.main(config_path="../config", config_name="main", version_base=None)
def main(config: DictConfig):  # noqa: C901
    """
    **Main function for directing all steps and running specific submodules.**

    argument1
    : hydra config dictionary

    From here, the following steps are orchestrated:

      1. Load raw data: Agrometeo timeseries. Input, processed, and output data paths have to be specificied in the "config/main.yaml" file.

      2. Select columns to use as specified in the process config files.

      3. Select column formats and tolerated value ranges depending on the specific input data as specified in the process config files.

      4. Process data columns and check that measurements fall within the tolerated ranges as specified in the process config files.

      5. Load model parameters from the model config file. *N.B. specific model parameters can be changed within the config files in the "config/model" folder.
      New model configurations can also be fully added as new config files and then manually specified in the "config/main.yaml" file.*

      6. Run cumulative infection risk computation across entire timeseries dataset.

    """

    # determine output filenames base on input or explicit run name
    output_files = utils.create_output_filenames(
        config.input_data.meteo,
        config.input_data.spore_counts,
        output_dir=getattr(config, "output", {}).get("directory"),
        run_name=getattr(config, "output", {}).get("run_name"),
    )

    # Parse log filename.
    logfile = output_files.logfile

    # Open logfile.
    logf = open(logfile, "w")

    logf.write(
        "©Plasmopy\
        \n\nPython implementation of Vitimeteo Plasmopara\
        \n\nLivio Ruzzante\
        \nAgroscope Changins (CH), 2023\
        \nversion 1.0\
        \n"
    )

    # Start timer.
    t_start = datetime.now()
    logf.write(f"\nRuntime start: {t_start}\n")

    # Close log file.
    logf.close()

    # Running model computation.

    # Initialize automated data pull if enabled
    data_pull_thread = None
    data_pull_stop_event = None
    # resolve meteorological file path for potential auto-pull
    meteo_file_path = config.input_data.meteo
    from pathlib import Path
    from urllib.parse import parse_qs, urlparse

    if not meteo_file_path or meteo_file_path.strip() == "":
        if config.input_data.get("automated_weather_pull", False):
            # Build a coordinate-keyed filename so data fetched for different
            # site coordinates are never merged into the same file.
            _api_q = config.input_data.get("weather_api_query", "") or ""
            _automated_meteo_path = "data/input/automated_meteo.csv"
            if _api_q:
                _qs = parse_qs(urlparse(_api_q).query)
                _lat = (_qs.get("lat") or _qs.get("latitude") or [None])[0]
                _lon = (_qs.get("lon") or _qs.get("longitude") or [None])[0]
                if _lat and _lon:
                    _automated_meteo_path = (
                        f"data/input/automated_meteo_lat{_lat}_lon{_lon}.csv"
                    )
            meteo_file_path = _automated_meteo_path
            Path(meteo_file_path).parent.mkdir(parents=True, exist_ok=True)
            if not Path(meteo_file_path).exists():
                open(meteo_file_path, "w").close()
        else:
            meteo_file_path = None

    if config.input_data.get("automated_weather_pull", False):
        api_query = config.input_data.get("weather_api_query")

        # verify coordinates (and elevation) match between config and API url
        if api_query is not None:
            parsed = urlparse(api_query)
            qs = parse_qs(parsed.query)
            try:
                lat_list = qs.get("lat") or qs.get("latitude")
                lon_list = qs.get("lon") or qs.get("longitude")
                asl_list = qs.get("asl")
                if lat_list and lon_list:
                    api_lat = float(lat_list[0])
                    api_lon = float(lon_list[0])
                    cfg_lat = float(config.site.latitude)
                    cfg_lon = float(config.site.longitude)
                    # allow small tolerance
                    if abs(api_lat - cfg_lat) > 1e-4 or abs(api_lon - cfg_lon) > 1e-4:
                        msg = (
                            f"\nERROR: API coordinates ({api_lat},{api_lon}) do not match",
                            f"config coordinates ({cfg_lat},{cfg_lon}).\nPlease correct them and rerun.\n",
                        )
                        with open(logfile, "a") as logf:
                            logf.write("".join(msg))
                        print(
                            "ERROR: API coordinates do not match config; check settings."
                        )
                        sys.exit(1)
                # elevation check
                if asl_list:
                    try:
                        api_asl = float(asl_list[0])
                        cfg_elev = float(config.site.elevation)
                        # allow 1 m tolerance
                        if abs(api_asl - cfg_elev) > 1.0:
                            msg = (
                                f"\nERROR: API elevation asl={api_asl} does not",
                                f"match config elevation={cfg_elev}.\nPlease correct and rerun.\n",
                            )
                            with open(logfile, "a") as logf:
                                logf.write("".join(msg))
                            print(
                                "ERROR: API elevation does not match config; check settings."
                            )
                            sys.exit(1)
                    except ValueError:
                        with open(logfile, "a") as logf:
                            logf.write(
                                "\nWARNING: could not parse asl value from API query URL.\n"
                            )
            except ValueError:
                with open(logfile, "a") as logf:
                    logf.write(
                        "\nWARNING: could not parse coordinates from API query URL.\n"
                    )

    # Start periodic background thread only if enabled and has API query
    if config.input_data.get("automated_weather_pull", False) and api_query is not None:
        data_pull_stop_event = threading.Event()
        data_pull_thread = automated_weather_pull.start_periodic_data_pull(
            meteo_file_path=meteo_file_path,
            api_query_url=api_query,
            logfile=logfile,
            stop_event=data_pull_stop_event,
        )
        if data_pull_thread is not None:
            data_pull_thread.start()

    # Load raw data: vitimeteo timeseries.  ``meteo_file_path`` has already
    # been computed above to take into account the possibility of an empty
    # configuration value and the automated pull fall‑back.
    input_meteo_file = meteo_file_path

    if not input_meteo_file or input_meteo_file.strip() == "":
        if config.input_data.get("automated_weather_pull", False):
            # Reuse the coordinate-keyed path derived above, falling back to
            # the generic name only if the earlier block was never reached.
            input_meteo_file = locals().get(
                "_automated_meteo_path", "data/input/automated_meteo.csv"
            )
            Path(input_meteo_file).parent.mkdir(parents=True, exist_ok=True)
            if not Path(input_meteo_file).exists():
                # create placeholder with header row so pandas can read columns
                with open(input_meteo_file, "w") as fh:
                    fh.write("datetime;temperature;humidity;rainfall;leaf_wetness\n")
        else:
            err = "\nERROR: no meteo input file provided and automated_weather_pull is disabled."
            print(err)
            with open(logfile, "a") as logf:
                logf.write(err + "\n")
            sys.exit(1)
    # If the automated pull is enabled, attempt one immediate fetch/merge.
    # log to stdout so the user can see progress before load_data runs.
    if config.input_data.get("automated_weather_pull", False) and api_query is not None:
        print("Performing initial weather data fetch...")
        csv_data = automated_weather_pull.fetch_weather_data_from_api(
            api_query, logfile
        )
        if csv_data is not None:
            automated_weather_pull.merge_weather_data(
                input_meteo_file, csv_data, logfile
            )
        else:
            print("Initial fetch returned no data; input file may remain empty.")

    loaded_data = load_data.load_data(input_meteo_file, logfile)
    if loaded_data is None or getattr(loaded_data, "empty", False):
        msg = (
            "\nERROR: meteorological file contains no data. "
            "Provide a valid meteo input or wait until the automated pull populates the file.\n"
        )
        print(msg)
        with open(logfile, "a") as logf:
            logf.write(msg)
        sys.exit(1)

    # Select columns to use as specified in the config files.
    selected_columns = config.data_columns.use_columns
    standard_colnames = config.data_columns.rename_columns

    # Select column formats and tolerated value ranges depending on the specific input data as specified in the config files.
    standard_colformats = config.data_columns.format_columns

    # Parse site's timezone from config file.
    timezone = config.site.timezone

    # Parse output filename for processed data.
    outfile = output_files.processed_file_meteo

    # Load model parameters from config files.
    # model_parameters = config

    # Format columns and check that measurements fall within the tolerated ranges.
    processed_data = process_data.process_data(
        loaded_data,
        selected_columns,
        standard_colnames,
        standard_colformats,
        timezone,
        config,
        logfile,
        outfile,
    )

    # Run infection model for all datetime rows, starting from the oospore maturation datetime predicted above.
    logf = open(logfile, "a")
    logf.write("\nRunning infection model...\n")
    logf.write("\nModel parameters:\n")
    for key, value in config.items():
        logf.write(f"\t{key}: {value}\n")

    # Determine which spore counts file (if any) to use
    spore_counts_result = None
    input_spore_file = config.input_data.spore_counts
    if not input_spore_file or input_spore_file.strip() == "":
        if config.input_data.get("automated_spore_pull", False):
            api_query = config.input_data.get("spore_counts_api_query")
            if api_query:
                tmpfile = "data/input/auto_spore_counts.csv"
                Path(tmpfile).parent.mkdir(parents=True, exist_ok=True)
                try:
                    csvtext = support_decision_tool.fetch_spore_counts(
                        api_query, logfile
                    )
                    if csvtext:
                        with open(tmpfile, "w") as f:
                            f.write(csvtext)
                        input_spore_file = tmpfile
                        msg = f"Spore counts saved to {tmpfile}"
                        print(msg)
                        logf.write(f"\n{msg}\n")
                    else:
                        msg = "Unable to fetch spore counts from API; running normal flow."
                        print(msg)
                        logf.write(f"\n{msg}\n")
                except Exception as e:
                    msg = f"Error pulling spore counts: {e}"
                    print(msg)
                    logf.write(f"\n{msg}\n")
            else:
                logf.write(
                    "\nAutomated spore pull enabled but no API query provided.\n"
                )

    # Check spore counts to determine if model should skip to sporulation stage
    if (
        config.input_data.get("decision_support_tool_enabled", False)
        and input_spore_file is not None
    ):
        logf.write(
            "\nSupport decision tool enabled. Checking spore counts file for decision support...\n"
        )
        spore_counts_result = support_decision_tool.check_spore_counts(
            input_spore_file,
            logfile,
            spore_count_threshold=config.input_data.get("spore_count_threshold", 10),
            spore_count_lookback_days=config.input_data.get(
                "spore_count_lookback_days", 3
            ),
            spore_count_percent_increase=config.input_data.get(
                "spore_count_percent_increase", 20
            ),
        )
        if spore_counts_result.get("skip_to_dispersion"):
            logf.write(
                "\nSpore counts flat threshold exceeded. "
                "Model will jump to oospore dispersion stage.\n"
            )
        if spore_counts_result.get("skip_to_sporulation"):
            logf.write(
                "\nSpore counts percent-increase threshold exceeded. "
                "Model will jump to sporulation stage.\n"
            )
    else:
        if config.input_data.get("decision_support_tool_enabled", False):
            logf.write(
                "\nSupport decision tool enabled but no spore counts file available. Running normal model flow.\n"
            )
        else:
            logf.write("\nSupport decision tool disabled. Running normal model flow.\n")

    daily_temperatures = utils.get_daily_measurements(processed_data, "temperature")
    daily_mean_temperatures = utils.get_daily_mean_measurements(
        processed_data, "temperature"
    )

    # Determine oospore maturation date from the model (always run normal path).
    # Spore count shortcut events are injected after the main loop as supplements.
    (
        oospore_maturation_date,
        oospore_maturation_datetime_rowindex,
    ) = infection_model.get_oospore_maturation_date(
        processed_data,
        config,
        standard_colformats,
        timezone,
        daily_temperatures,
        daily_mean_temperatures,
        logfile,
    )

    # Extract the oospore maturation date from the processed datetime column,
    # so to make sure that the format is the same as in the other infection datetimes.
    oospore_maturation_datetime = (
        processed_data["datetime"][oospore_maturation_datetime_rowindex]
        if oospore_maturation_datetime_rowindex is not None
        else None
    )

    algorithmic_time_steps = int(config.run_settings.algorithmic_time_steps // 1)
    if algorithmic_time_steps < 1:
        logf.write(
            "WARNING: algorithmic time-step cannot be lower than 1. Running model at 1 time-step intervals..."
        )
        algorithmic_time_steps = 1
    computational_time_steps = int(config.run_settings.computational_time_steps // 1)
    if computational_time_steps < 1:
        logf.write(
            "WARNING: computational time-step cannot be lower than 1. Running model at 1 time-step intervals..."
        )
        computational_time_steps = 1

    # Clearing the output file content. We need to clear it before hand to avoid later "appending"
    # results from previous model runs.

    # For temporary oospore_infection_datetime processing:
    oospore_infection_datetimes = "data/tmp/oospore_infection_datetimes.csv"
    f = open(oospore_infection_datetimes, "w")
    f.close()

    # For result events output file:
    f = open(output_files.events_text, "w")
    f.close()

    # And for infection results output file.
    with open(output_files.infection_datetimes, "w") as f:
        header_str = (
            "id"
            + ","
            + "start"
            + ","
            + "oospore_maturation"
            + ","
            + "oospore_germination"
            + ","
            + "oospore_dispersion"
            + ","
            + "oospore_infection"
            + ","
            + "completed_incubation"
            + ","
            + "sporulation"
            + ","
            + "sporangia_density"
            + ","
            + "secondary_infection"
            + "\n"
        )
        f.write(header_str)

    infection_predictions = []
    infection_events = []

    if oospore_maturation_datetime_rowindex is not None:
        progress_bar = tqdm(
            range(
                oospore_maturation_datetime_rowindex,
                len(processed_data.index),
                computational_time_steps,
            )
        )

        # Progress bar output on terminal.
        for i in progress_bar:
            infection_prediction = infection_event.InfectionEvent(
                processed_data,
                config,
                i,
                oospore_maturation_datetime,
                daily_mean_temperatures,
                algorithmic_time_steps,
                logfile,
                oospore_infection_datetimes,
                None,  # shortcut events are injected separately after this loop
            )
            infection_prediction.predict_infection()
            infection_events.append(infection_prediction.infection_events)
            infection_predictions.append(infection_prediction)

            progress_bar.set_description(
                f"DateTime Row {i}/{len(processed_data.index)}: {infection_prediction.start_event_datetime}"
            )

            ## Appending InfectionEvent results at every iteration so to make the results dynamically
            ## accessible during model runtime.
            with open(output_files.events_text, "a") as f:
                f.write(str(infection_prediction) + "\n")

            ## Adding collateral infection counts (i.e. subsequent secondary infections
            ## from succesful secondary infections) to overall secondary infections.
            # sporangia_counts = infection_prediction.infection_events["sporangia_counts"]
            # collateral_sporangia_counts = infection_prediction.infection_events[
            #     "collateral_sporangia_counts"
            # ]
            # all_sporangia_counts = []
            # if sporangia_counts is not None:
            #     for (
            #         _sporulation_datetime_rowindex,
            #         sporangia_count,
            #     ) in sporangia_counts.items():
            #         if sporangia_count is not None:
            #             all_sporangia_counts.append(sporangia_count)
            # if collateral_sporangia_counts is not None:
            #     for (
            #         _sporulation_datetime_rowindex,
            #         collateral_sporangia_count,
            #     ) in collateral_sporangia_counts.items():
            #         if collateral_sporangia_count is not None:
            #             all_sporangia_counts.append(collateral_sporangia_count)
            #
            # secondary_infections = infection_prediction.infection_events[
            #     "secondary_infections"
            # ]
            # collateral_secondary_infections = infection_prediction.infection_events[
            #     "collateral_secondary_infections"
            # ]
            # all_secondary_infections = []
            # if secondary_infections is not None:
            #     secondary_infections = list(
            #         filter(lambda item: item is not None, secondary_infections)
            #     )
            #     all_secondary_infections.extend(secondary_infections)
            # if collateral_secondary_infections is not None:
            #     collateral_secondary_infections = list(
            #         filter(
            #             lambda item: item is not None, collateral_secondary_infections
            #         )
            #     )
            #     all_secondary_infections.extend(collateral_secondary_infections)

            ## Saving the overall infection counts, dates, and parameters to output result file.
            # with open(config.results.infections, "a") as f:
            #     i = 0
            #     for secondary_infection in all_secondary_infections:
            #         output_str = (
            #             str(infection_prediction.start_event_rowindex)
            #             + ","
            #             + str(infection_prediction.start_event_datetime)
            #             + ","
            #             + str(
            #                 infection_prediction.infection_events["oospore_germination"]
            #             )
            #             + ","
            #             + str(
            #                 infection_prediction.infection_events["oospore_dispersion"]
            #             )
            #             + ","
            #             + str(
            #                 infection_prediction.infection_events["oospore_infection"]
            #             )
            #             + ","
            #             + str(all_sporangia_counts[i])
            #             + ","
            #             + str(secondary_infection)
            #             + "\n"
            #         )
            #         f.write(output_str)
            with open(output_files.infection_datetimes, "a") as f:
                _ev = infection_prediction.infection_events
                if _ev["oospore_infection"] is not None:
                    _sec_infs = _ev.get("secondary_infections") or []
                    _sporuls = _ev.get("sporulations") or []
                    _spor_dens = _ev.get("sporangia_densities") or []
                    _n_rows = max(1, len(_sec_infs), len(_sporuls))
                    for _ri in range(_n_rows):
                        f.write(
                            str(infection_prediction.start_event_rowindex)
                            + ","
                            + str(infection_prediction.start_event_datetime)
                            + ","
                            + str(_ev["oospore_maturation"])
                            + ","
                            + str(_ev["oospore_germination"])
                            + ","
                            + str(_ev["oospore_dispersion"])
                            + ","
                            + str(_ev["oospore_infection"])
                            + ","
                            + str(_ev["completed_incubation"])
                            + ","
                            + str(_sporuls[_ri] if _ri < len(_sporuls) else "NA")
                            + ","
                            + str(_spor_dens[_ri] if _ri < len(_spor_dens) else "NA")
                            + ","
                            + str(_sec_infs[_ri] if _ri < len(_sec_infs) else "NA")
                            + "\n"
                        )

    else:
        logf.write(
            "\nOospore maturation conditions not reached. Normal model loop skipped; "
            "processing spore count shortcut events only.\n"
        )

    # ------------------------------------------------------------------ #
    # Inject supplementary shortcut events from spore count conditions.  #
    # These add events that bypass early infection stages based on spore  #
    # trap data, without replacing the normal model events above.         #
    # ------------------------------------------------------------------ #
    if spore_counts_result is not None:
        # One entry per triggering datetime, each activating only one
        # condition so run_infection_model takes the correct branch.
        _sc_to_inject = []
        for _sc_dt in spore_counts_result.get("sporulation_datetimes", []):
            _sc_to_inject.append(
                {
                    **spore_counts_result,
                    "skip_to_sporulation": True,
                    "skip_to_dispersion": False,
                    "sporulation_datetime": _sc_dt,
                }
            )
        for _sc_dt in spore_counts_result.get("dispersion_datetimes", []):
            _sc_to_inject.append(
                {
                    **spore_counts_result,
                    "skip_to_sporulation": False,
                    "skip_to_dispersion": True,
                    "dispersion_datetime": _sc_dt,
                }
            )

        for _sc_result in _sc_to_inject:
            _anchor_raw = (
                _sc_result.get("sporulation_datetime")
                if _sc_result.get("skip_to_sporulation")
                else _sc_result.get("dispersion_datetime")
            )
            if _anchor_raw is None:
                continue
            _sc_dt = pd.to_datetime(_anchor_raw)
            if processed_data["datetime"].dt.tz is not None and _sc_dt.tzinfo is None:
                _sc_dt = _sc_dt.tz_localize(timezone)
            _closest = (processed_data["datetime"] - _sc_dt).abs().argmin()
            _sc_rowindex = processed_data.index.get_loc(processed_data.index[_closest])

            _sc_event = infection_event.InfectionEvent(
                processed_data,
                config,
                _sc_rowindex,
                oospore_maturation_datetime,
                daily_mean_temperatures,
                algorithmic_time_steps,
                logfile,
                oospore_infection_datetimes,
                _sc_result,
            )
            _sc_event.predict_infection()
            infection_events.append(_sc_event.infection_events)
            infection_predictions.append(_sc_event)

            with open(output_files.events_text, "a") as f:
                f.write(str(_sc_event) + "\n")

            with open(output_files.infection_datetimes, "a") as f:
                _sc_ev = _sc_event.infection_events
                if _sc_ev["oospore_infection"] is not None:
                    _sc_sec = _sc_ev.get("secondary_infections") or []
                    _sc_spor = _sc_ev.get("sporulations") or []
                    _sc_dens = _sc_ev.get("sporangia_densities") or []
                    _sc_rows = max(1, len(_sc_sec), len(_sc_spor))
                    for _sc_ri in range(_sc_rows):
                        f.write(
                            str(_sc_event.start_event_rowindex)
                            + ","
                            + str(_sc_event.start_event_datetime)
                            + ","
                            + str(_sc_ev["oospore_maturation"])
                            + ","
                            + str(_sc_ev["oospore_germination"])
                            + ","
                            + str(_sc_ev["oospore_dispersion"])
                            + ","
                            + str(_sc_ev["oospore_infection"])
                            + ","
                            + str(_sc_ev["completed_incubation"])
                            + ","
                            + str(_sc_spor[_sc_ri] if _sc_ri < len(_sc_spor) else "NA")
                            + ","
                            + str(_sc_dens[_sc_ri] if _sc_ri < len(_sc_dens) else "NA")
                            + ","
                            + str(_sc_sec[_sc_ri] if _sc_ri < len(_sc_sec) else "NA")
                            + "\n"
                        )

    if not infection_events:
        logf.write(
            "\nNo infection events produced (no maturation and no spore count shortcuts triggered).\n"
        )
        t_end = datetime.now()
        logf.write(f"Runtime end: {t_end}\nRuntime total: {t_end - t_start}\n")
        if data_pull_stop_event is not None:
            data_pull_stop_event.set()
            if data_pull_thread is not None and data_pull_thread.is_alive():
                data_pull_thread.join(timeout=5)
        logf.close()
        return

    logf.write(
        "\nModel run complete. Infection events details and summary of predicted infection datetimes are stored in 'data/output/'.\n"
    )

    # End the timer.
    t_end = datetime.now()
    logf.write(f"Runtime end: {t_end}\n")

    # Calculate the elapsed time.
    t_diff = t_end - t_start
    logf.write(f"Runtime total: {t_diff}\n")

    # Stop automated data pull if it was started
    if data_pull_stop_event is not None:
        logf.write("\nStopping automated weather data pull thread...\n")
        data_pull_stop_event.set()
        if data_pull_thread is not None and data_pull_thread.is_alive():
            data_pull_thread.join(timeout=5)

    # Close the log file.
    logf.close()

    # Plot infection events predictions (PDF only).
    utils.plot_events(infection_events, config, output_files.pdf_graph)

    with open(output_files.events_dict, "wb") as pickle_file:
        pickle.dump(infection_events, pickle_file)
    with open(output_files.model_params, "wb") as pickle_file:
        pickle.dump(config, pickle_file)

    ### WRITE CSV "DATAFRAME" OF ALL INFECTION EVENTS DATETIMES
    with open(output_files.events_dataframe, "w") as f:
        event_columns = list(infection_events[0].keys())
        event_columns.insert(0, "id")
        event_columns.insert(1, "start")
        wr = csv.writer(f, quoting=csv.QUOTE_NONE)
        wr.writerow(event_columns)
        event_id = 0
        for event in infection_events:
            start_time = infection_predictions[event_id].start_event_datetime
            id = infection_predictions[event_id].id
            f.write(str(id) + "," + str(start_time) + ",")
            event_id += 1
            n_events = len(event.keys())
            i = 0
            for key, item in event.items():  # noqa: B007
                i += 1
                if isinstance(item, list):
                    if item:
                        if i < n_events:
                            f.write(str(item[0]) + ",")
                        else:
                            f.write(str(item[0]))
                else:
                    if i < n_events:
                        f.write(str(item) + ",")
                    else:
                        f.write(str(item))
            f.write("\n")

    # Plot analysis graph (Rplot.R equivalent).
    analysis_fig = utils.plot_infection_analysis(
        output_files.events_dataframe,
        output_files.analysis_html,
        model_parameters=config,
        spore_counts_path=input_spore_file,
        title="Infection analysis: " + (config.input_data.meteo or "automated pull"),
    )

    # Plot spore counts overview with infection event background colours.
    overview_fig = utils.plot_spore_infection_overview(
        output_files.events_dataframe,
        output_files.overview_html,
        model_parameters=config,
        spore_counts_result=spore_counts_result,
        spore_counts_path=input_spore_file,
        title="Spore counts & infection overview: "
        + (config.input_data.meteo or "automated pull"),
    )

    # Combined HTML: overview as default view, toggle button switches to analysis.
    utils.write_combined_html(overview_fig, analysis_fig, output_files.html_graph)


if __name__ == "__main__":
    # import argparse
    #
    # parser = argparse.ArgumentParser(description='Run Plasmopy infection modeling.')
    # parser.add_argument('--meteo', metavar='file', required=False,
    #                     help='meteorological data input file')
    # parser.add_argument('--params', metavar='file', required=False,
    #                     help='config file with model parameters')
    # args = parser.parse_args()
    # main(meteo=args.meteo, params=args.params)
    main()
