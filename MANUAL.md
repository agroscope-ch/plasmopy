# Plasmopy v1.0
# Manual


## Input data - Weather variables

Input data needs to be in the form of timeseries in a semicolon-delimited CSV file, where the positioning of columns must be precisely kept in the following order:

1. **Date and time** of measurement in the *%d.%m.%Y %H:%M* local timezone format.

2. **Average temperature** *[°C]* in degrees Celsius.

3. **Relative humidity** *[%]* in percentages.

4. **Rainfall intensity** *[mm/h]* in millimeters per hour.

5. **Leaf wetness** *[min]* in minutes of wetness over 10 minutes (by default, or whatever sampling period is available).

Such timeseries data is publicly available for Switzerland from the Agroscope weather stations, accessible at [Agrometeo](https://www.agrometeo.ch/meteorologie).

Examples of input weather data are available in `data/input/`.

Be sure to update accordingly the most important input-dependent parameters in `config/main.yaml`: *measurement_time_interval*, *computational_time_steps*, *algorithmic_time_steps*.

The file can be managed directly, or through the streamlit web-app, as detailed in the [README](https://github.com/agroscope-ch/plasmopy/blob/main/README.md).


**_Example_**:

If the data sampling interval consists in weather data rows generated every 10 minutes, then *measurement_time_interval* is 10.

Accordingly, if computational_time_steps is set to 6, a simulated infection event is launched every 6x10 minutes, i.e. once every hour.

If the *algorithmic_time_steps* is set to 1, specific algorithmic loops within that simulated infection event are instead set to analyze the data at every row, i.e. looking in detail at the highest possible resolution of 10 minutes.

If the *algorithmic_time_steps* is set to 6, the specific algorithmic loops would only check the necessary weather conditions at a hourly-rate, thus decreasing the simulation precision while increasing the simulation speed.

### Optional input data - Spore counts

Input spore counts data (e.g. from qPCR, microscopy, ...) columns must be ordered and formatted in the following way:

1. Date of daily spore counts in the *%d.%m.%Y %H:%M* local timezone format.

2. Spore counts.



## Workflow description


### Data Loading Function

The data loading function load_data is responsible for importing raw time series data from a specified file path. It accepts two input arguments:

*raw_data_path* (str): The file path of the raw data, typically formatted as a semicolon-delimited CSV file.

*logfile* (str): The path to a log file where the function records details about the data loading process.

The function begins by appending a log entry that indicates the start of the data loading process, including the provided file path. It then attempts to read the data using the pandas library's read_csv function with a semicolon delimiter (sep=";"). If the data is successfully read into a pandas DataFrame, the function logs the number of rows in the dataset and provides summary statistics (minimum and maximum values) for each of the columns (excluding the first column).
If any error occurs during the data loading process (e.g., if the file cannot be read), an error message is written to the log file, and the function terminates the execution by calling sys.exit().
The function returns the loaded DataFrame if successful. If an error occurs, the function prints the error message and terminates the process.


### Data Processing Functions

The Python code consists of two primary functions: *map_to_timegrid* and process_data. The *map_to_timegrid* function is designed to create a consistent time grid onto which measurement data can be mapped, ensuring that missing rows and uneven time intervals are avoided.
The *process_data function*, which is the core of the data processing workflow, takes multiple inputs, including a raw pandas DataFrame (*input_data: meteo*), column indices of interest (*selected_columns*), standard column names (*standard_colnames*), column formats (*standard_colformats*), timezone (*timezone*), model parameters (*model_parameters*), and file paths for logs (*logfile*) and output data (*outfile*). This function processes the data to ensure that the measurement values are within specified tolerance ranges and that any missing or erroneous data is handled appropriately.

**Column Selection and Renaming**
The function first extracts the selected columns from the input data based on the provided indices and logs the selected columns and their corresponding standard names. The columns are then renamed according to the standard_colnames mapping.

**Datetime Parsing and Localization**
The first column, assumed to be the datetime column, is parsed into a pandas datetime format and localized to the specified timezone. An error is logged if the datetime column cannot be parsed correctly.

**Time Grid Creation**
A consistent time grid is generated using the start_timegrid and end_timegrid values from the input data, with the frequency determined by the measurement_time_interval parameter in the model_parameters. This time grid is then merged with the processed data to handle missing timestamps by filling in the gaps.

**Data Type Validation and Quality Filtering**
The function iterates through each data column (excluding the datetime column) and attempts to convert the data to numeric format. Non-numeric values are coerced to NaN. The data is then checked for values outside of the specified acceptable ranges (given in standard_colformats). Out-of-range values are either replaced with NaN or, in the case of specific variables (e.g., leaf wetness), corrected to the maximum allowable value.

**Handling Missing and Out-of-Range Data**
Missing or out-of-range values are identified and logged. A custom handling process is implemented for the leaf wetness variable, where values exceeding the specified range are corrected. The function fills missing values (either from data gaps or out-of-range values) using linear interpolation between adjacent valid values.

**Data Output and Logging**
After processing, the resulting data is saved to a CSV file, and the operations are logged to a specified log file. Any errors encountered during file I/O operations are logged.
The function returns the processed data as a pandas DataFrame, with the cleaned and interpolated values, along with the final output file and log file paths.

**Error Handling and Logging**
Throughout the process, detailed error messages are written to the log file. This includes warnings for out-of-range values, formatting issues, and potential mismatches in the input data structure. The log also captures the number of out-of-range and missing values replaced through interpolation.

### Infection event class

*\__init\__(self, timeseries, parameters, start_event_rowindex, oospore_maturation_date, daily_mean_temperatures, algorithmic_time_steps, logfile, oospore_infection_datetimes)*
The initialization method of the InfectionEvent class. This method sets up the object by assigning input values to instance variables. These include the timeseries of data, model parameters, index of the start event, date of oospore maturation, daily mean temperatures, algorithmic time steps, a logfile for logging outputs, and a list of infection datetimes. The method also computes the datetime corresponding to the start of the event from the provided timeseries and assigns a unique ID based on the row index of the start event.

*predict_infection(self)*
This method calls the run_infection_model function from the infection_model module to compute the infection events based on the initialized instance variables. It passes the relevant data, including timeseries, model parameters, oospore maturation date, and other relevant inputs, and stores the output in the infection_events attribute.

*\__str\__(self)*
The string representation method returns a human-readable string of the InfectionEvent object. The string includes the event ID, start datetime of the event, and the computed infection events, providing an overview of the object's state.


## Infection model

The `main.py` and `infection_model.py` Python scripts orchestrate a computational framework for modeling infection dynamics based on meteorological and biological parameters. Below, the main components of the methodology are outlined:

**Data Preprocessing and Initialization**
The script requires input data formatted as a time-series DataFrame, model parameters provided via a configuration file, and supporting metadata such as time zones and column formats. Model parameters are validated and logged, ensuring consistency across computational stages.

**Determination of Oospore Maturation**
The get_oospore_maturation_date function identifies the date of oospore maturation using daily temperature data. If a predefined maturation date is unavailable, the function computes it based on degree-day thresholds and writes results to a log file. Missing data or unmet threshold conditions halt the process.

**Infection Event Construction**
The function get_infection_events_dictionary compiles and organizes data into a dictionary containing key infection event datetimes (e.g., oospore germination, sporulation) and their associated parameters (e.g., sporangia density, spore lifespan).


> Primary Infection Prediction

The *run_infection_model* function coordinates the infection prediction process, starting with primary infection stages:

**Oospore Germination**: Simulated based on relative humidity, temperature thresholds, and environmental conditions.

**Oospore Dispersion**: Modeled as a rainfall-driven process with latency considerations.

**Oospore Infection**: Dependent on leaf wetness, degree-hour accumulation, and environmental conditions.


> Secondary Infection and Incubation Dynamics

Subsequent infection stages include:

**Incubation Period**: Duration is computed based on mean temperatures.

**Sporulation**: Triggered by environmental factors such as humidity, temperature, and darkness duration.

**Sporangia Density**: Simulated as a function of temperature and latency parameters.

**Spore Lifespan**: Calculated using vapor pressure and lifespan constants.

**Secondary Infections**: Modeled based on spore availability, temperature thresholds, and leaf wetness conditions.

### Logging and Error Handling

The script employs robust error logging to identify issues such as missing configuration parameters or unfulfilled biological conditions. Warnings are issued if model requirements (e.g., maturation thresholds) are unmet.

### Output

The final output is a structured dictionary summarizing infection event properties and datetimes. This dictionary serves as the primary interface for downstream analyses or reporting.



## Infection algorithms

### 1. Oospore maturation

If oospore maturation date not observed in the field thus cannot be manually inserted, then compute it with the following formula [Gehmann 1991]:

<div align="center">

</div>


### 2. Oospore germination

Stage 1 of primary infection, i.e. oospore infection from soil. This stage can be run by either one of two algorithms:

**Algorithm 1, oospore development**:

<div align="center">


</div>


If no datetime could be found due to never reaching the conditions, then the oospore germination datetime can not be found and the model is interrupted for the whole season.


**Algorithm 2, moisture penetration**:


<div align="center">


</div>

### 3. Oospore dispersion

Stage 2 of primary infection, i.e. oospore spreading through rain splashing.

### 4. Oospore infection

Stage 3 of primary infection, i.e. activating conditions for a successful oospore infection.

### 5. Incubation

### 6. Sporulation

### 7. Estimation of sporangia density

### 8. Estimation of spore life-span

### 9. Secondary infection
