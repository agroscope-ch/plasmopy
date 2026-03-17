# To launch streamlit app on browser, run this command from the terminal:
# streamlit run plasmopy-app.py --server.enableCORS=false
#
# Design principle: the config/main.yaml file is NEVER modified by this app.
# Instead, all user-selected values are passed to the model at launch time as
# Hydra CLI overrides (key=value arguments appended to the python command).
# This preserves the YAML file's structure, ordering, and inline comments.

import os
import subprocess
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
import yaml

from src import utils

# ---------------------------------------------------------------------------
# Load config defaults (read-only — never written back by this app)
# ---------------------------------------------------------------------------
with open("config/main.yaml", "r") as f:
    C = yaml.safe_load(f)


def wide_space_default():
    st.set_page_config(layout="wide")


def read_text_file(file):
    return Path(file).read_text()


wide_space_default()

st.sidebar.title("Plasmopy *v1.0*")


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def meteo_file_selector(folder_path="data/input"):
    filenames = os.listdir(folder_path)
    filenames.insert(0, "")
    selected = st.selectbox("Select an input weather data file:", filenames)
    return os.path.join(folder_path, selected) if selected else ""


def meteo_file_uploader(folder_path="data/input"):
    uploaded = st.file_uploader(
        "Or upload a new weather data file: "
        "*COLUMN ORDER: DATE; TEMPERATURE; HUMIDITY; RAINFALL; LEAF_WETNESS*"
    )
    if uploaded is None:
        return ""
    filepath = os.path.join(folder_path, uploaded.name)
    pd.read_csv(uploaded, sep=";").to_csv(filepath, sep=";", index=False)
    return filepath


def sporecounts_file_selector(folder_path="data/input"):
    filenames = os.listdir(folder_path)
    filenames.insert(0, "")
    selected = st.selectbox(
        "Select an input spore counts data file: *:gray[[optional]]*", filenames
    )
    return os.path.join(folder_path, selected) if selected else ""


def sporecounts_file_uploader(folder_path="data/input"):
    uploaded = st.file_uploader(
        "Or upload a new spore counts data file: *:gray[[optional]]*"
    )
    if uploaded is None:
        return ""
    filepath = os.path.join(folder_path, uploaded.name)
    pd.read_csv(uploaded, sep=";").to_csv(filepath, sep=";", index=False)
    return filepath


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Input data", "Data processing", "Model parameters"])

all_pandas_timezones = pytz.all_timezones

with tab1:
    # ── Weather data ──────────────────────────────────────────────────────
    st.subheader("Weather data")
    automated_weather_pull = st.checkbox(
        "Automated weather data pull",
        value=bool(C["input_data"].get("automated_weather_pull", False)),
    )
    weather_api_query = ""
    input_meteo = ""
    new_input_meteo = ""
    if automated_weather_pull:
        weather_api_query = st.text_input(
            "Weather API URL:",
            value=C["input_data"].get("weather_api_query", "") or "",
        )
    else:
        input_meteo = meteo_file_selector()
        new_input_meteo = meteo_file_uploader()

    # ── Spore counts data ─────────────────────────────────────────────────
    st.subheader("Spore counts data")
    automated_spore_pull = st.checkbox(
        "Automated spore counts pull",
        value=bool(C["input_data"].get("automated_spore_pull", False)),
    )
    spore_counts_api_query = ""
    if automated_spore_pull:
        spore_counts_api_query = st.text_input(
            "Spore counts API URL:",
            value=C["input_data"].get("spore_counts_api_query", "") or "",
        )
    input_spores = sporecounts_file_selector()
    new_input_spores = sporecounts_file_uploader()

    # ── Spore-driven model ────────────────────────────────────────────────
    st.subheader("Spore-driven model")
    _sdm_cfg = C.get("spore_driven_model") or {}
    decision_support_tool_enabled = st.checkbox(
        "Enable spore-driven model",
        value=bool(_sdm_cfg.get("enabled", False)),
    )
    if decision_support_tool_enabled:
        spore_count_threshold = st.number_input(
            "Spore count flat-threshold *:gray[[any day exceeds this count]]*:",
            value=int(_sdm_cfg.get("spore_count_threshold", 40)),
            min_value=0,
        )
        spore_count_lookback_days = st.number_input(
            "Lookback window *[days]*:",
            value=int(_sdm_cfg.get("spore_count_lookback_days", 5)),
            min_value=1,
        )
        spore_count_percent_increase = st.number_input(
            "Min percent increase over lookback *[%]*:",
            value=float(_sdm_cfg.get("spore_count_percent_increase", 30)),
            min_value=0.0,
        )
    else:
        spore_count_threshold = int(_sdm_cfg.get("spore_count_threshold", 40))
        spore_count_lookback_days = int(_sdm_cfg.get("spore_count_lookback_days", 5))
        spore_count_percent_increase = float(
            _sdm_cfg.get("spore_count_percent_increase", 30)
        )

