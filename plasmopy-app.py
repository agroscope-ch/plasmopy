# To launch streamlit app on browser, run this command from the terminal:
# streamlit run plasmopy-app.py --server.enableCORS=false

import os
import pickle
import subprocess
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st
import yaml

from src import utils

with open("config/main.yaml", "r") as f:
    config = yaml.safe_load(f)


def wide_space_default():
    st.set_page_config(layout="wide")


def read_text_file(file):
    return Path(file).read_text()


wide_space_default()

st.sidebar.title(
    """
Plasmopy *v1.0*
"""
)


with open("config/main.yaml", "r") as f:
    config_yaml = f.readlines()
    config_yaml = "".join(config_yaml)
    loaded_config = yaml.safe_load(f)


def meteo_file_selector(folder_path="data/input"):
    filenames = os.listdir(folder_path)
    filenames.insert(0, "")  # <-- default empty
    selected_filename = st.selectbox("Select an input weather data file:", filenames)
    filepath = os.path.join(folder_path, selected_filename)
    if selected_filename == "":
        filepath = ""
    return filepath


def meteo_file_uploader(folder_path="data/input"):
    selected_filename = None
    selected_filename = st.file_uploader(
        "Or upload a new weather data file: *COLUMN ORDER: DATE; TEMPERATURE; HUMIDITY; RAINFALL; LEAF_WETNESS*"
    )
    if selected_filename is None:
        filepath = ""
    else:
        filepath = os.path.join(folder_path, selected_filename.name)
        dataframe = pd.read_csv(selected_filename, sep=";")
        dataframe.to_csv(filepath, sep=";", index=False)
        st.write(dataframe)
    return filepath


def sporecounts_file_selector(folder_path="data/input"):
    filenames = os.listdir(folder_path)
    filenames.insert(0, "")  # <-- default empty
    selected_filename = st.selectbox(
        "Select an input spore counts data file: *:gray[[optional]]*", filenames
    )
    filepath = os.path.join(folder_path, selected_filename)
    if selected_filename == "":
        filepath = ""
    return filepath


def sporecounts_file_uploader(folder_path="data/input"):
    selected_filename = None
    selected_filename = st.file_uploader(
        "Or upload a new spore counts data file: *:gray[[optional]]*"
    )
    if selected_filename is None:
        filepath = ""
    else:
        filepath = os.path.join(folder_path, selected_filename.name)
        dataframe = pd.read_csv(selected_filename, sep=";")
        dataframe.to_csv(filepath, sep=";", index=False)
        st.write(dataframe)
    return filepath


tab1, tab2, tab3 = st.tabs(["Input data", "Data processing", "Model parameters"])

all_pandas_timezones = pytz.all_timezones

with tab1:
    input_meteo = meteo_file_selector()
    new_input_meteo = meteo_file_uploader()
    input_spores = sporecounts_file_selector()
    new_input_spores = sporecounts_file_uploader()
with tab2:
    measurement_time_interval = st.number_input(
        "Measurement time interval *[min]*:",
        value=int(config["measurement_time_interval"]),
        min_value=1,
    )
    computational_time_steps = st.number_input(
        "Computational step:",
        value=int(config["computational_time_steps"]),
        min_value=1,
    )
    algorithmic_time_steps = st.number_input(
        "Algorithmic step:",
        value=int(config["algorithmic_time_steps"]),
        min_value=1,
    )
    date_format = st.text_input("Date format", config["format_columns"][0])
    temperature_range = st.slider(
        "Min and Max allowed temperature *[°C]*:",
        -30,
        70,
        (config["format_columns"][1][0], config["format_columns"][1][1]),
    )
    humidity_range = st.slider(
        "Min and Max allowed relative humidity *[%]*:",
        0,
        100,
        (config["format_columns"][2][0], config["format_columns"][2][1]),
    )
    rainfall_range = st.slider(
        "Min and Max allowed rainfall intensity *[mm/h]*:",
        0,
        300,
        (config["format_columns"][3][0], config["format_columns"][3][1]),
    )
    leaf_wetness_range = st.slider(
        "Min and Max allowed leaf wetness *[min]*:",
        0,
        10,
        (config["format_columns"][4][0], config["format_columns"][4][1]),
    )
