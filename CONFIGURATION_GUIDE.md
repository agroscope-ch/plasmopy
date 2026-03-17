# Configuration Guide: Advanced Features

This guide covers the configuration options for the two advanced features added to Plasmopy:
1. **Spore-Driven Model** — uses spore count observations to inject algorithmic shortcuts into the infection model
2. **Automated Data Pull** — fetches and updates weather and spore count data from external APIs

---

## Secrets Setup

Sensitive values (site coordinates, API keys) are kept out of `config/main.yaml` to avoid
accidental commits.  They live in a gitignored companion file:

```
config/secrets.yaml          ← your local copy (gitignored, never committed)
config/secrets.example.yaml  ← template (committed, safe to share)
```

**First-time setup:**
```bash
cp config/secrets.example.yaml config/secrets.yaml
# then edit config/secrets.yaml with your actual values
```

`secrets.yaml` uses the same structure as `main.yaml`.  At runtime the model merges it on top
of `main.yaml`, so any key set in `secrets.yaml` overrides the corresponding `null` placeholder.

Fields stored in `secrets.yaml`:

```yaml
input_data:
  spore_counts_api_query: "https://your.api/spores?site=changins"
  weather_api_query: "https://my.meteoblue.com/packages/basic-1h_agro-1h?apikey=KEY&lat=46.4&lon=6.2&asl=439&format=json"

site:
  latitude: 46.4
  longitude: 6.2
  elevation: 439.0
  timezone: Europe/Zurich
```

---

## Complete Configuration Example (`config/main.yaml`)

```yaml
hydra:
  output_subdir: null
  run:
    dir: .

# -----------------------------------------------------------------------------
# INPUT DATA
# -----------------------------------------------------------------------------
input_data:
  meteo: data/input/2025_meteo_changins.csv
  spore_counts: null                  # path to flat CSV, or null
  automated_spore_pull: true          # fetch spore counts from API if no file given
  spore_counts_api_query: null        # set in config/secrets.yaml
  automated_weather_pull: false       # fetch weather data from API at startup
  weather_api_query: null             # set in config/secrets.yaml

# -----------------------------------------------------------------------------
# OUTPUT / RUN IDENTIFIER
# -----------------------------------------------------------------------------
output:
  directory: data/output
  run_name: null                      # null = derived from meteo filename

# -----------------------------------------------------------------------------
# SPORE-DRIVEN MODEL
# Algorithmic: spore counts are fed into the model to bypass early stages.
# -----------------------------------------------------------------------------
spore_driven_model:
  enabled: true
  spore_count_threshold: 40           # [counts] any day exceeding this → skip to dispersion
  spore_count_lookback_days: 5        # [days]   look-back window for percent-increase check
  spore_count_percent_increase: 30    # [%]       minimum increase over the window → skip to sporulation

# -----------------------------------------------------------------------------
# RISK HEATMAP (visual only — no algorithmic coupling)
# Colour thresholds for the smartphone heatmap rows.
# -----------------------------------------------------------------------------
risk_heatmap:
  model_thresholds:   [50, 100, 200]  # [°C·h]   Modèle row: green / pink / salmon / red
  mildiou_thresholds: [10,  50,  150] # [counts]  Mildiou row band boundaries

# -----------------------------------------------------------------------------
# SITE PARAMETERS  (set actual values in config/secrets.yaml)
# -----------------------------------------------------------------------------
site:
  latitude: null
  longitude: null
  elevation: null
  timezone: null

# -----------------------------------------------------------------------------
# RUN SETTINGS
# -----------------------------------------------------------------------------
run_settings:
  algorithmic_time_steps: 1
  computational_time_steps: 6
  measurement_time_interval: 10       # minutes between consecutive measurements
  fast_mode: true

# -----------------------------------------------------------------------------
# DATA COLUMN SETTINGS
# -----------------------------------------------------------------------------
data_columns:
  use_columns:
    - 0
    - 1
    - 2
    - 3
    - 4
  rename_columns:
    0: datetime
    1: temperature
    2: humidity
    3: rainfall
    4: leaf_wetness
  format_columns:
    0: '%d.%m.%Y %H:%M'
    1: [-20, 50]
    2: [0, 100]
    3: [0, 200]
    4: [0, 10]

# -----------------------------------------------------------------------------
# OOSPORE MATURATION
# -----------------------------------------------------------------------------
oospore_maturation:
  date: null
  base_temperature: 8.0
  sum_degree_days_threshold: 140.0

# -----------------------------------------------------------------------------
# OOSPORE GERMINATION
# -----------------------------------------------------------------------------
oospore_germination:
  algorithm: 2
  base_temperature: 8
  base_duration: 8
  leaf_wetness_threshold: 10
  relative_humidity_threshold: 80
  moisturization_temperature_threshold: 8.0
  moisturization_rainfall_threshold: 5.0
  moisturization_rainfall_period: 48

# (remaining model parameters as in main.yaml …)
```