with tab2:
    fast_mode = st.radio("Fast mode:", options=[True, False], index=0)
    measurement_time_interval = st.number_input(
        "Measurement time interval *[min]*:",
        value=int(C["run_settings"]["measurement_time_interval"]),
        min_value=1,
    )
    computational_time_steps = st.number_input(
        "Computational step:",
        value=int(C["run_settings"]["computational_time_steps"]),
        min_value=1,
    )
    algorithmic_time_steps = st.number_input(
        "Algorithmic step:",
        value=int(C["run_settings"]["algorithmic_time_steps"]),
        min_value=1,
    )
    date_format = st.text_input("Date format", C["data_columns"]["format_columns"][0])
    temperature_range = st.slider(
        "Min and Max allowed temperature *[°C]*:",
        -30,
        70,
        (
            C["data_columns"]["format_columns"][1][0],
            C["data_columns"]["format_columns"][1][1],
        ),
    )
    humidity_range = st.slider(
        "Min and Max allowed relative humidity *[%]*:",
        0,
        100,
        (
            C["data_columns"]["format_columns"][2][0],
            C["data_columns"]["format_columns"][2][1],
        ),
    )
    rainfall_range = st.slider(
        "Min and Max allowed rainfall intensity *[mm/h]*:",
        0,
        300,
        (
            C["data_columns"]["format_columns"][3][0],
            C["data_columns"]["format_columns"][3][1],
        ),
    )
    leaf_wetness_range = st.slider(
        "Min and Max allowed leaf wetness *[min]*:",
        0,
        10,
        (
            C["data_columns"]["format_columns"][4][0],
            C["data_columns"]["format_columns"][4][1],
        ),
    )