with tab3:
    st.subheader("Site coordinates")
    longitude = st.number_input(
        "Longitude *[decimal degrees]*: ", value=float(config["longitude"])
    )
    latitude = st.number_input(
        "Latitude *[decimal degrees]*: ", value=float(config["latitude"])
    )
    elevation = st.number_input("Elevation *[m]*: ", value=float(config["elevation"]))
    timezone = st.selectbox(
        "Timezone:",
        all_pandas_timezones,
        index=all_pandas_timezones.index("Europe/Zurich"),
    )
    st.subheader("Oospore maturation")
    oospore_maturation_date = st.text_input(
        "Date *[%d.%m.%Y %H:%M] :gray[[keep empty to compute automatically]]*:", None
    )
    oospore_maturation_base_temperature = st.number_input(
        "Base temperature *[°C]*: ",
        value=float(config["oospore_maturation_base_temperature"]),
    )
    oospore_maturation_sum_degree_days_threshold = st.number_input(
        "Sum degree days threshold *[°C]*: ",
        value=float(config["oospore_maturation_sum_degree_days_threshold"]),
    )
    st.subheader("Primary Infection Stage 1: oospore germination / moisturization")
    oospore_germination_algorithm = st.radio(
        "Select oospore germination algorithm *[1 for oospore germination; 2 for moisturization]*:",
        options=[1, 2],
        index=1,
    )
    if oospore_germination_algorithm == 1:
        oospore_germination_relative_humidity_threshold = st.number_input(
            "oospore_germination_relative_humidity_threshold:",
            value=float(config["oospore_germination_relative_humidity_threshold"]),
        )
        oospore_germination_leaf_wetness_threshold = st.number_input(
            "oospore_germination_leaf_wetness_threshold:",
            value=float(config["oospore_germination_leaf_wetness_threshold"]),
        )
        oospore_germination_base_temperature = st.number_input(
            "oospore_germination_base_temperature:",
            value=float(config["oospore_germination_base_temperature"]),
        )
        oospore_germination_base_duration = st.number_input(
            "oospore_germination_base_duration:",
            value=float(config["oospore_germination_base_duration"]),
        )
    elif oospore_germination_algorithm == 2:
        moisturization_temperature_threshold = st.number_input(
            "moisturization_temperature_threshold:",
            value=float(config["moisturization_temperature_threshold"]),
        )
        moisturization_rainfall_threshold = st.number_input(
            "moisturization_rainfall_threshold:",
            value=float(config["moisturization_rainfall_threshold"]),
        )
        moisturization_rainfall_period = st.number_input(
            "moisturization_rainfall_period:",
            value=float(config["moisturization_rainfall_period"]),
        )
    st.subheader("Primary Infection Stage 2: oospore dispersion by rain splashing")
    oospore_dispersion_rainfall_threshold = st.number_input(
        "oospore_dispersion_rainfall_threshold:",
        value=float(config["oospore_dispersion_rainfall_threshold"]),
    )
    oospore_dispersion_latency = st.number_input(
        "oospore_dispersion_latency:",
        value=float(config["oospore_dispersion_latency"]),
    )
    st.subheader("Primary Infection Stage 3: oospore infection")
    oospore_infection_sum_degree_hours_threshold = st.number_input(
        "oospore_infection_sum_degree_hours_threshold:",
        value=float(config["oospore_infection_sum_degree_hours_threshold"]),
    )
    oospore_infection_base_temperature = st.number_input(
        "oospore_infection_base_temperature:",
        value=float(config["oospore_infection_base_temperature"]),
    )
    oospore_infection_leaf_wetness_latency = st.number_input(
        "oospore_infection_leaf_wetness_latency:",
        value=float(config["oospore_infection_leaf_wetness_latency"]),
    )
    st.subheader("Sporulation")
    sporulation_leaf_wetness_threshold = st.number_input(
        "sporulation_leaf_wetness_threshold:",
        value=float(config["sporulation_leaf_wetness_threshold"]),
    )
    sporulation_min_humidity = st.number_input(
        "sporulation_min_humidity:",
        value=float(config["sporulation_min_humidity"]),
    )
    sporulation_min_temperature = st.number_input(
        "sporulation_min_temperature:",
        value=float(config["sporulation_min_temperature"]),
    )
    sporulation_min_darkness_hours = st.number_input(
        "sporulation_min_darkness_hours:",
        value=float(config["sporulation_min_darkness_hours"]),
    )
    st.subheader("Sporangia density")
    sporangia_latency = st.number_input(
        "sporangia_latency:",
        value=float(config["sporangia_latency"]),
    )
    sporangia_min_temperature = st.number_input(
        "sporangia_min_temperature:",
        value=float(config["sporangia_min_temperature"]),
    )
    sporangia_max_temperature = st.number_input(
        "sporangia_max_temperature:",
        value=float(config["sporangia_max_temperature"]),
    )
    sporangia_max_density = st.number_input(
        "sporangia_max_density:",
        value=float(config["sporangia_max_density"]),
    )
    st.subheader("Spore die-off")
    saturation_vapor_pressure = st.number_input(
        "Saturation vapor pressure *[hPa]* :gray[[keep empty if unknown]]:",
        value=config["saturation_vapor_pressure"],
    )
    spore_lifespan_constant = st.number_input(
        "spore_lifespan_constant:",
        value=float(config["spore_lifespan_constant"]),
    )
    st.subheader("Secondary infections")
    secondary_infection_min_temperature = st.number_input(
        "secondary_infection_min_temperature:",
        value=float(config["secondary_infection_min_temperature"]),
    )
    secondary_infection_max_temperature = st.number_input(
        "secondary_infection_max_temperature:",
        value=float(config["secondary_infection_max_temperature"]),
    )
    secondary_infection_leaf_wetness_latency = st.number_input(
        "secondary_infection_leaf_wetness_latency:",
        value=float(config["secondary_infection_leaf_wetness_latency"]),
    )
    secondary_infection_sum_degree_hours_threshold = st.number_input(
        "secondary_infection_sum_degree_hours_threshold:",
        value=float(config["secondary_infection_sum_degree_hours_threshold"]),
    )

