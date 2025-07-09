"""
Main script orchestrating all modeling steps and launching specific submodules.

"""

import pickle
from datetime import datetime

import hydra
import infection_event
import infection_model
import load_data
import process_data
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

    output_files = utils.create_output_filenames(
        config.input_data.meteo, config.input_data.spore_counts
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

    # Load raw data: vitimeteo timeseries.
    input_meteo_file = config.input_data.meteo
    loaded_data = load_data.load_data(input_meteo_file, logfile)

    # Select columns to use as specified in the config files.
    selected_columns = config.use_columns
    standard_colnames = config.rename_columns

    # Select column formats and tolerated value ranges depending on the specific input data as specified in the config files.
    standard_colformats = config.format_columns

    # Parse site's timezone from config file.
    timezone = config.timezone

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

    daily_temperatures = utils.get_daily_measurements(processed_data, "temperature")
    daily_mean_temperatures = utils.get_daily_mean_measurements(
        processed_data, "temperature"
    )

    # Determine oospore maturation date.
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
    oospore_maturation_datetime = processed_data["datetime"][
        oospore_maturation_datetime_rowindex
    ]

    algorithmic_time_steps = int(config.algorithmic_time_steps // 1)
    if algorithmic_time_steps < 1:
        logf.write(
            "WARNING: algorithmic time-step cannot be lower than 1. Running model at 1 time-step intervals..."
        )
        algorithmic_time_steps = 1
    computational_time_steps = int(config.computational_time_steps // 1)
    if computational_time_steps < 1:
        logf.write(
            "WARNING: computational time-step cannot be lower than 1. Running model at 1 time-step intervals..."
        )
        computational_time_steps = 1
    if oospore_maturation_datetime_rowindex is not None:
        progress_bar = tqdm(
            range(
                oospore_maturation_datetime_rowindex,
                len(processed_data.index),
                computational_time_steps,
            )
        )

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
                + "sporangia_density"
                + ","
                + "secondary_infection"
                + "\n"
            )
            f.write(header_str)

        infection_events = []

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
            )
            infection_prediction.predict_infection()
            infection_events.append(infection_prediction.infection_events)
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
                i = 0
                if (
                    infection_prediction.infection_events["secondary_infections"]
                    is not None
                ):
                    for _secondary_infection in infection_prediction.infection_events[
                        "secondary_infections"
                    ]:
                        output_str = (
                            str(infection_prediction.start_event_rowindex)
                            + ","
                            + str(infection_prediction.start_event_datetime)
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "oospore_maturation"
                                ]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "oospore_germination"
                                ]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "oospore_dispersion"
                                ]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "oospore_infection"
                                ]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events["sporulations"][i]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "sporangia_densities"
                                ][i]
                            )
                            + ","
                            + str(
                                infection_prediction.infection_events[
                                    "secondary_infections"
                                ][i]
                            )
                            + "\n"
                        )
                        f.write(output_str)

        logf.write(
            "\nModel run complete. Infection events details and summary of predicted infection datetimes are stored in 'data/output/'.\n"
        )

        # End the timer.
        t_end = datetime.now()
        logf.write(f"Runtime end: {t_end}\n")

        # Calculate the elapsed time.
        t_diff = t_end - t_start
        logf.write(f"Runtime total: {t_diff}\n")

        # Close the log file.
        logf.close()

        # Plot infection events predictions.
        utils.plot_events(
            infection_events, config, [output_files.pdf_graph, output_files.html_graph]
        )

        with open(output_files.events_dict, "wb") as pickle_file:
            pickle.dump(infection_events, pickle_file)
        with open(output_files.model_params, "wb") as pickle_file:
            pickle.dump(config, pickle_file)


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
