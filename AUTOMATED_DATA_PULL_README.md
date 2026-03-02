# Automated Weather Data Pull Implementation

## Overview
The automated weather data pull feature enables the infection model to fetch updated weather data from an external API source at startup and merge it with the existing weather data file. Since external scheduling tools (bash/cron) control execution frequency, the pull is performed once per model run.

## Components

### Module: `src/automated_data_pull.py`
This module handles all aspects of automated weather data collection and integration.

**Key Functions**:

#### 1. `fetch_weather_data_from_api(api_query_url, logfile=None)`
Fetches weather data from the specified API query URL.

**Parameters**:
- `api_query_url` (str): The API endpoint/query URL
- `logfile` (str, optional): Path to logfile for logging

**Returns**:
- CSV formatted string of weather data, or None if fetch fails

**Notes**:
- Currently uses mock data for testing/demo
- In production, modify to make actual HTTP requests using `requests.get()`
- Expects API to return CSV data in the same format as existing weather files

#### 2. `merge_weather_data(existing_file_path, new_csv_data, logfile=None)`
Merges new weather data with existing data file while preserving historical values.

**Parameters**:
- `existing_file_path` (str): Path to existing weather data file
- `new_csv_data` (str): CSV formatted string of new weather data
- `logfile` (str, optional): Path to logfile for logging

**Returns**:
- Boolean: True if merge successful, False otherwise

**Behavior**:
- Loads existing data from file
- Parses new data from CSV string
- Updates rows where datetime matches (overwrites with new values)
- Adds new rows for datetimes not present in existing data
- Removes duplicate datetimes
- Sorts by datetime
- Writes merged data back to the same file

**Example**:
```python
csv_data = """datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.2;75;0;0
02.03.2026 09:00;6.1;72;0;0
"""
success = merge_weather_data('data/input/2024_meteo.csv', csv_data, 'logfile.txt')
```

#### 3. `start_periodic_data_pull(meteo_file_path, api_query_url, logfile=None, stop_event=None)`
Starts a background thread to fetch and merge weather data once.

**Parameters**:
- `meteo_file_path` (str): Path to weather data file to update
- `api_query_url` (str): API query URL for data source
- `logfile` (str, optional): Path to logfile for logging
- `stop_event` (threading.Event, optional): Event to signal stop (not actively used for one-shot)

**Returns**:
- `threading.Thread` object (daemon thread), or None if parameters invalid

**Behavior**:
- Validates parameters (api_query_url not None)
- Creates daemon thread that:
  - Fetches new data from API once
  - Merges with existing file
  - Logs results
  - Exits

**Execution Model**:
Since execution frequency is controlled externally (via cron/bash scheduling), this function performs a single fetch/merge at startup. To fetch data at regular intervals, schedule the entire model run via external tools.

**Usage**:
```python
import threading

# External scheduling controls how often this runs
thread = start_periodic_data_pull(
    meteo_file_path='data/input/meteo.csv',
    api_query_url='https://api.example.com/weather?location=changins',
    logfile='run.log'
)

if thread:
    thread.start()
```

#### 4. `_get_mock_weather_data()`
**Internal function** that generates mock weather data for testing/demonstration.

Returns CSV-formatted string with realistic weather data for March 2-3, 2026.

## Configuration

Add these parameters to `config/main.yaml`:

```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: null
  support_decision_tool_enabled: false
  # New parameters:
  automated_data_pull: false                           # Enable/disable feature
  weather_api_query: null                             # API endpoint URL
```

### Parameter Descriptions

- **`automated_data_pull`** (bool, default: `false`)
  - Enable or disable the automated weather data pull feature
  - If `false`, no API pulls occur even if other parameters are set

- **`weather_api_query`** (str, default: `null`)
  - The API endpoint URL to query for weather data
  - Must return CSV data in the same format as existing weather files
  - Example: `"https://api.example.com/weather?location=changins&format=csv"`
  - Required if `automated_data_pull` is `true`

## Workflow

### When Automated Data Pull is Disabled (default)
Model runs normally with static weather data from the configured meteorological file.

### When Automated Data Pull is Enabled

1. **At Startup**:
   - Model checks if `automated_data_pull=true`
   - Validates `weather_api_query` is specified
   - Creates background daemon thread to fetch/merge data
   - Thread starts immediately and performs single operation

2. **Background Operation** (runs once per model execution):
   - Fetches new weather data from API
   - Merges with existing file (updates matching datetimes, preserves history)
   - Logs operation results
   - Thread completes

3. **Model Execution**:
   - Model uses the weather data file after synchronous startup fetch
   - Updated data from API is immediately available for model predictions
   - To refresh data at intervals, re-run the model (schedule via external tools)

4. **Cleanup**:
   - When model run completes, cleanup code signals thread to stop
   - Waits up to 5 seconds for graceful shutdown
   - Closes logfile

## Data Format Requirements

### Input Weather File Format
CSV file with semicolon delimiter and columns:
```
datetime;temperature;humidity;rainfall;leaf_wetness
DD.MM.YYYY HH:MM;value;value;value;value
```

Example:
```
datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.2;75;0;0
02.03.2026 09:00;6.1;72;0;0
02.03.2026 10:00;7.5;68;0;0
```

#### Column Specifications
- **datetime**: Format must be `DD.MM.YYYY HH:MM`
- **temperature**: Temperature in °C (float)
- **humidity**: Relative humidity in % (0-100, float)
- **rainfall**: Rainfall in mm (float)
- **leaf_wetness**: Leaf wetness in hours or droplets (float)

### API Expected Response Format
The API endpoint must return CSV data in the same format as above.

Example for fetching data from `https://api.example.com/weather`:
```csv
datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 14:00;10.2;60;0;0
02.03.2026 15:00;11.5;58;0;0
02.03.2026 16:00;12.1;55;0;0
```