if input_meteo:
    config["input_data"]["meteo"] = input_meteo
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
else:
    config["input_data"]["meteo"] = None
if input_spores:
    config["input_data"]["spore_counts"] = input_spores
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
else:
    config["input_data"]["spore_counts"] = None
if new_input_meteo:
    config["input_data"]["meteo"] = os.path.relpath(new_input_meteo)
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if new_input_spores:
    config["input_data"]["spore_counts"] = os.path.relpath(new_input_spores)
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if measurement_time_interval:
    config["measurement_time_interval"] = measurement_time_interval
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if computational_time_steps:
    config["computational_time_steps"] = computational_time_steps
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if algorithmic_time_steps:
    config["algorithmic_time_steps"] = algorithmic_time_steps
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if date_format:
    config["format_columns"][0] = date_format
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if temperature_range:
    (config["format_columns"][1][0], config["format_columns"][1][1]) = temperature_range
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if humidity_range:
    (config["format_columns"][2][0], config["format_columns"][2][1]) = humidity_range
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if rainfall_range:
    (config["format_columns"][3][0], config["format_columns"][3][1]) = rainfall_range
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if leaf_wetness_range:
    (
        config["format_columns"][4][0],
        config["format_columns"][4][1],
    ) = leaf_wetness_range
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if longitude:
    config["longitude"] = longitude
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if latitude:
    config["latitude"] = latitude
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if elevation:
    config["elevation"] = elevation
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if timezone:
    config["timezone"] = timezone
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_maturation_date:
    config["oospore_maturation_date"] = oospore_maturation_date
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_maturation_base_temperature:
    config["oospore_maturation_base_temperature"] = oospore_maturation_base_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_maturation_sum_degree_days_threshold:
    config[
        "oospore_maturation_sum_degree_days_threshold"
    ] = oospore_maturation_sum_degree_days_threshold
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_germination_algorithm:
    config["oospore_germination_algorithm"] = oospore_germination_algorithm
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_germination_algorithm == 1:
    if oospore_germination_relative_humidity_threshold:
        config[
            "oospore_germination_relative_humidity_threshold"
        ] = oospore_germination_relative_humidity_threshold
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
    if oospore_germination_leaf_wetness_threshold:
        config[
            "oospore_germination_leaf_wetness_threshold"
        ] = oospore_germination_leaf_wetness_threshold
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
    if oospore_germination_base_temperature:
        config[
            "oospore_germination_base_temperature"
        ] = oospore_germination_base_temperature
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
    if oospore_germination_base_duration:
        config["oospore_germination_base_duration"] = oospore_germination_base_duration
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
elif oospore_germination_algorithm == 2:
    if moisturization_temperature_threshold:
        config[
            "moisturization_temperature_threshold"
        ] = moisturization_temperature_threshold
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
    if moisturization_rainfall_threshold:
        config["moisturization_rainfall_threshold"] = moisturization_rainfall_threshold
        with open("config/main.yaml", "w") as f:
            yaml.dump(config, f)