---

## Feature: Spore-Driven Model

### What It Does

Analyses the full spore counts dataset and determines whether the infection model should skip
early primary-infection stages and jump directly to the **oospore dispersion** or **sporulation**
stage.  This allows the model to incorporate observational evidence of active sporulation in the
field, rather than relying solely on weather-based predictions.

> This is fundamentally different from the **Risk Heatmap** thresholds (see below).
> The spore-driven model *algorithmically* alters the model flow; the risk heatmap uses spore
> counts only as a *visual* row in the smartphone output — the two are never combined in the
> infection algorithm.

### Configuration

```yaml
# config/main.yaml
spore_driven_model:
  enabled: true
  spore_count_threshold: 40           # condition 1
  spore_count_lookback_days: 5        # condition 2 window
  spore_count_percent_increase: 30    # condition 2 threshold
```

### Activation Criteria

The model injects an algorithmic shortcut when **either** condition is met anywhere in the dataset:

1. **Flat threshold** — any day's total spore count exceeds `spore_count_threshold`
   → shortcut to **oospore dispersion** stage
2. **Percent increase** — the count on the last day of a `spore_count_lookback_days`-day window
   is at least `spore_count_percent_increase` % higher than the first day
   → shortcut to **sporulation** stage

### When to Enable

- You have actual spore count measurements (qPCR, microscopy, …) for the current location/season.
- You want to accelerate model predictions when sporulation is confirmed by observations.

### Example: Enabled with automated pull

```yaml
input_data:
  spore_counts: null
  automated_spore_pull: true
  spore_counts_api_query: null        # set in secrets.yaml

spore_driven_model:
  enabled: true
  spore_count_threshold: 40
  spore_count_lookback_days: 5
  spore_count_percent_increase: 30
```

### Example: Disabled (default)

```yaml
spore_driven_model:
  enabled: false
```

Result: spore counts file (if any) is loaded for visualisation in the heatmap, but the model
runs its normal weather-based flow without algorithmic shortcuts.

---

## Feature: Risk Heatmap Thresholds

### What It Does

Controls the colour categories displayed in the smartphone risk heatmap (`plot_risk_heatmap`).
Three independent rows are shown:

| Row | Source | Algorithmic role |
|-----|--------|-----------------|
| **Modèle** | daily infection strength (°C·h) from the mechanistic model | — |
| **Mildiou** | daily spore counts from the trap | — |
| **RISQUE** | display-only product of the two rows above | visual only |

All thresholds here are **purely visual**; they do not affect the infection model computation.

### Configuration

```yaml
risk_heatmap:
  model_thresholds:   [50, 100, 200]  # lower boundary of pink / salmon / red for Modèle row
  mildiou_thresholds: [10,  50,  150] # lower boundary of pink / salmon / red for Mildiou row
  # Risque thresholds are auto-derived as pair-wise products of the above.
```

---

## Feature: Automated Data Pull (Weather)

### What It Does

Fetches current weather data from a Meteoblue JSON API at model startup and merges it with the
weather input file before the infection model runs.

### Configuration

```yaml
# config/main.yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  automated_weather_pull: false
  weather_api_query: null             # set in config/secrets.yaml

# config/secrets.yaml
input_data:
  weather_api_query: "https://my.meteoblue.com/packages/basic-1h_agro-1h?apikey=KEY&lat=46.4&lon=6.2&asl=439&format=json"
```

