# 🚦 crashlens

**An end-to-end data pipeline and AI-powered analytics dashboard for NYC motor vehicle collisions.**

crashlens ingests live crash data from the [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95) Socrata API, validates and cleans it, loads it into a local [DuckDB](https://duckdb.org/) warehouse, and serves an interactive [Streamlit](https://streamlit.io/) dashboard — including a natural-language **"Ask the Data"** feature powered by the Claude API that converts plain-English questions into SQL.

```
 NYC Open Data API ──▶ ingest (paging, retries, cache)
                          │
                          ▼
                       clean & transform (pandas)
                          │
                          ▼
                       validate (pandera schema)
                          │
                          ▼
                       DuckDB warehouse
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     Streamlit dashboard      "Ask the Data" (Claude → SQL)
```

## Features

- **Resilient ingestion** — pages through the Socrata API with retries, exponential backoff, and a local parquet cache
- **Data quality gates** — a [pandera](https://pandera.readthedocs.io/) schema enforces types, value ranges, NYC geo-bounds, and uniqueness before anything reaches the warehouse
- **Columnar warehouse** — cleaned data lands in DuckDB for fast analytical SQL
- **Interactive dashboard** — trends over time, contributing-factor analysis, and a 20k-point crash map with borough/date filters
- **AI-powered querying** — ask questions like *"Which borough had the most cyclist injuries in 2024?"* and get the SQL, an explanation, and the results (SELECT-only guardrails + read-only connection)
- **Tested & CI'd** — pytest suite covering transforms, validation, and SQL guards; GitHub Actions on every push

## Quickstart

```bash
# 1. Install
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
pip install -e .

# 2. Run the pipeline (use --limit for a quick first run)
python -m crashlens.pipeline --limit 100000

# 3. Launch the dashboard
streamlit run app/dashboard.py
```

### Enable AI querying (optional)

Set an [Anthropic API key](https://platform.claude.com/) before launching:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
streamlit run app/dashboard.py
```

Without a key, the dashboard works normally — the Ask tab just shows setup instructions.

## Project layout

```
crashlens/
├── src/crashlens/
│   ├── config.py      # paths & API endpoints
│   ├── ingest.py      # Socrata API client (paging, retries, caching)
│   ├── transform.py   # cleaning + DuckDB loading
│   ├── validate.py    # pandera data-quality schema
│   ├── ask.py         # natural language → SQL via the Claude API
│   └── pipeline.py    # CLI entrypoint
├── app/dashboard.py   # Streamlit app
├── tests/             # pytest suite
└── .github/workflows/ci.yml
```

## Running tests

```bash
pytest -v
```

## Hosting

- **Project page (Vercel):** `public/index.html` is served as a static site — `vercel.json` disables
  framework detection and points the output at `public/`, so there is no build step.
- **Dashboard (Streamlit Community Cloud):** create an app from this repo with main file
  `app/dashboard.py`. A 100k-row demo warehouse is committed at `data/warehouse/crashlens.duckdb`,
  so the app boots with data on the first run. Add `ANTHROPIC_API_KEY` under
  **Settings → Secrets** to enable "Ask the Data".

## Tech stack

Python · pandas · DuckDB · pandera · Streamlit · Plotly · Anthropic Claude API · pytest · GitHub Actions
