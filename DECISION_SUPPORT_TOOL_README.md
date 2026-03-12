# Support Decision Tool

## Overview

The support decision tool analyses a spore count dataset (spore trap
measurements) and determines whether the infection model should skip early
primary-infection stages and jump directly to the dispersion or sporulation
stage.  This allows the model to incorporate observational evidence of
sporulation when trap data is available, rather than relying solely on
weather-based predictions.

Two independent conditions are evaluated across the **entire** spore counts
file.  Both can be triggered simultaneously and each generates its own list of
event datetimes that are injected into the infection model.

---

## Module: `src/support_decision_tool.py`

### `fetch_spore_counts(api_query_url, logfile=None)`

Fetches daily spore counts from a remote JSON API and returns them as a
semicolon-delimited CSV string.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_query_url` | str | Full API endpoint URL |
| `logfile` | str, optional | Path to the run logfile |

**Returns** — `str` (CSV) or `None` on failure.

**Expected API response format**

The URL must return a JSON object with a `Mildiou` key containing two parallel
arrays:

| JSON key | Format | Description |
|----------|--------|-------------|
| `Mildiou.date` | `YYYYMMDD_HHMMSS` | Observation timestamps |
| `Mildiou.count` | integer | Spore count per observation |

The function aggregates all observations by calendar day (sum), and produces a
CSV with columns `Date;Counts` (date format `DD.MM.YYYY 00:00`).

**Output CSV example:**
```
Date;Counts
03.04.2025 00:00;9
04.04.2025 00:00;46
05.04.2025 00:00;120
```

When `automated_spore_pull: true` and no manual `spore_counts` file is
specified, the downloaded CSV is saved to `data/input/auto_spore_counts.csv`
before the support decision check runs.

---

### `check_spore_counts(spore_counts_filepath, logfile=None, spore_count_threshold=10, spore_count_lookback_days=3, spore_count_percent_increase=20)`

Reads the full spore counts CSV, aggregates to daily totals, and evaluates two
independent conditions against the entire dataset.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spore_counts_filepath` | str | — | Path to `Date;Counts` CSV file |
| `logfile` | str, optional | `None` | Path to run logfile |
| `spore_count_threshold` | int/float | `10` | Flat daily count threshold (condition 1) |
| `spore_count_lookback_days` | int | `3` | Sliding window size in days (condition 2) |
| `spore_count_percent_increase` | float | `20` | Minimum % increase over the window (condition 2) |

**Input CSV format**

Semicolon-delimited, one row per measurement day:

```
Date;Counts
DD.MM.YYYY HH:MM;integer
```

**Returns** — `dict`:

| Key | Type | Description |
|-----|------|-------------|
| `skip_to_dispersion` | bool | `True` if condition 1 is met anywhere in the dataset |
| `dispersion_datetimes` | list[datetime] | First day of each contiguous surge above the flat threshold |
| `skip_to_sporulation` | bool | `True` if condition 2 is met anywhere in the dataset |
| `sporulation_datetimes` | list[datetime] | Last day of each non-overlapping triggering N-day window |
| `analysis_message` | str | Summary of analysis results |

---

## Decision conditions

Both conditions are evaluated **independently** across the full dataset.  Both
can be `True` at the same time, generating separate injection events for the
model.

### Condition 1 — Flat threshold → skip to oospore dispersion

Any calendar day whose total spore count exceeds `spore_count_threshold` marks
the **onset of a surge**.  The first day of each contiguous block of
above-threshold days is recorded as a `dispersion_datetime`.  Once the count
drops back to or below the threshold, a new surge can begin.

> Example with threshold = 50, counts = [10, 5, 80, 90, 3, 60]:
> → surges start on day 3 (80) and day 6 (60) → two `dispersion_datetimes`

### Condition 2 — Percent increase → skip to sporulation