## Implementation in main.py

### Imports
```python
import threading
import automated_data_pull
```

### Initialization (after logfile creation)
```python
data_pull_thread = None
data_pull_stop_event = None
if config.input_data.get("automated_data_pull", False):
    api_query = config.input_data.get("weather_api_query")
    frequency = config.input_data.get("data_pull_frequency_hours", 1)
    
    if api_query is not None and frequency >= 1:
        data_pull_stop_event = threading.Event()
        data_pull_thread = automated_data_pull.start_periodic_data_pull(
            meteo_file_path=config.input_data.meteo,
            api_query_url=api_query,
            frequency_hours=int(frequency),
            logfile=logfile,
            stop_event=data_pull_stop_event,
        )
        if data_pull_thread is not None:
            data_pull_thread.start()
```

### Cleanup (before model completion)
```python
if data_pull_stop_event is not None:
    data_pull_stop_event.set()
    if data_pull_thread is not None and data_pull_thread.is_alive():
        data_pull_thread.join(timeout=5)
```

## Usage Examples

### Example 1: Disable Automated Data Pull (Default)
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_data_pull: false
  weather_api_query: null
  data_pull_frequency_hours: 1
```
Model runs with static data from `2024_meteo_changins.csv`.

### Example 2: Enable with Hourly Updates
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_data_pull: true
  weather_api_query: "https://api.meteo.example.com/data?station=changins&format=csv"
  data_pull_frequency_hours: 1
```
New weather data is fetched every hour and merged with existing file.

### Example 3: Updates Every 6 Hours
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  automated_data_pull: true
  weather_api_query: "https://api.meteo.example.com/station/changins"
  data_pull_frequency_hours: 6
```
Less frequent pulls reduce API load while still maintaining relatively current data.

## Data Merge Behavior

The merge algorithm ensures:

1. **No Data Loss**: Historical values for datetimes not in new API response are preserved
2. **Current Updates**: Datetimes present in new API response are updated with latest values
3. **Chronological Order**: Data remains sorted by datetime after each merge
4. **File Consistency**: Only one weather data file is maintained, updated in-place

### Example Merge Scenario

**Before Merge** (existing file):
```
datetime;temperature;humidity
01.03.2026 12:00;8.5;70
01.03.2026 13:00;9.2;68
02.03.2026 08:00;5.2;75
```

**New API Data**:
```
datetime;temperature;humidity
02.03.2026 08:00;5.3;74
02.03.2026 09:00;6.1;72
```

**After Merge** (updated file):
```
datetime;temperature;humidity
01.03.2026 12:00;8.5;70
01.03.2026 13:00;9.2;68
02.03.2026 08:00;5.3;74
02.03.2026 09:00;6.1;72
```

Note: 
- `01.03.2026 12:00` and `13:00`: Preserved (not in new data)
- `02.03.2026 08:00`: Updated with new values (5.3°C, 74% humidity)
- `02.03.2026 09:00`: Added as new record

## Logging

All automated data pull operations are logged to the model logfile with timestamps:
- When data pull thread starts/stops
- Each API fetch attempt and result
- Each merge operation and record counts
- Any errors or warnings

Example log output:
```
Starting automated data pull thread...
Automated weather data pull started. Frequency: every 1 hour(s)
Pulling weather data from API at 2026-03-02 10:15:30.123456
Successfully fetched weather data from API at 2026-03-02 10:15:31.456789
Successfully merged new weather data into data/input/2024_meteo_changins.csv. Added/Updated 5 records.
```

## Error Handling

The module includes robust error handling:

- **Connection Failures**: Logged but don't stop model execution
- **Invalid CSV Format**: Logged with details, file not updated
- **Missing Parameters**: Logged, data pull not started
- **Column Mismatches**: Attempts to map columns, fails gracefully if impossible

The model continues running even if data pulls fail, using the latest successfully updated weather data.

## Customization for Production APIs

To use with a real weather API, modify `fetch_weather_data_from_api()` function:

**Current (Mock) Implementation**:
```python
def fetch_weather_data_from_api(api_query_url, logfile=None):
    # ... setup code ...
    csv_data = _get_mock_weather_data()  # Mock data
    return csv_data
```

**Production Implementation** (example for OpenWeatherMap or similar):
```python
def fetch_weather_data_from_api(api_query_url, logfile=None):
    # ... setup code ...
    try:
        response = requests.get(api_query_url, timeout=30)
        response.raise_for_status()
        csv_data = response.text  # API returns CSV format
        return csv_data
    except requests.exceptions.RequestException as e:
        # ... error handling ...
```

## Performance Considerations

- **Daemon Thread**: Background thread doesn't prevent model from ending
- **Non-Blocking Updates**: Data file is updated independently from model iteration
- **Memory Efficient**: Only reads/writes to weather data file, doesn't load entire history
- **Thread Safety**: File operations are atomic at the OS level

## Troubleshooting

### "No spore counts file specified. Running normal model flow."
This is expected if `automated_data_pull: false`. Enable it with `true` or provide `weather_api_query`.

### Data not updating
- Check `automated_data_pull: true` is set
- Verify `weather_api_query` is provided and not null
- Ensure `data_pull_frequency_hours >= 1`
- Check model logfile for API fetch errors

### Datetime format errors
- Verify API returns dates in `DD.MM.YYYY HH:MM` format
- Check existing weather file uses same format
- Look for error messages in logfile detailing the mismatch

## Limitations

- Currently uses UTC/configurable timezone; ensure API returns data in same timezone
- File-based merging means updates are only visible after file write completes
- No database backend; for high-frequency updates (< hourly), consider alternative storage
- Mock API included for testing; replace with real API URL for production use
