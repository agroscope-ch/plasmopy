# Automated Weather Data Pull

## Overview

The automated weather data pull feature fetches current weather data from an
external API at model startup and merges it with the weather data file before
the infection model runs.  The pull is **synchronous and happens once per model
execution**; repeat scheduling is handled by external tools (cron, bash scripts,
the Streamlit app).

---

## Module: `src/automated_weather_pull.py`

### `fetch_weather_data_from_api(api_query_url, logfile=None)`

Fetches weather data from a Meteoblue-compatible JSON API and returns it as a
semicolon-delimited CSV string ready for merging.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_query_url` | str | Full API endpoint URL |
| `logfile` | str, optional | Path to the run logfile |

**Returns** — `str` (CSV data) or `None` on failure.

**Expected API response format**

The URL must return a JSON object containing a `data_1h` key with parallel
arrays:

| JSON key | Maps to CSV column |
|----------|--------------------|
| `time` | `datetime` (`DD.MM.YYYY HH:MM`) |
| `temperature` | `temperature` |
| `relativehumidity` | `humidity` |
| `precipitation` | `rainfall` |
| `leafwetnessindex` | `leaf_wetness` |

Example Meteoblue URL (basic-1h + agro-1h package):
```
https://my.meteoblue.com/packages/basic-1h_agro-1h?apikey=KEY&lat=46.4&lon=6.2&asl=439&format=json
```

If the API response is missing the `data_1h` block, the function falls back to
returning built-in mock data and logs a warning.  This allows model development
and testing without an active API subscription.

---

### `merge_weather_data(existing_file_path, new_csv_data, logfile=None)`

Merges newly fetched data into the existing weather file while preserving all
historical records.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `existing_file_path` | str | Path to the current weather CSV |
| `new_csv_data` | str | CSV string returned by `fetch_weather_data_from_api` |
| `logfile` | str, optional | Path to the run logfile |

**Returns** — `bool`: `True` on success, `False` on failure.

**Merge rules**

1. If the target file does not exist or is empty, the fetched data is written
   directly.
2. Rows whose `datetime` already exists in the file are **updated** with the
   new values.
3. Rows with new datetimes are **appended**.
4. The result is sorted chronologically and written back to the same file.
5. Column mismatches are flagged; if the column count matches the order is
   re-mapped, otherwise the merge is aborted.

**Example merge**

*Before merge (existing file):*
```
datetime;temperature;humidity;rainfall;leaf_wetness
01.03.2026 12:00;8.5;70;0;0
01.03.2026 13:00;9.2;68;0;0
02.03.2026 08:00;5.2;75;0;0
```

*New API data:*
```
datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.3;74;0;0
02.03.2026 09:00;6.1;72;0;0
```

*After merge (updated file):*
```
datetime;temperature;humidity;rainfall;leaf_wetness
01.03.2026 12:00;8.5;70;0;0   ← preserved (not in new data)
01.03.2026 13:00;9.2;68;0;0   ← preserved
02.03.2026 08:00;5.3;74;0;0   ← updated
02.03.2026 09:00;6.1;72;0;0   ← new record appended
```

---

### `start_periodic_data_pull(meteo_file_path, api_query_url, logfile=None, stop_event=None)`

Creates a daemon background thread that performs a single fetch-and-merge
operation.  The thread is used to allow the rest of the model startup sequence
to continue in parallel with the API call on slow connections.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `meteo_file_path` | str | Path to the weather file to update |
| `api_query_url` | str | API endpoint URL |
| `logfile` | str, optional | Path to the run logfile |
| `stop_event` | `threading.Event`, optional | Signal for graceful shutdown |

**Returns** — `threading.Thread` or `None` if `api_query_url` is missing.

---

## Configuration (`config/main.yaml`)

```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv   # leave null to use automated pull only
  automated_weather_pull: false                  # set true to enable
  weather_api_query: null                     # Meteoblue API URL
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `automated_weather_pull` | bool | `false` | Enable/disable the feature |
| `weather_api_query` | str | `null` | Full Meteoblue API URL including coordinates and API key |

> **Note:** `meteo` can be left `null` when `automated_weather_pull: true`.  The
> model will create `data/input/automated_meteo.csv` as a placeholder and
> populate it from the API before running.

---

## Workflow

### Disabled (default)

The model reads the static file specified in `input_data.meteo` and runs
normally.

### Enabled

1. **File resolution** — if `input_data.meteo` is null, the model uses
   `data/input/automated_meteo.csv`, creating an empty placeholder if
   necessary.
2. **Synchronous pre-run fetch** — `fetch_weather_data_from_api()` and
   `merge_weather_data()` are called directly and complete before the model
   loads any data.  This ensures the input file is current when `load_data`
   runs.
3. **Background thread** — `start_periodic_data_pull()` is also started as a
   daemon thread to handle any additional in-run updates on slow connections.
4. **Model execution** — the infection model runs against the now-updated
   weather file.
5. **Cleanup** — at model end, `stop_event.set()` is called and the thread is
   joined with a 5-second timeout.

---

## Data format

### Weather CSV (file and API output)

Semicolon-delimited, one row per measurement interval:

```
datetime;temperature;humidity;rainfall;leaf_wetness
DD.MM.YYYY HH:MM;°C;%;mm;min
```

Example:
```
datetime;temperature;humidity;rainfall;leaf_wetness
02.03.2026 08:00;5.2;75;0;0
02.03.2026 09:00;6.1;72;0;0
```

Column specifications:

| Column | Unit | Notes |
|--------|------|-------|
| `datetime` | — | `DD.MM.YYYY HH:MM` |
| `temperature` | °C | float |
| `humidity` | % (0–100) | float |
| `rainfall` | mm | float |
| `leaf_wetness` | min per interval | float |

---

## Logging

Operations are appended to the model logfile:

```
Starting automated data pull thread...
Automated weather data pull started (runs once per model execution).
Pulling weather data from API at 2026-03-03 10:15:30
Fetched 48 rows  |  01.03.2026 00:00  →  02.03.2026 23:00
Successfully fetched weather data from API at 2026-03-03 10:15:31
Successfully merged new weather data into data/input/automated_meteo.csv. Added/Updated 48 records.
Weather data updated successfully at 2026-03-03 10:15:31
```

---

## Error handling

| Scenario | Behaviour |
|----------|-----------|
| Network/HTTP error | Logged; model continues with existing file |
| JSON missing `data_1h` | Warning logged; mock data returned as fallback |
| Column mismatch (same count) | Columns re-mapped to match existing file |
| Column mismatch (different count) | Merge aborted; error logged |
| File missing | New file created from fetched data |
| Empty file | Replaced with fetched data |

The model always continues even if data pull fails; it uses whatever data is
already in the weather file.

---

## Troubleshooting

**Weather file not updating**
- Check `automated_weather_pull: true` is set in the config.
- Verify `weather_api_query` is a valid Meteoblue URL with correct coordinates
  and API key.
- Inspect the model logfile for API fetch errors.

**`data_1h` block missing warning**
- The API URL does not point to a Meteoblue basic-1h or agro-1h package.
- Mock data will be used as fallback.

**Datetime format errors during merge**
- Verify the API returns timestamps that parse correctly to `DD.MM.YYYY HH:MM`.
- Check the existing weather file uses the same format.