with tab3:
    st.subheader("Site coordinates")
    longitude = st.number_input(
        "Longitude *[decimal degrees]*:", value=float(C["site"]["longitude"])
    )
    latitude = st.number_input(
        "Latitude *[decimal degrees]*:", value=float(C["site"]["latitude"])
    )
    elevation = st.number_input("Elevation *[m]*:", value=float(C["site"]["elevation"]))
    timezone = st.selectbox(
        "Timezone:",
        all_pandas_timezones,
        index=list(all_pandas_timezones).index(C["site"]["timezone"]),
    )

    st.subheader("Oospore maturation")
    oospore_maturation_date = st.text_input(
        "Date *[%d.%m.%Y %H:%M]* :gray[[keep empty to compute automatically]]:", ""
    )
    oospore_maturation_base_temperature = st.number_input(
        "Base temperature *[°C]*:",
        value=float(C["oospore_maturation"]["base_temperature"]),
        key="maturation_base_temp",
    )
    oospore_maturation_sum_degree_days_threshold = st.number_input(
        "Sum degree days threshold *[°C·day]*:",
        value=float(C["oospore_maturation"]["sum_degree_days_threshold"]),
    )

    st.subheader("Primary Infection Stage 1: oospore germination / moisturization")
    oospore_germination_algorithm = st.radio(
        "Select oospore germination algorithm "
        "*[1 = oospore germination conditions; 2 = soil moisturization]*:",
        options=[1, 2],
        index=int(C["oospore_germination"]["algorithm"]) - 1,
    )
    if oospore_germination_algorithm == 1:
        oospore_germination_relative_humidity_threshold = st.number_input(
            "Relative humidity threshold *[%]*:",
            value=float(C["oospore_germination"]["relative_humidity_threshold"]),
        )
        oospore_germination_leaf_wetness_threshold = st.number_input(
            "Leaf wetness threshold *[min]*:",
            value=float(C["oospore_germination"]["leaf_wetness_threshold"]),
            key="germination_lw_thresh",
        )
        oospore_germination_base_temperature = st.number_input(
            "Base temperature *[°C]*:",
            value=float(C["oospore_germination"]["base_temperature"]),
            key="germination_base_temp",
        )
        oospore_germination_base_duration = st.number_input(
            "Base duration *[h]*:",
            value=float(C["oospore_germination"]["base_duration"]),
        )
        # Keep moisturization params at their config defaults (not shown)
        moisturization_temperature_threshold = C["oospore_germination"][
            "moisturization_temperature_threshold"
        ]
        moisturization_rainfall_threshold = C["oospore_germination"][
            "moisturization_rainfall_threshold"
        ]
        moisturization_rainfall_period = C["oospore_germination"][
            "moisturization_rainfall_period"
        ]
    else:
        moisturization_temperature_threshold = st.number_input(
            "Moisturization temperature threshold *[°C]*:",
            value=float(
                C["oospore_germination"]["moisturization_temperature_threshold"]
            ),
        )
        moisturization_rainfall_threshold = st.number_input(
            "Moisturization rainfall threshold *[mm]*:",
            value=float(C["oospore_germination"]["moisturization_rainfall_threshold"]),
        )
        moisturization_rainfall_period = st.number_input(
            "Moisturization rainfall period *[h]*:",
            value=float(C["oospore_germination"]["moisturization_rainfall_period"]),
        )
        # Keep germination params at their config defaults (not shown)
        oospore_germination_relative_humidity_threshold = C["oospore_germination"][
            "relative_humidity_threshold"
        ]
        oospore_germination_leaf_wetness_threshold = C["oospore_germination"][
            "leaf_wetness_threshold"
        ]
        oospore_germination_base_temperature = C["oospore_germination"][
            "base_temperature"
        ]
        oospore_germination_base_duration = C["oospore_germination"]["base_duration"]

    st.subheader("Primary Infection Stage 2: oospore dispersion by rain splashing")
    oospore_dispersion_rainfall_threshold = st.number_input(
        "Rainfall threshold *[mm]*:",
        value=float(C["oospore_dispersion"]["rainfall_threshold"]),
    )
    oospore_dispersion_latency = st.number_input(
        "Dispersion latency *[h]*:",
        value=float(C["oospore_dispersion"]["latency"]),
    )

    st.subheader("Primary Infection Stage 3: oospore infection")
    oospore_infection_sum_degree_hours_threshold = st.number_input(
        "Sum degree hours threshold *[°C·h]*:",
        value=float(C["primary_infection"]["sum_degree_hours_threshold"]),
        key="primary_infection_dh_thresh",
    )
    oospore_infection_base_temperature = st.number_input(
        "Base temperature *[°C]*:",
        value=float(C["primary_infection"]["base_temperature"]),
        key="primary_infection_base_temp",
    )
    oospore_infection_leaf_wetness_latency = st.number_input(
        "Leaf wetness latency *[h]*:",
        value=float(C["primary_infection"]["leaf_wetness_latency"]),
    )

    st.subheader("Sporulation")
    sporulation_leaf_wetness_threshold = st.number_input(
        "Leaf wetness threshold *[min]*:",
        value=int(C["sporulation"]["leaf_wetness_threshold"]),
        min_value=0,
        key="sporulation_lw_thresh",
    )
    sporulation_min_humidity = st.number_input(
        "Min relative humidity *[%]*:",
        value=float(C["sporulation"]["min_humidity"]),
    )
    sporulation_min_temperature = st.number_input(
        "Min temperature *[°C]*:",
        value=float(C["sporulation"]["min_temperature"]),
        key="sporulation_min_temp",
    )
    sporulation_min_darkness_hours = st.number_input(
        "Min darkness hours *[h]*:",
        value=float(C["sporulation"]["min_darkness_hours"]),
    )

    st.subheader("Sporangia density")
    sporangia_latency = st.number_input(
        "Sporangia latency *[h]*:",
        value=float(C["sporangia"]["latency"]),
    )
    sporangia_min_temperature = st.number_input(
        "Min temperature *[°C]*:",
        value=float(C["sporangia"]["min_temperature"]),
        key="sporangia_min_temp",
    )
    sporangia_max_temperature = st.number_input(
        "Max temperature *[°C]*:",
        value=float(C["sporangia"]["max_temperature"]),
        key="sporangia_max_temp",
    )
    sporangia_max_density = st.number_input(
        "Max density *[sporangia/cm²]*:",
        value=float(C["sporangia"]["max_density"]),
    )

    st.subheader("Spore lifespan")
    _svp_default = C["spore_lifespan"]["saturation_vapor_pressure"]
    saturation_vapor_pressure = st.number_input(
        "Saturation vapor pressure *[hPa]* :gray[[0 if unknown]]:",
        value=float(_svp_default) if _svp_default is not None else 0.0,
        min_value=0.0,
    )
    spore_lifespan_constant = st.number_input(
        "Lifespan constant:",
        value=float(C["spore_lifespan"]["constant"]),
    )

    st.subheader("Secondary infections")
    secondary_infection_min_temperature = st.number_input(
        "Min temperature *[°C]*:",
        value=float(C["secondary_infection"]["min_temperature"]),
        key="secondary_min_temp",
    )
    secondary_infection_max_temperature = st.number_input(
        "Max temperature *[°C]*:",
        value=float(C["secondary_infection"]["max_temperature"]),
        key="secondary_max_temp",
    )
    secondary_infection_leaf_wetness_latency = st.number_input(
        "Leaf wetness latency *[min]*:",
        value=float(C["secondary_infection"]["leaf_wetness_latency"]),
    )
    secondary_infection_sum_degree_hours_threshold = st.number_input(
        "Sum degree hours threshold *[°C·h]*:",
        value=float(C["secondary_infection"]["sum_degree_hours_threshold"]),
        key="secondary_dh_thresh",
    )


