# Configuration Guide: Advanced Features

This guide covers the configuration options for two advanced features added to Plasmopy:
1. **Support Decision Tool** - Uses spore count observations to trigger sporulation stage
2. **Automated Data Pull** - Periodically fetches and updates weather data from API

## Complete Configuration Example

Here's a complete `config/main.yaml` file showing all available options:

```yaml
# ============================================================================
# PLASMOPY MODEL CONFIGURATION
# ============================================================================

# Algorithmic and computational parameters
algorithmic_time_steps: 1
computational_time_steps: 6
elevation: 439.0
fast_mode: true

# Column format definitions
format_columns:
  0: '%d.%m.%Y %H:%M'  # datetime format
  1:
  - -20     # temperature min
  - 50      # temperature max
  2:
  - 0       # humidity min
  - 100     # humidity max
  3:
  - 0       # rainfall min
  - 200     # rainfall max
  4:
  - 0       # leaf_wetness min
  - 10      # leaf_wetness max

# Hydra configuration
hydra:
  output_subdir: null
  run:
    dir: .

# ============================================================================
# OUTPUT / RUN IDENTIFIER (optional)
# ---------------------------------------------------------------------------
# You may specify a name for this simulation.  If provided the name is used
# as the prefix for all result files and the subdirectory created under the
# output directory.  When left null the software falls back to the stem of the
# meteorological input filename.  This is useful when no local meteo file is
# available (e.g. automatic data pulls) or when running multiple experiments
# using the same input data.
output:
  directory: data/output   # base results directory (can be changed)
  run_name: null           # custom name for this run

# ============================================================================
# INPUT DATA CONFIGURATION - ADVANCED FEATURES
# ============================================================================
input_data:
  # Main meteorological input file (required)
  meteo: data/input/2024_meteo_changins.csv
  
  # Spore counts file for support decision tool (optional)
  spore_counts: null
  
  # FEATURE 1: Support Decision Tool
  # Enables conditional model flow based on observed spore counts
  decision_support_tool_enabled: false
  # Set to true to use spore counts to trigger sporulation stage
  # Requires: spore_counts file must be specified above
  # Effect: If last 3 days show >10 total spores OR 20%+ increase,
  #         model skips to sporulation stage instead of gradual build-up
  
  # FEATURE 2: Automated Data Pull (weather)
  # Background thread periodically fetches and updates weather data
  automated_weather_pull: false
  # Set to true to enable automatic weather data fetching from API
  
  # API endpoint URL for weather data (required if automated_weather_pull=true)
  weather_api_query: null
  # Example: "https://api.meteo.example.com/data?station=changins&format=csv"
  # Mock API included for testing/demo purposes
  
  # FEATURE 3: Automated Spore Counts Pull
  # If no local spore_counts file is provided the model can pull
  # counts from an online API before running support decision analysis.
  automated_spore_pull: false
  # API endpoint URL returning semicolon-separated CSV with Date;Counts
  spore_counts_api_query: null
  # Example: "https://my.domain/sporecounts?site=changins&format=csv"
  # Minimum value: 1
  # Common values: 1 (hourly), 6 (6-hourly), 24 (daily)

# ============================================================================
# LOCATION AND MEASUREMENT PARAMETERS
# ============================================================================
latitude: 46.4
longitude: 6.2
measurement_time_interval: 10  # minutes between measurements

# ============================================================================
# MOISTURE AND INFECTION THRESHOLDS
# ============================================================================
moisturization_rainfall_period: 48          # hours
moisturization_rainfall_threshold: 5.0      # mm
moisturization_temperature_threshold: 8.0   # °C

oospore_dispersion_latency: 6.0             # hours
oospore_dispersion_rainfall_threshold: 3.0  # mm

oospore_germination_algorithm: 2
oospore_germination_base_duration: 8        # hours
oospore_germination_base_temperature: 8.0   # °C
oospore_germination_leaf_wetness_threshold: 10
oospore_germination_relative_humidity_threshold: 80  # %

oospore_infection_base_temperature: 8.0     # °C
oospore_infection_leaf_wetness_latency: 6.0 # hours
oospore_infection_sum_degree_hours_threshold: 50.0

# ============================================================================
# OOSPORE MATURATION
# ============================================================================
oospore_maturation_base_temperature: 8.0    # °C
oospore_maturation_date: null
# Set to null to compute automatically from degree days
# Set to specific date like "15.04.2024" to use fixed date
oospore_maturation_sum_degree_days_threshold: 140.0

# ============================================================================
# COLUMN NAME MAPPING
# ============================================================================
rename_columns:
  0: datetime
  1: temperature
  2: humidity
  3: rainfall
  4: leaf_wetness

# ============================================================================
# ATMOSPHERIC PARAMETERS
# ============================================================================
saturation_vapor_pressure: null  # Calculate from other parameters if null

# ============================================================================
# SECONDARY INFECTION PARAMETERS
# ============================================================================
secondary_infection_leaf_wetness_latency: 60.0  # hours
secondary_infection_max_temperature: 29.0       # °C
secondary_infection_min_temperature: 3.0        # °C
secondary_infection_sum_degree_hours_threshold: 50.0

# ============================================================================
# SPORANGIA PARAMETERS
# ============================================================================
sporangia_latency: 4.0                    # hours
sporangia_max_density: 300000.0           # per cm²
sporangia_max_temperature: 17.5           # °C
sporangia_min_temperature: 11.0           # °C

# ============================================================================
# SPORE LIFESPAN
# ============================================================================
spore_lifespan_constant: 11.35            # days

# ============================================================================
# SPORULATION PARAMETERS
# ============================================================================
sporulation_leaf_wetness_threshold: 0
sporulation_min_darkness_hours: 4.0       # hours
sporulation_min_humidity: 92.0            # %
sporulation_min_temperature: 12.0         # °C

# ============================================================================
# TIMEZONE
# ============================================================================
timezone: Europe/Zurich

# ============================================================================
# COLUMNS TO USE FROM INPUT DATA
# ============================================================================
use_columns:
- 0  # datetime
- 1  # temperature
- 2  # humidity
- 3  # rainfall
- 4  # leaf_wetness
```