### Combined file behaviour

When **both** `meteo` (a flat file) and `automated_weather_pull: true` are set, the model:

1. Copies the flat file to a new file named `{stem}_lat{lat}_lon{lon}.csv` in the same directory.
2. Merges API data into that new combined file.
3. Runs the model against the combined file.

The original flat file is **never modified**.  This ensures flat-file updates (e.g. new seasonal
data) are always picked up on the next run.

### When to Enable

- You have access to a live Meteoblue weather API.
- You want the model to always run against current or forecasted weather data.

### Configuration Parameters

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `automated_weather_pull` | `main.yaml` | `false` | Enable/disable the feature |
| `weather_api_query` | `secrets.yaml` | `null` | Full Meteoblue API URL with coordinates and API key |

> The model validates that the `lat`/`lon`/`asl` parameters in the API URL match the
> `site.latitude`, `site.longitude`, `site.elevation` values in the config.  A mismatch
> (beyond ±0.0001° for coordinates, ±1 m for elevation) causes the run to abort.

### Example Configurations

#### Example 1: Disabled (default)
```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  automated_weather_pull: false
```

#### Example 2: Flat file + API merge (recommended for operational use)
```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  automated_weather_pull: true
  weather_api_query: null   # set in secrets.yaml
```
Creates `data/input/2025_meteo_changins_lat46.4_lon6.2.csv`; original file unchanged.

#### Example 3: API only (no local file)
```yaml
input_data:
  meteo: null
  automated_weather_pull: true
  weather_api_query: null   # set in secrets.yaml
```
Creates `data/input/automated_meteo_lat46.4_lon6.2.csv` automatically.

---

## Common Configuration Scenarios

### Scenario 1: Offline model (no APIs)

```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  spore_counts: null
  automated_spore_pull: false
  automated_weather_pull: false

spore_driven_model:
  enabled: false
```

### Scenario 2: With local spore observations

```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  spore_counts: data/input/2025_qPCR_changins.csv
  automated_spore_pull: false
  automated_weather_pull: false

spore_driven_model:
  enabled: true
  spore_count_threshold: 40
  spore_count_lookback_days: 5
  spore_count_percent_increase: 30
```

### Scenario 3: With live weather updates

```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  spore_counts: null
  automated_spore_pull: false
  automated_weather_pull: true
  weather_api_query: null   # set in secrets.yaml

spore_driven_model:
  enabled: false
```

### Scenario 4: Full monitoring (spore API + live weather)

```yaml
input_data:
  meteo: data/input/2025_meteo_changins.csv
  spore_counts: null
  automated_spore_pull: true
  spore_counts_api_query: null   # set in secrets.yaml
  automated_weather_pull: true
  weather_api_query: null        # set in secrets.yaml

spore_driven_model:
  enabled: true
  spore_count_threshold: 40
  spore_count_lookback_days: 5
  spore_count_percent_increase: 30
```

---

## Troubleshooting

### Feature not working
1. Check the relevant `enabled` / `automated_*` flag is set to `true`.
2. Verify `config/secrets.yaml` exists and contains the required API keys.
3. Check the model logfile for error messages.

### API errors
- Verify the API URL in `secrets.yaml` is correct.
- Ensure the Meteoblue URL includes a valid `apikey` parameter.
- Look for network/connection errors in the logfile.

### Coordinate mismatch error
- The `lat`/`lon`/`asl` in `weather_api_query` must match `site.latitude`, `site.longitude`,
  `site.elevation` in `secrets.yaml`.

### Data not updating
- Confirm `automated_weather_pull: true` and `weather_api_query` is not null.
- Review the logfile for API fetch or merge failures.

---

## Additional Resources

- `DECISION_SUPPORT_TOOL_README.md` — spore count analysis and spore-driven model details
- `AUTOMATED_DATA_PULL_README.md` — API integration and data merging details
- `src/support_decision_tool.py` — Python implementation of spore count analysis
- `src/automated_weather_pull.py` — Python implementation of weather data pull
- `src/plots.py` — all plotting functions (PDF, risk heatmap, infection chains, combined HTML)
