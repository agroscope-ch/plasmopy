# Support Decision Tool Implementation

## Overview
A new support decision tool has been created to enable the infection model to continue from the sporulation stage based on actual spore count observations. This allows the model to skip theoretical prediction stages when real-world evidence indicates that sporulation has already occurred.


## Additional Capability: Automated Spore Pull

If the `spore_counts` file is absent the model can optionally fetch counts from a
remote API.  Set the following in `config/main.yaml`:

```yaml
input_data:
  spore_counts: null
  automated_spore_pull: true
  spore_counts_api_query: "https://your.api/spores?site=changins"
```

When enabled the main program writes the downloaded CSV to
`data/tmp/auto_spore_counts.csv` and then proceeds with its normal analysis.

{
  This behavior is implemented in `src/support_decision_tool.fetch_spore_counts`.
}

## Components Created/Modified

### 1. New File: `src/support_decision_tool.py`
This module contains the core logic for analyzing spore count data.

**Main Function**: `check_spore_counts(spore_counts_filepath, logfile=None)`

**Purpose**: Analyzes the last 3 days of spore count data from a CSV file and determines if conditions warrant continuing from the sporulation stage.

**Parameters**:
- `spore_counts_filepath` (str): Path to CSV file with columns "Date" and "Counts" (semicolon-delimited)
  - Date format: "DD.MM.YYYY HH:MM"
- `logfile` (str, optional): Path to logfile for recording analysis results

**Returns**: Dictionary containing:
```python
{
    "continue_from_sporulation": bool,  # True if conditions are met
    "sporulation_datetime": datetime,   # Last day's datetime for sporulation event
    "last_3_days_counts": list,        # List of 3 daily total counts
    "analysis_message": str            # Detailed analysis results
}
```

**Decision Criteria**: 
The function returns `continue_from_sporulation=True` if **either**:
1. **Any day's total surpasses 10 spores**, OR
2. **At least 20% increase** between the first and last day of the 3-day period

**Example Data Format** (`2025_qPCR_changins.chasselas.csv`):
```
Date;Counts
04.06.2025 00:00;77.41
07.07.2025 00:00;27.3
23.07.2025 00:00;182.93
```

### 2. Modified File: `src/main.py`
**Changes**:
- Added `import support_decision_tool`
- After data loading and processing, calls `support_decision_tool.check_spore_counts()` if a spore counts file is specified in config
- Passes the result to each InfectionEvent object

**Config Integration**:
The spore counts file path is specified in `config/main.yaml`:
```yaml
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: data/input/2025_qPCR_changins.chasselas.csv  # Set to enable support decision
```

Set `spore_counts: null` to disable the feature and run normal model flow.

### 3. Modified File: `src/infection_event.py`
**Changes**:
- Constructor now accepts optional `spore_counts_result` parameter
- Passes this result to `infection_model.run_infection_model()`

### 4. Modified File: `src/infection_model.py`
**Changes**:
- `run_infection_model()` function now accepts optional `spore_counts_result` parameter
- When `continue_from_sporulation=True`:
  - Skips all primary infection stages (oospore germination, dispersion, infection, incubation)
  - Uses the last spore count datetime as the sporulation event datetime
  - Continues normal flow from the sporulation stage onwards
- Variables initialized for skipped stages: `oospore_germination_datetime`, `oospore_dispersion_datetime`, `oospore_infection_datetime` are set to None
- The sporulation stage and all subsequent stages (sporangia density, spore lifespan, secondary infections) proceed normally

## Workflow

### Default Flow (No Spore Counts File)
1. Load meteorological data
2. Process data → determine oospore maturation date
3. Run normal infection model for each datetime:
   - Oospore germination (weather-based detection)
   - Oospore dispersion
   - Oospore infection  
   - Incubation
   - **Sporulation** (predicted from weather)
   - Sporangia density
   - Spore lifespan
   - Secondary infections

### Enhanced Flow (With Spore Counts File)
1. Load meteorological data
2. Check spore counts file
3. If conditions met (spores > 10 OR 20%+ increase):
   - Skip to sporulation stage
   - Use last spore count datetime as sporulation event
4. For each datetime, continue from:
   - **Sporulation** (confirmed by observed spores)
   - Sporangia density
   - Spore lifespan  
   - Secondary infections

## Logical Benefits

1. **Evidence-Based Decision**: Uses real observational data instead of weather-only predictions
2. **Model Acceleration**: Skips unnecessary early-stage predictions when sporulation is confirmed
3. **Hybrid Approach**: Combines observed data (spore counts) with weather-based predictions (secondary infection stages)
4. **Flexibility**: Can be enabled/disabled via configuration without code changes

## Usage Example

In `config/main.yaml`:

```yaml
# Enable support decision tool
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: data/input/2024_qPCR_changins.chasselas.csv

# Or disable it
input_data:
  meteo: data/input/2024_meteo_changins.csv
  spore_counts: null
```

## Testing

The support_decision_tool can be tested independently:

```python
import sys
sys.path.insert(0, 'src')
import support_decision_tool

result = support_decision_tool.check_spore_counts('data/input/2025_qPCR_changins.chasselas.csv')
print(f"Continue from sporulation: {result['continue_from_sporulation']}")
print(f"Sporulation datetime: {result['sporulation_datetime']}")
print(f"Last 3 days counts: {result['last_3_days_counts']}")
```

## Output Files

When using the support decision tool, log entries will include:
- Spore count analysis results
- Decision about skipping to sporulation
- Sporulation stage start datetime  
- All subsequent infection event predictions

These are logged to the standard output file specified in the configuration.

## Requirements

- `pandas`: For CSV parsing and datetime handling
- All existing plasmopy dependencies

## Notes

- The function handles missing or incomplete data gracefully, returning error messages without crashing
- Date parsing expects "DD.MM.YYYY HH:MM" format strictly
- If multiple dates are present in the spore counts file, only the last 3 unique dates are considered
- The sporulation datetime used is the last recorded time for the last day with spore counts