if oospore_dispersion_rainfall_threshold:
    config[
        "oospore_dispersion_rainfall_threshold"
    ] = oospore_dispersion_rainfall_threshold
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_dispersion_latency:
    config["oospore_dispersion_latency"] = oospore_dispersion_latency
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_infection_sum_degree_hours_threshold:
    config[
        "oospore_infection_sum_degree_hours_threshold"
    ] = oospore_infection_sum_degree_hours_threshold
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_infection_base_temperature:
    config["oospore_infection_base_temperature"] = oospore_infection_base_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if oospore_infection_leaf_wetness_latency:
    config[
        "oospore_infection_leaf_wetness_latency"
    ] = oospore_infection_leaf_wetness_latency
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporulation_leaf_wetness_threshold:
    config["sporulation_leaf_wetness_threshold"] = sporulation_leaf_wetness_threshold
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporulation_min_humidity:
    config["sporulation_min_humidity"] = sporulation_min_humidity
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporulation_min_temperature:
    config["sporulation_min_temperature"] = sporulation_min_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporulation_min_darkness_hours:
    config["sporulation_min_darkness_hours"] = sporulation_min_darkness_hours
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporangia_latency:
    config["sporangia_latency"] = sporangia_latency
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporangia_min_temperature:
    config["sporangia_min_temperature"] = sporangia_min_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporangia_max_temperature:
    config["sporangia_max_temperature"] = sporangia_max_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if sporangia_max_density:
    config["sporangia_max_density"] = sporangia_max_density
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if saturation_vapor_pressure:
    config["saturation_vapor_pressure"] = saturation_vapor_pressure
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if spore_lifespan_constant:
    config["spore_lifespan_constant"] = spore_lifespan_constant
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if secondary_infection_min_temperature:
    config["secondary_infection_min_temperature"] = secondary_infection_min_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if secondary_infection_max_temperature:
    config["secondary_infection_max_temperature"] = secondary_infection_max_temperature
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if secondary_infection_leaf_wetness_latency:
    config[
        "secondary_infection_leaf_wetness_latency"
    ] = secondary_infection_leaf_wetness_latency
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)
if secondary_infection_sum_degree_hours_threshold:
    config[
        "secondary_infection_sum_degree_hours_threshold"
    ] = secondary_infection_sum_degree_hours_threshold
    with open("config/main.yaml", "w") as f:
        yaml.dump(config, f)


manual_markdown = read_text_file("MANUAL.md")
readme_markdown = read_text_file("README.md")

with st.sidebar.popover("Click to view **:red[MANUAL]**", use_container_width=True):
    st.markdown(manual_markdown, unsafe_allow_html=True)