A sliding window of `spore_count_lookback_days` days is scanned.  If the count
on the last day of a window is at least `spore_count_percent_increase` % higher
than the count on the **first** day (and the first day's count is > 0), the
last day of that window is recorded as a `sporulation_datetime`.  After a
window triggers, the scan advances by the full window size to avoid overlapping
surges contributing multiple events.

> Example with window = 3 days, threshold = 20 %, counts = [2, 5, 10, 1, 2,
> 8]:
> → window [2,5,10]: increase = 400 % ≥ 20 % → triggers on day 3
> → scan jumps to day 4; window [1,2,8]: increase = 700 % → triggers on day 6

---

## Workflow

### Default flow (no spore counts file, or `decision_support_tool_enabled: false`)

The model runs the full primary infection sequence for every datetime:

1. Oospore maturation
2. Oospore germination / soil moisturization
3. Oospore dispersion
4. Oospore infection
5. Incubation
6. Sporulation (weather-based prediction)
7. Sporangia density
8. Spore lifespan
9. Secondary infections

### Enhanced flow (spore counts available and tool enabled)

1. Load weather data.
2. Fetch or read the spore counts file.
3. `check_spore_counts()` evaluates both conditions across the whole dataset.
4. For each `dispersion_datetime`:  the model injects an infection event that
   skips directly to the **oospore dispersion** stage (skipping germination).
5. For each `sporulation_datetime`: the model injects an infection event that
   skips directly to the **sporulation** stage (skipping germination,
   dispersion, infection, and incubation).
6. Normal weather-based events continue in parallel for every datetime.
7. Injected and weather-based events are shown together in the analysis plot
   (injected events rendered in red).

Multiple injection events are possible when the dataset contains repeated
surges across the season.

---

## Configuration (`config/main.yaml`)

```yaml
input_data:
  spore_counts: null                         # path to flat CSV, or null
  decision_support_tool_enabled: true        # enable/disable the tool
  automated_spore_pull: true                 # fetch counts from API if no file given
  spore_counts_api_query: "https://your.api/spores?site=changins"
  spore_count_threshold: 50                  # condition 1: flat daily count threshold
  spore_count_lookback_days: 5               # condition 2: sliding window size [days]
  spore_count_percent_increase: 30           # condition 2: minimum % increase
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `spore_counts` | `null` | Path to a manual spore counts CSV file |
| `decision_support_tool_enabled` | `false` | Enable/disable `check_spore_counts` |
| `automated_spore_pull` | `false` | Fetch from API when no manual file is set |
| `spore_counts_api_query` | `null` | API URL returning Mildiou JSON |
| `spore_count_threshold` | `10` | Flat count threshold for condition 1 |
| `spore_count_lookback_days` | `3` | Sliding window size for condition 2 |
| `spore_count_percent_increase` | `20` | Minimum % increase for condition 2 |

**File resolution priority** (highest to lowest):

1. Explicit `spore_counts` path in config / Streamlit file selector.
2. Automated pull (`automated_spore_pull: true`) → saved to
   `data/input/auto_spore_counts.csv`.
3. No spore data → tool is skipped regardless of `decision_support_tool_enabled`.

---

## Spore counts CSV format

```
Date;Counts
DD.MM.YYYY HH:MM;integer
```

Example:
```
Date;Counts
03.03.2025 00:00;0
07.03.2025 00:00;3
26.03.2025 00:00;2
03.04.2025 00:00;9
04.04.2025 00:00;46
```

Multiple rows with the same calendar date are summed to a single daily total
before the conditions are evaluated.

---

## Logging

Analysis results are appended to the model logfile:

```
Support decision tool enabled. Checking spore counts file for decision support...

Spore count analysis (full dataset, 42 days):
Condition 1 – flat threshold (any day > 50): True → 2 surge(s) detected
Condition 2 – percent increase (30%+ over 5-day window): True → 1 triggering window(s) detected

Spore counts flat threshold exceeded. Model will jump to oospore dispersion stage.
Spore counts percent-increase threshold exceeded. Model will jump to sporulation stage.
```

---

## Error handling

| Scenario | Behaviour |
|----------|-----------|
| File not found | Warning logged; tool skipped; normal model flow |
| Empty file or no valid dates | Warning logged; tool skipped |
| API fetch failure | Warning logged; tool skipped if no fallback file |
| Malformed date strings | Skipped silently per row |

---

## Testing the tool independently

```python
import sys
sys.path.insert(0, 'src')
import support_decision_tool

result = support_decision_tool.check_spore_counts(
    'data/input/auto_spore_counts.csv',
    spore_count_threshold=50,
    spore_count_lookback_days=5,
    spore_count_percent_increase=30,
)
print("Skip to dispersion:", result["skip_to_dispersion"])
print("Dispersion datetimes:", result["dispersion_datetimes"])
print("Skip to sporulation:", result["skip_to_sporulation"])
print("Sporulation datetimes:", result["sporulation_datetimes"])
```

---

## Dependencies

- `pandas` — CSV parsing, groupby aggregation, datetime handling
- `requests` — API fetch in `fetch_spore_counts`
- All standard plasmopy dependencies
