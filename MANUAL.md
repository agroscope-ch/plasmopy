# Plasmopy v1.0 — Manual

## Input data

### Weather data

A semicolon-delimited CSV file with columns in this exact order:

| # | Variable | Unit | Notes |
|---|----------|------|-------|
| 1 | Datetime | `DD.MM.YYYY HH:MM` | local timezone |
| 2 | Temperature | °C | average per interval |
| 3 | Relative humidity | % | 0–100 |
| 4 | Rainfall intensity | mm/h | |
| 5 | Leaf wetness | min | per measurement interval |

Example data is available in `data/input/`. Weather data for Switzerland is available at [Agrometeo](https://www.agrometeo.ch/meteorologie).

Update `measurement_time_interval`, `computational_time_steps`, and `algorithmic_time_steps` in `config/main.yaml` to match your data resolution.

> **Example:** Data sampled every 10 min → `measurement_time_interval: 10`. With `computational_time_steps: 6`, infection events are launched every 60 min. With `algorithmic_time_steps: 1`, internal loops run at full 10-min resolution; set to 6 to run at hourly resolution (faster but less precise).

### Spore counts data (optional)

A semicolon-delimited CSV with two columns:

| # | Variable | Format |
|---|----------|--------|
| 1 | Date | `DD.MM.YYYY HH:MM` |
| 2 | Counts | integer |

Multiple rows for the same calendar day are summed to a daily total. Only data within the current weather data date range is used (see [Spore-Driven Model](#spore-driven-model)).

---

## Infection model

The model simulates the *Plasmopara viticola* life cycle through sequential stages:

1. **Oospore maturation** — cumulative degree-days above base temperature reach a threshold (or a date is set manually).
2. **Germination / soil moisturization** — triggered by humidity, temperature, and rainfall conditions.
3. **Oospore dispersion** — rain splash after germination, subject to a rainfall threshold and latency.
4. **Primary infection** — leaf wetness and degree-hour accumulation complete the infection.
5. **Incubation** — duration computed from mean temperature.
6. **Sporulation** — triggered by humidity, temperature, and darkness conditions.
7. **Sporangia density** — calculated from temperature and latency.
8. **Spore lifespan** — estimated from vapour pressure.
9. **Secondary infections** — driven by spore availability, temperature, and leaf wetness.

When the spore-driven model is enabled, observational spore data can bypass stages 2–5 (skip directly to dispersion) or stages 2–8 (skip directly to sporulation). See [Spore-Driven Model](#spore-driven-model).

---

## Output files

All outputs are written to `data/output/{run_name}/`:

| File | Description |
|------|-------------|
| `*.log` | Run log: data processing, model parameters, errors |
| `*.processed.csv` | Processed and quality-filtered weather data |
| `*.events_log.csv` | Text summary of each infection event |
| `*.events_table.csv` | Tabular infection event data (datetimes, densities) |
| `*.infection_datetimes.csv` | Infection datetimes for downstream use |
| `*.analysis.pdf` | PDF of the full infection chain plot |
| `*.html` | Mobile-optimised combined view (primary output) |
| `*.analysis.html` | Standalone interactive infection chain plot |
| `*.overview.html` | Standalone spore counts + infection overview |
| `*.heatmap.html` | Standalone risk heatmap |

The **combined HTML** (`*.html`) is the primary mobile output. It contains:
- **Aide à la décision** — smartphone risk heatmap with three rows: *Modèle* (infection strength), *Mildiou* (spore counts), *RISQUE* (visual product of the two);
- **Modèle détaillé** — full infection chain analysis (toggled by a button).

Future forecast dates (beyond today) are shown with reduced opacity in the heatmap and analysis plots.

---

## Configuration

### Secrets setup

Sensitive values (site coordinates, API keys) are stored in `config/secrets.yaml`, which is gitignored and never committed.

```bash
cp config/secrets.example.yaml config/secrets.yaml
# edit config/secrets.yaml with your actual values
```

`secrets.yaml` is merged on top of `main.yaml` at runtime. It follows the same structure:

```yaml
input_data:
  spore_counts_api_query: "https://your.api/spores.json"
  weather_api_query: "https://my.meteoblue.com/packages/basic-1h_agro-1h?apikey=KEY&lat=46.4&lon=6.2&asl=439&format=json"

site:
  latitude: 46.4
  longitude: 6.2
  elevation: 439.0
  timezone: Europe/Zurich
```

### Output naming

```yaml
output:
  directory: data/output   # base output directory
  run_name: my_run         # all output files named my_run.*; null = derive from meteo filename
```

`run_name` may contain dots (e.g. `test.changins.2026`). All dots are treated as part of the name, not as file extensions — output files will be named `test.changins.2026.log`, `test.changins.2026.html`, etc.

### Key parameters reference

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `input_data.meteo` | `main.yaml` | — | Path to weather CSV; `null` for API-only |
| `input_data.spore_counts` | `main.yaml` | `null` | Path to spore counts CSV; `null` for API or none |
| `input_data.automated_weather_pull` | `main.yaml` | `false` | Fetch weather from API at startup |
| `input_data.automated_spore_pull` | `main.yaml` | `false` | Fetch spore counts from API |
| `run_settings.measurement_time_interval` | `main.yaml` | `10` | Minutes between data rows |
| `oospore_maturation.date` | `main.yaml` | `null` | Pre-set maturation date; `null` = compute |
| `output.run_name` | `main.yaml` | `null` | Custom name for output files and folder |

All model biological parameters (germination, dispersion, infection thresholds, etc.) are documented inline in `config/main.yaml`.

---

## Automated Data Pull

Both weather and spore count data can be fetched automatically from external APIs at model startup.

### Weather API

Fetches from a Meteoblue-compatible JSON endpoint (`data_1h` block with `time`, `temperature`, `relativehumidity`, `precipitation`, `leafwetnessindex`). The fetched data is merged into the local weather file — existing rows are updated, new rows appended, file is sorted chronologically.

**Configuration:**
```yaml
input_data:
  automated_weather_pull: true
  weather_api_query: null   # set in secrets.yaml
```

**File behaviour:**
- `meteo: null` + API → creates `data/input/automated_meteo_lat{lat}_lon{lon}.csv`
- `meteo: path` + API → copies flat file to `{stem}_lat{lat}_lon{lon}.csv`, merges API data into the copy; original file is never modified

If the API call fails, the model continues with whatever data is already in the file.

### Spore counts API

Fetches from a JSON endpoint returning a `Mildiou` object with `date` (`YYYYMMDD_HHMMSS`) and `count` arrays. Daily totals are aggregated and saved to `data/input/automated_spore_{station_id}.csv` (where `station_id` is derived from the URL path stem).

**Configuration:**
```yaml
input_data:
  automated_spore_pull: true
  spore_counts_api_query: null   # set in secrets.yaml
```

---

## Spore-Driven Model

When enabled, the model analyses the spore counts file and injects algorithmic shortcuts into the infection model when sporulation is confirmed by trap observations, rather than relying solely on weather predictions.

> This is distinct from the **Risk Heatmap** thresholds: the spore-driven model algorithmically alters the model flow; the heatmap uses spore counts only for visual display and never affects the infection algorithm.

### Season window

Only spore count records within the current **weather data date range** are considered. Records outside this window (e.g. previous season data in the same file) are automatically excluded and logged.

### Conditions

Both conditions are evaluated independently. Either or both can trigger simultaneously.

**Condition 1 — Flat threshold → skip to oospore dispersion**

Any day whose total count exceeds `spore_count_threshold` starts a surge. The first day of each contiguous surge above the threshold is recorded as a dispersion event.

**Condition 2 — Percent increase → skip to sporulation**

Within any `spore_count_lookback_days`-day window, if the last day's count is at least `spore_count_percent_increase` % higher than the first day's (and first day > 0), the last day is recorded as a sporulation event. The scan advances by the full window after each trigger to avoid overlapping surges.

**In the analysis plots:** spore-shortcut events are shown in red; normal weather-based events in black.

### Configuration

```yaml
spore_driven_model:
  enabled: true
  spore_count_threshold: 40          # condition 1: flat daily count
  spore_count_lookback_days: 5       # condition 2: window size [days]
  spore_count_percent_increase: 30   # condition 2: minimum % increase
```

---

## Risk Heatmap

The heatmap (`*.heatmap.html`, also the primary view in `*.combined.html`) shows three independent rows:

| Row | Source | Role |
|-----|--------|------|
| **Modèle** | Daily infection strength [°C·h] | From the mechanistic model |
| **Mildiou** | Daily spore counts | From trap data |
| **RISQUE** | Product of the two above | Visual only — not used in the model |

Colour thresholds for each row are configurable:

```yaml
risk_heatmap:
  model_thresholds:   [50, 100, 200]   # [°C·h]   lower bounds for pink / salmon / red
  mildiou_thresholds: [20,  50,  100]  # [counts]  lower bounds for pink / salmon / red
```

Grey tiles indicate missing spore data. Transparent tiles indicate forecast (future) dates.