## Feature: Support Decision Tool

### What It Does
Analyzes the last 3 days of observed spore counts and determines if the model should skip the gradual infection build-up and jump directly to the sporulation stage.

### Configuration
```yaml
input_data:
  spore_counts: data/input/2024_qPCR_changins.chasselas.csv
  decision_support_tool_enabled: false
```

### When to Enable
- You have actual spore count measurements for the location/season
- You want to accelerate model predictions when sporulation is confirmed
- You want to skip weather-based prediction stages and use observed evidence

### Activation Criteria
The model continues from sporulation stage when **either**:
1. **Spore Count > 10**: Any day's total surpasses 10 spores, OR
2. **20% Increase**: At least 20% increase from first to last day over 3 days

### Example: Enabled
```yaml
input_data:
  spore_counts: data/input/2025_qPCR_changins.chasselas.csv
  decision_support_tool_enabled: true
```
Result: Model checks spore counts each run and may skip to sporulation stage.

### Example: Disabled (Default)
```yaml
input_data:
  spore_counts: data/input/2025_qPCR_changins.chasselas.csv
  decision_support_tool_enabled: false
```
Result: Spore counts file is ignored; model runs normal flow even if file exists.

## Feature: Automated Data Pull

### What It Does
Runs a background thread that periodically fetches fresh weather data from an API and merges it with the existing weather data file. This allows the model to work with continuously updated data.

### Configuration
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_weather_pull: false
  weather_api_query: null