# ---------------------------------------------------------------------------
# Resolve active file paths (uploaded > selected > config default)
# ---------------------------------------------------------------------------
active_meteo = (
    ""
    if automated_weather_pull
    else new_input_meteo or input_meteo or C["input_data"].get("meteo", "") or ""
)
active_spores = (
    new_input_spores or input_spores or C["input_data"].get("spore_counts", "") or ""
)


# ---------------------------------------------------------------------------
# Sidebar: manual / readme
# ---------------------------------------------------------------------------
manual_markdown = read_text_file("MANUAL.md")
readme_markdown = read_text_file("README.md")

with st.sidebar.popover("Click to view **:red[MANUAL]**", use_container_width=True):
    st.markdown(manual_markdown, unsafe_allow_html=True)
with st.sidebar.popover("Click to view **:red[README]**", use_container_width=True):
    st.markdown(readme_markdown, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Build Hydra CLI overrides
#
# The config/main.yaml is NEVER written by this function.  All user choices
# from the widgets above are serialised as Hydra override strings and passed
# as extra arguments to `python src/main.py`.  Hydra merges them on top of
# the base YAML at runtime, so the file on disk stays untouched.
#
# Hydra override syntax for nested keys: parent.child=value
# Lists:  key=[v1,v2]   (OmegaConf list literal)
# Strings with spaces or % must be single-quoted: key='%d.%m.%Y %H:%M'
# Null:   key=null
# ---------------------------------------------------------------------------
def _q(v):
    """Quote a string value for OmegaConf if it contains spaces or %."""
    s = str(v)
    if any(c in s for c in (" ", "%", "/")):
        return f"'{s}'"
    return s


def build_hydra_overrides():
    ov = []

    # Input files
    ov.append(f"input_data.meteo={_q(active_meteo) if active_meteo else 'null'}")
    ov.append(
        f"input_data.spore_counts={_q(active_spores) if active_spores else 'null'}"
    )

    # Automated data pulls
    ov.append(
        f"input_data.automated_weather_pull={'true' if automated_weather_pull else 'false'}"
    )
    ov.append(
        f"input_data.weather_api_query="
        f"{_q(weather_api_query) if weather_api_query else 'null'}"
    )
    ov.append(
        f"input_data.automated_spore_pull={'true' if automated_spore_pull else 'false'}"
    )
    ov.append(
        f"input_data.spore_counts_api_query="
        f"{_q(spore_counts_api_query) if spore_counts_api_query else 'null'}"
    )

    # Spore-driven model
    ov.append(
        f"spore_driven_model.enabled="
        f"{'true' if decision_support_tool_enabled else 'false'}"
    )
    ov.append(f"spore_driven_model.spore_count_threshold={spore_count_threshold}")
    ov.append(
        f"spore_driven_model.spore_count_lookback_days={spore_count_lookback_days}"
    )
    ov.append(
        f"spore_driven_model.spore_count_percent_increase={spore_count_percent_increase}"
    )

    # Site
    ov.append(f"site.latitude={latitude}")
    ov.append(f"site.longitude={longitude}")
    ov.append(f"site.elevation={elevation}")
    ov.append(f"site.timezone={_q(timezone)}")

    # Run settings
    ov.append(f"run_settings.fast_mode={'true' if fast_mode else 'false'}")
    ov.append(f"run_settings.measurement_time_interval={measurement_time_interval}")
    ov.append(f"run_settings.computational_time_steps={computational_time_steps}")
    ov.append(f"run_settings.algorithmic_time_steps={algorithmic_time_steps}")

    # Data columns — format_columns keys are integer-keyed dict in the YAML
    ov.append(f"data_columns.format_columns.0={_q(date_format)}")
    ov.append(
        f"data_columns.format_columns.1=[{temperature_range[0]},{temperature_range[1]}]"
    )
    ov.append(
        f"data_columns.format_columns.2=[{humidity_range[0]},{humidity_range[1]}]"
    )
    ov.append(
        f"data_columns.format_columns.3=[{rainfall_range[0]},{rainfall_range[1]}]"
    )
    ov.append(
        f"data_columns.format_columns.4=[{leaf_wetness_range[0]},{leaf_wetness_range[1]}]"
    )

    # Oospore maturation
    if oospore_maturation_date:
        ov.append(f"oospore_maturation.date={_q(oospore_maturation_date)}")
    ov.append(
        f"oospore_maturation.base_temperature={oospore_maturation_base_temperature}"
    )
    ov.append(
        f"oospore_maturation.sum_degree_days_threshold="
        f"{oospore_maturation_sum_degree_days_threshold}"
    )

    # Oospore germination
    ov.append(f"oospore_germination.algorithm={oospore_germination_algorithm}")
    ov.append(
        f"oospore_germination.relative_humidity_threshold="
        f"{oospore_germination_relative_humidity_threshold}"
    )
    ov.append(
        f"oospore_germination.leaf_wetness_threshold="
        f"{oospore_germination_leaf_wetness_threshold}"
    )
    ov.append(
        f"oospore_germination.base_temperature={oospore_germination_base_temperature}"
    )
    ov.append(f"oospore_germination.base_duration={oospore_germination_base_duration}")
    ov.append(
        f"oospore_germination.moisturization_temperature_threshold="
        f"{moisturization_temperature_threshold}"
    )
    ov.append(
        f"oospore_germination.moisturization_rainfall_threshold="
        f"{moisturization_rainfall_threshold}"
    )
    ov.append(
        f"oospore_germination.moisturization_rainfall_period="
        f"{moisturization_rainfall_period}"
    )

    # Oospore dispersion
    ov.append(
        f"oospore_dispersion.rainfall_threshold={oospore_dispersion_rainfall_threshold}"
    )
    ov.append(f"oospore_dispersion.latency={oospore_dispersion_latency}")

    # Primary infection
    ov.append(
        f"primary_infection.sum_degree_hours_threshold="
        f"{oospore_infection_sum_degree_hours_threshold}"
    )
    ov.append(
        f"primary_infection.base_temperature={oospore_infection_base_temperature}"
    )
    ov.append(
        f"primary_infection.leaf_wetness_latency={oospore_infection_leaf_wetness_latency}"
    )

    # Sporulation
    ov.append(
        f"sporulation.leaf_wetness_threshold={sporulation_leaf_wetness_threshold}"
    )
    ov.append(f"sporulation.min_humidity={sporulation_min_humidity}")
    ov.append(f"sporulation.min_temperature={sporulation_min_temperature}")
    ov.append(f"sporulation.min_darkness_hours={sporulation_min_darkness_hours}")

    # Sporangia
    ov.append(f"sporangia.latency={sporangia_latency}")
    ov.append(f"sporangia.min_temperature={sporangia_min_temperature}")
    ov.append(f"sporangia.max_temperature={sporangia_max_temperature}")
    ov.append(f"sporangia.max_density={sporangia_max_density}")

    # Spore lifespan
    svp = saturation_vapor_pressure if saturation_vapor_pressure != 0.0 else "null"
    ov.append(f"spore_lifespan.saturation_vapor_pressure={svp}")
    ov.append(f"spore_lifespan.constant={spore_lifespan_constant}")

    # Secondary infection
    ov.append(
        f"secondary_infection.min_temperature={secondary_infection_min_temperature}"
    )
    ov.append(
        f"secondary_infection.max_temperature={secondary_infection_max_temperature}"
    )
    ov.append(
        f"secondary_infection.leaf_wetness_latency="
        f"{secondary_infection_leaf_wetness_latency}"
    )
    ov.append(
        f"secondary_infection.sum_degree_hours_threshold="
        f"{secondary_infection_sum_degree_hours_threshold}"
    )

    return ov


# ---------------------------------------------------------------------------
# Sidebar: run button
# ---------------------------------------------------------------------------
start_button = st.sidebar.button(
    "**RUN MODEL**", type="primary", use_container_width=True
)
if start_button:
    overrides = build_hydra_overrides()
    command = ["poetry", "run", "python3", "src/main.py"] + overrides
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


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if active_meteo or automated_weather_pull:
    output_files = utils.create_output_filenames(
        active_meteo or None,
        active_spores or None,
        output_dir=C.get("output", {}).get("directory"),
        run_name=C.get("output", {}).get("run_name"),
    )

    if os.path.isfile(output_files.logfile):
        progress_text = "Loading: model prediction data..."
        bar = st.progress(0, text=progress_text)

        # Download buttons
        col1, col2, col3, col4 = st.columns(4)
        with open(output_files.logfile, "r") as lf:
            log = lf.read()
        with col1:
            st.download_button("Download logfile", data=log, file_name="logfile.txt")
        with open(output_files.events_text, "r") as ef:
            events = ef.read()
        with col2:
            st.download_button("Download events", data=events, file_name="events.csv")
        with open(output_files.infection_datetimes, "r") as inf_f:
            infections = inf_f.read()
        with col3:
            st.download_button(
                "Download infection datetimes",
                data=infections,
                file_name="infections.csv",
            )
        with open(output_files.analysis_pdf, "rb") as pdf_f:
            PDFbyte = pdf_f.read()
        with col4:
            st.download_button(
                "Download PDF graph", data=PDFbyte, file_name="graph.pdf"
            )

        bar.progress(40, text=progress_text)

        try:
            # ── Analysis plot: full infection-chain view ──────────────────
            if os.path.isfile(output_files.analysis_html):
                st.subheader("Infection analysis")
                components.html(
                    Path(output_files.analysis_html).read_text(encoding="utf-8"),
                    height=730,
                    scrolling=True,
                )
            bar.progress(70, text=progress_text)

            # ── Overview plot: spore counts + coloured backgrounds ────────
            if os.path.isfile(output_files.overview_html):
                st.subheader("Spore counts & infection overview")
                components.html(
                    Path(output_files.overview_html).read_text(encoding="utf-8"),
                    height=530,
                    scrolling=True,
                )
            bar.progress(100, text="Model prediction data: loading complete.")

        except (TypeError, FileNotFoundError):
            st.info(
                "No infection prediction results found — "
                "run a new prediction with the RUN MODEL button to access results."
            )
            bar.progress(0, text="Model prediction data: run a new simulation.")

    else:
        st.info("No corresponding simulation found, run a new one.")

else:
    st.info(
        "Select a weather data file (or enable automated pull) "
        "and run a new prediction with the RUN MODEL button."
    )