with st.sidebar.popover("Click to view **:red[README]**", use_container_width=True):
    st.markdown(readme_markdown, unsafe_allow_html=True)

start_button = st.sidebar.button(
    "**RUN MODEL**", type="primary", use_container_width=True
)
if start_button:
    command = ["make", "run"]
    st.info("Computing infection predictions...")
    model_run = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    model_info = st.empty()
    while model_run.poll() is None:
        line = model_run.stdout.readline()
        if not line:
            continue
        model_info.write(line.strip())

if input_meteo or new_input_meteo:
    output_files = utils.create_output_filenames(
        config["input_data"]["meteo"], config["input_data"]["spore_counts"]
    )
    if os.path.isfile(output_files.logfile) is True:
        progress_text = "Loading: model prediction data..."
        bar = st.progress(0, text=progress_text)

        col1, col2, col3, col4 = st.columns(4)

        with open(output_files.logfile, "r") as log_file:
            log = log_file.read()
        with col1:
            st.download_button("Download logfile", data=log, file_name="logfile.txt")
        with open(output_files.events_text, "r") as events_file:
            events = events_file.read()
        with col2:
            st.download_button("Download events", data=events, file_name="events.csv")
        with open(output_files.infection_datetimes, "r") as infections_file:
            infections = infections_file.read()
        with col3:
            st.download_button(
                "Download infection datetimes",
                data=infections,
                file_name="infections.csv",
            )
        with open(output_files.pdf_graph, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        with col4:
            st.download_button(
                "Download PDF graph", data=PDFbyte, file_name="graph.pdf"
            )

        with open(output_files.events_dict, "rb") as pickle_file:
            infection_events = pickle.load(pickle_file)
        bar.progress(33, text=progress_text)
        with open(output_files.model_params, "rb") as pickle_file:
            model_parameters = pickle.load(pickle_file)
        bar.progress(66, text=progress_text)

        try:
            fig = utils.plot_events(
                infection_events,
                model_parameters,
                [output_files.pdf_graph, output_files.html_graph],
            )
            st.subheader("Infection events")
            st.plotly_chart(fig, use_container_width=True)

            bar.progress(100, text="Model prediction data: loading complete.")

        except TypeError:
            st.info(
                "No infection prediction results found, run a new prediction with the RUN MODEL button to access results."
            )
            bar.progress(0, text="Model prediction data: run a new simulation.")
        except FileNotFoundError:
            st.info(
                "No infection prediction results found, run a new prediction with the RUN MODEL button to access results."
            )
            bar.progress(0, text="Model prediction data:  run a new simulation.")
    else:
        st.info("No corresponding simulation found, run a new one.")
else:
    st.info("Select stored data or run a new prediction with the RUN MODEL button.")


## Show Weather Data ---> Too much memory for streamlit web-app, left out for now.
# progress_text = "Loading: meteorological data..."
# bar = st.progress(0, text=progress_text)
# df = pd.read_csv(output_files.processed_file_meteo)
# df["datetime"] = [
#     datetime.strftime(datetime.strptime(x, "%Y-%m-%d %H:%M:%S%z"), "%d/%m/%y %H:%M")
#     for x in df["datetime"]
# ]
# variable_displaynames = {
#     "temperature": "Temperature [°C]",
#     "humidity": "Relative humidity [%]",
#     "rainfall": "Rainfall intensity [mm/hr]",
#     "leaf_wetness": "Leaf wetness [minutes]",
# }
#
# for i, var in enumerate(variable_displaynames.keys()):
#     progress_text = "Loading: " + var + "..."
#     percent_complete = i / len(variable_displaynames.keys())
#     bar.progress(percent_complete, text=progress_text)
#     st.subheader(variable_displaynames[var])
#     plot = (
#         alt.Chart(df)
#         .mark_line()
#         .encode(
#             x=alt.X("datetime", sort=None).title(None), y=alt.Y(var).title(None)
#         )
#     )
#     st.altair_chart(plot, use_container_width=True)
# bar.progress(100, text="Meteorological data: loading complete.")