```

### When to Enable
- You have access to a live weather data API
- You want the model to use current/forecasted weather data
- You need continuous data updates during long model runs
- You want to preserve historical data while adding new observations

### Configuration Parameters

#### `automated_weather_pull` (boolean)
- **Default**: `false`
- **true**: Enables automatic data pulls at startup
- **false**: Disables feature; API is not queried

#### `weather_api_query` (string)
- **Default**: `null`
- **Required if**: `automated_weather_pull=true`
- **Value**: Full URL to API endpoint that returns CSV weather data
- **Example**: `"https://api.meteo.example.com/station?id=changins&format=csv"`
- **Mock URL** (for testing): Leave as null or empty string; uses built-in mock data
- **Execution**: Data is fetched and merged once during startup. To fetch at regular intervals, schedule the model itself via cron/task scheduler.

### Example Configurations

*Note: when automated data pull is enabled the model will parse the `lat`, `lon` (and `asl` if present) parameters from the `weather_api_query` URL and compare them to the `latitude`, `longitude` and `elevation` values in the config. A mismatch (beyond a small tolerance of ~0.0001° for coords and 1 m for elevation) will cause the run to abort with an error message.*

#### Example 1: Disabled (Default - No Auto Updates)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_weather_pull: false
  weather_api_query: null
```
- Uses static weather file
- No background API calls
- No automatic updates

#### Example 2: API Updates (Scheduled via Bash/Cron)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_weather_pull: true
  weather_api_query: "https://api.agro.example.com/changins/weather.csv"
```
- Fetches new data during startup
- Merges with existing file
- Frequency controlled externally via cron/scheduler

#### Example 3: No Local Meteo File
```yaml
input_data:
  meteo: null
  automated_weather_pull: true
  weather_api_query: "https://api.meteo.example.com/station/changins"
```
- Creates placeholder file automatically
- Fetches data during startup
- Requires valid API query

#### Example 4: Demo/Testing (Uses Mock Data)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_weather_pull: true
  weather_api_query: "mock"  # Any non-null value triggers mock data
```
- Uses built-in mock weather data
- No external API dependency
- Useful for testing/demo without API access

### Data Format Requirements

#### Input Weather File
CSV format with semicolon delimiter:
```
datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.2;75;0;0
02.03.2026 09:00;6.1;72;0;0
```

#### API Response Format
Same as input weather file format.

Point your API URL to return data exactly like the input files.

### Data Merge Behavior

**Preserved**: Historical datetimes not in new API response
**Updated**: Datetimes present in new API response  
**Added**: New datetimes from API response
**Result**: Single file with complete history + latest data

### Logging

All operations logged to model logfile with timestamps:
- Thread start/stop
- API fetch attempts and results  
- Merge operations (record counts)
- Errors and warnings

### Combining Both Features

You can enable both features simultaneously:

```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: data/input/2024_qPCR_changins.chasselas.csv
  decision_support_tool_enabled: true
  automated_weather_pull: true
  weather_api_query: "https://api.meteo.example.com/changins"
```

This configuration:
1. Automatically fetches updated weather data every hour
2. Checks spore counts to conditionally skip to sporulation
3. Merges new weather data while preserving history
4. Uses both observed spores and updated weather for predictions

## Common Configuration Scenarios

### Scenario 1: Offline Model (No APIs)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: null
  decision_support_tool_enabled: false
  automated_weather_pull: false
  weather_api_query: null
```

### Scenario 2: With Spore Observations
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: data/input/2024_qPCR_changins.csv
  decision_support_tool_enabled: true
  automated_weather_pull: false
```

### Scenario 3: With Live Weather Updates
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: null
  decision_support_tool_enabled: false
  automated_weather_pull: true
  weather_api_query: "https://api.meteo.example.com/changins"
```

### Scenario 4: Full Monitoring (Spores + Live Weather)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: data/input/2024_qPCR_changins.csv
  decision_support_tool_enabled: true
  automated_weather_pull: true
  weather_api_query: "https://api.meteo.example.com/changins"
```

## Troubleshooting

### Feature Not Working
1. Check if parameter is set to `true`
2. Verify required parameters are provided and not `null`
3. Check model logfile for error messages

### API Errors
- Verify API URL is correct
- Check API response format matches weather file format
- Look for network/connection errors in logfile

### Data Not Updating
- Verify `automated_weather_pull: true`
- Confirm `weather_api_query` is not null
- Review logfile for API fetch failures

## Additional Resources

For detailed technical information:
- See `SUPPORT_DECISION_TOOL_README.md` for spore count analysis details
- See `AUTOMATED_DATA_PULL_README.md` for API integration and data merging details
- Review `src/support_decision_tool.py` for Python implementation
- Review `src/automated_weather_pull.py` for data pull implementation
