# KALYX: Reach Infinity

**Turn Earth observation data into evidence of environmental change.**

KALYX is a full-stack web application for investigating how the Earth is changing. A user picks an environmental variable and a place (a point or a drawn area), brings in data, and KALYX builds the time series, estimates the rate of change, tests whether the trend is statistically significant, maps where the change differs inside the area, and writes a PDF report.

Built for the NASA Space Apps Challenge 2026, **Be an Earth System Trend Detective!**

> **Data status.** The built-in `demo` source is a seeded **simulation**. It is labelled as simulated in every API response, on screen and in the PDF, and it is not NASA data. For real results, use a CSV exported from NASA Giovanni or AppEEARS, or the live NASA connectors. The AppEEARS, GES DISC and CMR connectors and the NASA GIBS layer settings follow public documentation but **have not been run against the live services** in development. See [Live NASA connectors](#live-nasa-connectors) and [Limitations](#limitations).

---

## Contents

1. [What it answers](#what-it-answers)
2. [Features](#features)
3. [How a run works](#how-a-run-works)
4. [How the statistics work](#how-the-statistics-work)
5. [Architecture](#architecture)
6. [Project structure](#project-structure)
7. [Getting started](#getting-started)
8. [Configuration](#configuration)
9. [Using real NASA data](#using-real-nasa-data)
10. [Live NASA connectors](#live-nasa-connectors)
11. [API reference](#api-reference)
12. [Frontend guide](#frontend-guide)
13. [Media assets](#media-assets)
14. [Testing](#testing)
15. [Deployment notes](#deployment-notes)
16. [Troubleshooting](#troubleshooting)
17. [Scientific safeguards](#scientific-safeguards)
18. [Limitations](#limitations)
19. [Roadmap](#roadmap)
20. [Data sources and credits](#data-sources-and-credits)
21. [AI assistance disclosure](#ai-assistance-disclosure)

---

## What it answers

| Question | How KALYX answers it |
|---|---|
| What is changing? | A catalogue of eight Earth-system variables, plus a live NASA CMR dataset search |
| Where? | A clicked point or a drawn polygon on a NASA GIBS satellite map, and a per-cell trend map |
| How is it changing? | Increasing, decreasing, or not significant |
| How much? | Ordinary least squares and Sen's slope, in units per decade |
| Is it significant? | Mann-Kendall and seasonal Mann-Kendall tests, an autocorrelation adjustment, and false-discovery control across map cells |

## Features

**Discover**
- Variable catalogue with category filters. Each card shows the NASA source product, spatial and temporal resolution, units and coverage: GPM IMERG precipitation, MODIS land surface temperature and NDVI, MERRA-2 soil wetness and runoff, OMI ozone, sea surface temperature, and GLDAS evapotranspiration.
- Dataset search against NASA Earthdata CMR (title, short name, version, provider, period, DOI).

**Locate**
- Leaflet map with NASA GIBS imagery: MODIS true colour, MODIS land surface temperature (day), and Blue Marble. Click to set a point.
- **Polygon drawing:** click corners, finish, clear. Areas can be up to 20 degrees across.
- Preset regions, including the Subarnarekha basin, and manual latitude and longitude.

**Bring in data**
- **Simulated demo** (point or area), clearly labelled.
- **Imported CSV** with a **column picker**: detected date, value and quality columns, scale factor, offset, fill value to drop, and quality-flag cutoff, plus a data preview. Metadata lines above the header (Giovanni style) are skipped.
- **NASA AppEEARS** live point fetch for MODIS land surface temperature and NDVI.
- **NASA GES DISC** live gridded fetch for GPM IMERG precipitation, MERRA-2 soil wetness and runoff, and GLDAS evapotranspiration.
- Background jobs with a progress bar and an on-disk cache.

**Process**
- Quality-flag, fill-value and scale handling, with a data-quality summary (valid rows and what was dropped).
- **Monthly aggregation** of 8-day, 16-day or daily data: mean, sum, or none. The aggregation is recorded.
- **Area averaging** over a drawn polygon with cos(latitude) weights, ignoring missing cells.

**Analyse**
- Linear regression with a 95% confidence interval, Sen's slope, Mann-Kendall with a lag-1 autocorrelation adjustment, and the **seasonal Mann-Kendall** test. You choose which test decides the verdict; both are reported.
- Optional seasonal-cycle removal (anomalies).
- **Pixel trend maps:** every cell inside the area is tested separately and corrected with Benjamini-Hochberg. Cells are drawn on the satellite map. Opposite trends inside one area are flagged.
- A plain-language verdict: significant increasing or decreasing, not significant, or insufficient data.

**Report and export**
- **PDF report:** setup, finding, time series, seasonal cycle, trend map, limitations, and references.
- Copy the time series as CSV, or the analysis metadata as JSON. Print from the browser.

**Learn**
- A long-form guide with 14 collapsible topics: trend tests, reading the verdict, seasonality, autocorrelation, false discoveries, point versus area versus pixel analysis, the NASA datasets, data quality, resolution, what significance does not mean, a step-by-step method, a glossary and FAQs.

**Design**
- Cinematic landing page with image or video holders, and a compact mission-control dashboard. Obsidian-black with cyan accents; Barlow Condensed, Inter and IBM Plex Mono. Responsive from phone to desktop, visible keyboard focus, reduced-motion support.

## How a run works

```
Choose variable + location (point or polygon) + period + options
        |
        v
Data source
   |- demo:      seeded simulation (point series, or a simulated grid over the polygon)
   |- csv:       parse with column picker -> filter fill/quality -> scale/offset -> aggregate to monthly
   |- appeears:  background job -> MODIS CSV -> parse and filter -> cache -> aggregate to monthly
   |- gesdisc:   background job -> NetCDF granules -> xarray subset -> unit conversion -> cube cache
        |
        v
Area average (polygon, cos-latitude weights) or point series
        |
        v
Statistics: OLS, Sen, Mann-Kendall (lag-1), seasonal Mann-Kendall -> verdict
        |
        v
Optional pixel map: per-cell annual means -> Mann-Kendall -> Benjamini-Hochberg
        |
        v
Chart, map overlay, quality summary, PDF / CSV / JSON
```

## How the statistics work

Time `t` is in decimal years. Results are reported per decade. Code is in `backend/app/stats.py`.

1. **Seasonality (optional).** For each calendar month, subtract that month's long-term mean, leaving anomalies.
2. **Linear regression.** `Y(t) = b0 + b1 t + e`. The slope `b1` and its 95% confidence interval come from `scipy.stats.linregress` with a t critical value.
3. **Mann-Kendall test.** `S` sums the signs of all pairwise differences. The variance includes a correction for tied values. The standardised statistic `Z` gives a two-sided p-value from the normal distribution. H0: no monotonic trend.
4. **Autocorrelation adjustment.** The lag-1 autocorrelation `r` is computed on the **detrended residuals**, so a real trend alone does not inflate it. If `r` is positive, the variance is multiplied by `(1 + r)/(1 - r)`, capped at 6. This is a simplified effective-sample-size correction, not the full Hamed-Rao or Yue-Wang procedure.
5. **Seasonal Mann-Kendall (Hirsch).** `S` and its variance are computed within each calendar month (at least 3 values per month) and summed. The seasonal cycle can neither create nor hide a trend. No autocorrelation correction is applied to this test.
6. **Sen's slope.** The median of all pairwise slopes. For the seasonal test it is the median of within-month slopes.
7. **Benjamini-Hochberg.** For pixel maps. Cells are ranked by p-value and the false discovery rate is controlled at the chosen alpha. Only cells inside the area form the test family.
8. **Verdict.** Fewer than 60 observations gives "Insufficient data". `p < alpha` gives "Significant increasing/decreasing trend". Otherwise "Increasing/Decreasing but not statistically significant".
9. **Area averaging.** `sum(w * x) / sum(w)` over cells inside the polygon, with `w = cos(latitude)` and missing cells dropped per time step. If no cell centre falls inside a tiny polygon, the nearest cell is used.
10. **Per-cell tests.** Each cell needs at least 70% valid months (and at least 60 values) and at least 10 years with 6 or more valid months. The test uses deseasonalised annual means.

A non-significant result is not proof that no change exists. Association is not causation.

## Architecture

```
Browser (React + TypeScript + Vite + Leaflet)
    |  JSON over /api  (Vite dev proxy to :8000)
    v
FastAPI backend
    |-- main.py        endpoints, validation, analysis orchestration
    |-- stats.py       OLS, Mann-Kendall, seasonal MK, Sen, BH, deseasonalisation
    |-- geo.py         polygon checks and masks, area weights, area average
    |-- gridded.py     gridded cubes: simulation, xarray conversion, cache I/O
    |-- ingest.py      CSV inspection and parsing (column picker, scale, fill, quality)
    |-- aggregate.py   monthly aggregation
    |-- jobs.py        background jobs, in-memory registry, disk cache
    |-- report.py      PDF generation
    |-- demo.py        seeded simulation
    |-- catalog.py     variables and preset regions
    '-- connectors/    appeears.py, gesdisc.py, cmr.py
```

Charts are drawn as plain SVG in React. The map uses Leaflet; the satellite imagery tiles come from NASA GIBS.

## Project structure

```
kalyx/
├── README.md
├── .gitignore
├── backend/
│   ├── .env.example               template for credentials (not loaded automatically)
│   ├── requirements.txt           core dependencies
│   ├── requirements-live.txt      extras for the GES DISC connector
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                API endpoints and analysis orchestration
│   │   ├── stats.py               statistical engine
│   │   ├── geo.py                 polygon validation, masks, area weighting
│   │   ├── gridded.py             Cube type, simulated grids, xarray conversion, save/load
│   │   ├── ingest.py              CSV inspection, header detection, parsing and filtering
│   │   ├── aggregate.py           monthly aggregation (mean or sum)
│   │   ├── jobs.py                background fetch jobs and cache
│   │   ├── report.py              PDF report (ReportLab, Matplotlib)
│   │   ├── demo.py                seeded simulated series
│   │   ├── catalog.py             variable catalogue and preset regions
│   │   └── connectors/
│   │       ├── __init__.py        connector registry
│   │       ├── appeears.py        NASA AppEEARS point sampling (MODIS)
│   │       ├── gesdisc.py         NASA GES DISC gridded data (IMERG, MERRA-2, GLDAS)
│   │       └── cmr.py             NASA CMR dataset search
│   └── tests/
│       ├── test_stats.py          core statistics and basic API calls
│       ├── test_features.py       CSV picker, aggregation, seasonal MK, AppEEARS job flow, CMR, PDF
│       ├── test_area.py           polygons, area weighting, xarray conversion, pixel maps, GES DISC job flow
│       └── test_robustness.py     NaN/inf input, constant series, request validation, stale-job checks, job-registry bound
└── frontend/
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── tsconfig.json
    ├── vite.config.ts             dev server, /api proxy, and test (vitest) settings
    ├── public/assets/
    │   └── README.txt             where to put hero and band media
    └── src/
        ├── __tests__/
        │   └── app.test.tsx       component and API tests (vitest, jsdom)
        ├── main.tsx               entry point
        ├── App.tsx                landing page, catalogue, CMR search, layout
        ├── api.ts                 typed API client and PDF download
        ├── styles.css             global styles and design tokens
        └── components/
            ├── MediaHolder.tsx    image or video background holder with gradient fallback
            ├── Investigate.tsx    dashboard: options, data sources, results, exports
            ├── MapPicker.tsx      Leaflet + NASA GIBS, polygon drawing, trend overlay
            ├── CsvPicker.tsx      CSV upload and column picker
            ├── NumInput.tsx       numeric field that allows typing -, 0. and 0.02
            ├── Chart.tsx          time-series SVG chart
            └── Learn.tsx          long-form guide (accordion)
```

Folders created at run time: `backend/.venv/`, `backend/data_cache/` (cached fetches), `frontend/node_modules/`, `frontend/dist/`.

## Getting started

**Requirements:** Python 3.10+ and Node.js 18+.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

For the live GES DISC connector, also run `pip install -r requirements-live.txt`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Requests to `/api` are proxied to the backend.

### 3. First test

Choose a variable, select the simulated source, draw an area on the map, turn on the pixel map, and click **Run analysis**. This works without any NASA login and shows area averaging, the seasonal test and the per-cell map.

### 4. Production build

```bash
cd frontend && npm run build     # output in frontend/dist
```

## Configuration

Environment variables are read by the backend. `.env.example` is only a template: the backend does **not** load a `.env` file, so export the variables in the shell that starts `uvicorn` (or load them with your process manager).

| Variable | Purpose |
|---|---|
| `EARTHDATA_USER` | NASA Earthdata username, for AppEEARS and GES DISC |
| `EARTHDATA_PASS` | NASA Earthdata password |
| `KALYX_CACHE` | Folder for cached fetches (default `backend/data_cache`) |

```bash
export EARTHDATA_USER=your_username          # Windows PowerShell: $env:EARTHDATA_USER="your_username"
export EARTHDATA_PASS=your_password
```

Never commit credentials. `.gitignore` already excludes `.env` and `backend/data_cache`.

## Using real NASA data

Create a free Earthdata account at https://urs.earthdata.nasa.gov. Then choose one route.

**A. Import a CSV.** Export from NASA Giovanni (Time Series, Area-Averaged) or AppEEARS, then choose **Imported CSV**. The column picker detects the date and value columns. Adjust them if needed and set the optional quality column, scale factor, offset and fill value. Example for MODIS land surface temperature from AppEEARS: scale `0.02`, offset `-273.15`, fill value `0`, quality column `QC_Day`, keep quality up to `1`.

**B. Live point fetch (AppEEARS).** For MODIS land surface temperature (`lst`) and NDVI (`ndvi`) at the selected point.

**C. Live gridded fetch (NASA GES DISC).** For precipitation (`pr`), soil wetness (`sm`), runoff (`ro`) and evapotranspiration (`et`) over your drawn area. This enables area averages and real pixel maps.

Always check units, scale factors and quality flags before trusting a result.

### Monthly aggregation

8-day, 16-day or daily observations are aggregated to monthly values: **mean** for temperature and indices, **sum** for accumulated precipitation, or **none**. The response and the PDF record the number of input observations, months produced, missing months, and observations per month. Sums assume complete coverage within each month and warn that months with missing observations are underestimated.

### Units

Live fetches report the unit of the converted data (for example `mm/month`), which can differ from the catalogue card's unit text. The demo series uses the catalogue unit.

## Live NASA connectors

### AppEEARS (`connectors/appeears.py`)

- Point-sample tasks for `lst` (MOD11A2.061, layer `LST_Day_1km`, quality `QC_Day`) and `ndvi` (MOD13Q1.061).
- Flow: log in, submit task, poll status, download the results CSV, parse with scale, offset, fill and quality filtering, cache.
- Quality: MODIS QC bits 0 and 1 are checked; values above 1 (cloud or no data) are dropped.

### GES DISC (`connectors/gesdisc.py`)

Install `requirements-live.txt` (earthaccess, h5netcdf, dask).

| Variable id | Product | Variable | Conversion |
|---|---|---|---|
| `pr` | GPM_3IMERGM v07 | `precipitation` | mm/hr to mm/month |
| `sm` | M2TMNXLND v5.12.4 | `GWETROOT` | none (fraction) |
| `ro` | M2TMNXLND v5.12.4 | `RUNOFF` | kg m-2 s-1 to mm/month |
| `et` | GLDAS_NOAH025_M v2.1 | `Evap_tavg` | kg m-2 s-1 to mm/month |

The connector logs in with `earthaccess`, searches CMR for monthly granules, opens them with `xarray` (`h5netcdf` engine), subsets your drawn area (or a 1 degree box around the point when no polygon is drawn), converts units, and caches the cube as a compressed `.npz` file. Limits: areas up to 20 degrees across and at most 400 granules per request. Large areas and long periods are slow because files are read over the network.

Product names, versions and variable names come from NASA documentation and must be checked on each dataset's page at https://disc.gsfc.nasa.gov/. A wrong variable name returns an error that lists the variables available in the files.

### CMR (`connectors/cmr.py`)

The "Search NASA datasets" box queries the public CMR collections endpoint. No login is needed.

### Status of the connectors

The code paths are covered by tests that use fake connectors and synthetic datasets. They have **not been run against the live NASA services**. Expect to adjust details on first run, such as product or layer names, bundle file names, or granule limits. Verify AppEEARS details at https://appeears.earthdatacloud.nasa.gov/api/.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/catalog` | List variables |
| GET | `/api/catalog/{id}` | One variable |
| GET | `/api/regions` | Preset regions |
| POST | `/api/analysis/trend` | Time series and trend statistics (point or area) |
| POST | `/api/analysis/spatial` | Per-cell trends with FDR correction (simulated grid or GES DISC data) |
| POST | `/api/data/inspect` | Detect columns in a CSV for the column picker |
| GET | `/api/data/products` | Variables with a live connector, per connector |
| POST | `/api/data/fetch` | Start a background job; returns `job_id` |
| GET | `/api/data/status/{id}` | Job status, progress, message, kind and connector |
| GET | `/api/discover?q=&limit=` | Search NASA CMR collections |
| POST | `/api/reports/pdf` | Download the PDF report (`include_map` adds the trend map) |

### Analysis request

```json
{
  "variable": "lst",
  "lat": 22.8,
  "lon": 86.2,
  "start_year": 2001,
  "end_year": 2025,
  "alpha": 0.05,
  "deseasonalize": true,
  "test": "mk",
  "source": "demo",
  "aggregate": "mean",
  "csv_text": null,
  "job_id": null,
  "polygon": [[22.0, 85.5], [22.0, 87.0], [23.5, 87.0], [23.5, 85.5]]
}
```

| Field | Meaning |
|---|---|
| `source` | `"demo"`, `"csv"`, or `"job"` (a finished fetch job) |
| `test` | `"mk"` or `"seasonal"`: which test decides the verdict |
| `aggregate` | `"mean"`, `"sum"` or `"none"` (applies to CSV and AppEEARS data) |
| `polygon` | Optional `[[lat, lon], ...]`, at least 3 vertices, at most 20 degrees across. With it the analysis is an area average |
| CSV options | `date_col`, `value_col`, `qc_col`, `qc_max`, `scale`, `offset`, `fill_value` |

The spatial endpoint accepts the same body. It needs `source: "demo"` or a finished GES DISC `job_id`.

### Fetch request

```json
{ "connector": "gesdisc", "variable": "pr", "lat": 22.8, "lon": 86.2,
  "start_year": 2001, "end_year": 2020, "polygon": [[22.0, 85.5], [22.0, 87.0], [23.5, 87.0], [23.5, 85.5]] }
```

`connector` is `"appeears"` (variables `lst`, `ndvi`) or `"gesdisc"` (variables `pr`, `sm`, `ro`, `et`). The response contains a `job_id`. Poll `/api/data/status/{job_id}` until `status` is `done` or `error`, then pass the id as `job_id` in an analysis request with `source: "job"`.

### Trend response (main fields)

| Field | Meaning |
|---|---|
| `variable`, `unit`, `dataset`, `n` | Identification and number of monthly values |
| `data_origin` | Simulated, user CSV, or NASA live fetch |
| `series` | `[{t, v}]` monthly series |
| `ols` | `slope_per_decade`, `ci95_per_decade`, `r2`, intercepts |
| `sen_per_decade` | Sen's slope per decade |
| `mann_kendall`, `seasonal_mk` | `S`, `z`, `p`, `tau`, lag-1 (and seasons used for the seasonal test) |
| `test_used`, `verdict` | Which test decided, and the plain-language verdict |
| `aggregation`, `data_quality`, `area` | Aggregation record, quality summary, area-average details |
| `seasonal_cycle`, `caveat` | Monthly means and the standard caveat |

### Spatial response (main fields)

`cells` (each with `row`, `col`, `lat`, `lon`, `slope_per_decade`, `p`, `significant_fdr`), `nrows`, `ncols`, `dlat`, `dlon`, `n_tested`, `n_significant`, `opposite_trends`, `unit`, `data_origin`.

### Errors

Requests are validated: years must be between 1950 and 2100, `alpha` between 0 and 1, and `csv_text` at most 10 MB. A job can only be analysed for the variable (and, for AppEEARS, the location) it was fetched for.

Errors return JSON `{"detail": "..."}` with status 404, 422 or 502. Common 422 causes: a period under 10 years, fewer than 24 valid observations, an invalid or oversized polygon, a missing column, an unfinished job, or a pixel-map request on point-only data.

## Frontend guide

| File | Role |
|---|---|
| `App.tsx` | Landing sections, variable catalogue, CMR search, dashboard and Learn placement |
| `components/Investigate.tsx` | Dashboard state: variable, location, period, test, aggregation, data source, job polling, results, PDF and copy buttons |
| `components/MapPicker.tsx` | Leaflet map with GIBS layer and date selection, point picking, polygon drawing, and the pixel-trend overlay |
| `components/NumInput.tsx` | Numeric text field that keeps what you type (for example `-273.15` or `0.02`) and reports only valid numbers |
| `components/CsvPicker.tsx` | Upload or paste CSV, column detection, scale, offset, fill, quality options, preview |
| `components/Chart.tsx` | Time series with the linear trend line |
| `components/MediaHolder.tsx` | Looks for `/assets/<name>.mp4` and `/assets/<name>.jpg`; falls back to a gradient |
| `components/Learn.tsx` | The long-form guide. Edit the `SECTIONS` array to change the text |
| `api.ts` | Types and fetch helpers for every endpoint |
| `styles.css` | Colour tokens (`#050607` background, `#69D5E8` accent), layout, responsive rules |

## Media assets

Put these files in `frontend/public/assets/`:

| File | Used for |
|---|---|
| `hero.mp4` or `hero.jpg` | Landing page hero background |
| `band.mp4` or `band.jpg` | Full-width mid-page band |

If a file is missing, a gradient is shown instead. Use short, muted, compressed videos. Check the usage terms and credit line of any imagery before publishing, and list each one in your resources. You can change file extensions as per your choice but remember to change extension in `frontend/src/components/MediaHolder.tsx`.

## Testing

**Backend** (28 tests):

```bash
cd backend
pytest
```

They cover: trend detection and a no-trend control; Benjamini-Hochberg; CSV inspection (Giovanni layout), scale, fill and quality filtering; monthly aggregation; seasonal Mann-Kendall; the CSV column-picker API path; the AppEEARS and GES DISC job and cache flows with fake connectors; missing-credential messages; CMR parsing; polygon masks, validation and area weighting; xarray conversion and unit conversion; per-cell opposite-trend detection with FDR; PDF generation; and robustness cases (NaN or infinite values, constant series, out-of-range requests, a fetched job reused for a different variable or place, and the bounded job registry).

**Frontend** (13 tests, Vitest with jsdom and Testing Library):

```bash
cd frontend
npm test
```

They cover: typing negative and partial decimals in numeric fields, API error formatting, running an analysis and showing the verdict or an error, blocking a live-source run until data is fetched, dropping a fetched job when the variable or place changes, the chart (including a flat series), the media-holder fallback, and the Learn guide. The map component is replaced by a stub in these tests, so Leaflet and polygon drawing are not covered by automated tests. `npm run build` also type-checks the code.

## Deployment notes

- Host `frontend/dist` on a static host (Vercel, Netlify) and the backend on a Python host (Render, Railway).
- `api.ts` calls relative `/api/...` URLs. In development Vite proxies them. In production, either serve both behind one domain with a rewrite from `/api` to the backend, or change the base URL in `api.ts`.
- CORS currently allows all origins. Restrict `allow_origins` in `main.py` for production.
- Set `EARTHDATA_USER` and `EARTHDATA_PASS` as secrets on the backend host. Use a persistent disk or set `KALYX_CACHE` to a persistent path if you want the cache to survive restarts.
- Jobs run as FastAPI background tasks in one process, and the job registry is in memory. Run a single worker, or replace it with a job queue before scaling.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Request failed" or empty results | The backend is not running. Keep both terminals open |
| `python` or `pip` not found | Try `python3` and `pip3` |
| Port already in use | Run `uvicorn app.main:app --port 8001` and update the proxy target in `frontend/vite.config.ts` |
| Map shows no imagery | Needs an internet connection. Try another date or layer; GIBS imagery for the latest days can be missing |
| "Set EARTHDATA_USER and EARTHDATA_PASS" | Export both variables in the shell that runs the backend, then restart it |
| "Live GES DISC access needs extra packages" | Run `pip install -r requirements-live.txt` |
| "Variable ... not in the files" | The variable name differs. The error lists the available names; update `connectors/gesdisc.py` |
| "No granules found" | Check the product, version, period and area at https://disc.gsfc.nasa.gov/ |
| "Pixel maps need gridded data" | Use the simulated source or a GES DISC fetch; CSV and AppEEARS are point-only |
| "Area too large" | Keep the polygon within 20 degrees in each direction |
| Result differs from a paper | Dataset version, period, quality filtering, aggregation, area and test choice all change results. The PDF report records the settings |

## Scientific safeguards

- Seasonal cycle removal and a seasonal Mann-Kendall test.
- Mann-Kendall variance adjusted for positive lag-1 autocorrelation of the detrended residuals (simplified).
- Area averages weighted by cos(latitude), with missing cells ignored and per-cell coverage thresholds.
- Multiple-testing correction across map cells.
- Quality-flag, fill-value and scale handling for imported and fetched data, with a data-quality summary.
- Short records flagged as insufficient data.
- Simulated data is labelled wherever it appears, including the PDF.
- Every result states that significance is not proof of cause.

## Limitations

- The AppEEARS, GES DISC and CMR connectors and the GIBS layer settings are **untested against the real services**. Gridded jobs can be slow and large.
- Live gridded data covers `pr`, `sm`, `ro` and `et` only, and monthly products only. Other variables need CSV import or a new entry in `connectors/gesdisc.py`.
- AppEEARS is point sampling only. Area averages and pixel maps need GES DISC or simulated data.
- Polygon membership uses cell centres, so cells partly inside are included or excluded as a whole. Cells coarser than the polygon fall back to the nearest cell.
- The seasonal Mann-Kendall test has no autocorrelation correction, and the lag-1 adjustment is not the full Hamed-Rao or Yue-Wang method. Per-cell tests use only 10 to 25 annual values.
- Jobs are held in memory (the newest 30 finished jobs are kept) and lost on restart (cached data survives). Monthly sums assume complete coverage.
- The catalogue unit text for some variables differs from the unit of live-converted data.
- No accounts, database or saved investigations. The map (Leaflet, GIBS tiles, polygon drawing) has no automated tests and has not been checked in a real browser.
- Trend significance is statistical evidence only. It does not identify causes.

## Roadmap

- Click a map cell to see that cell's time series
- More GES DISC products (ozone, soil moisture layers) and daily-to-monthly cube aggregation
- Fuller autocorrelation correction (multi-lag); persistent job store (Redis)
- Region comparison and multi-variable correlation
- Trend Atlas of cached results; PostgreSQL with PostGIS for saved investigations
- Browser-level end-to-end tests for the map and polygon drawing

## Data sources and credits

KALYX is designed around these NASA products. Follow each dataset's citation, license and attribution requirements, and cite the official dataset DOI from its landing page.

- NASA GIBS (satellite imagery tiles): https://nasa-gibs.github.io/gibs-api-docs/
- GPM IMERG precipitation: https://gpm.nasa.gov/data/directory
- MODIS MOD11A2 land surface temperature: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD11A2
- MERRA-2 land surface diagnostics (M2TMNXLND), NASA GMAO: https://disc.gsfc.nasa.gov/
- GLDAS: https://ldas.gsfc.nasa.gov/gldas
- OMI/MLS tropospheric ozone: https://ozoneaq.gsfc.nasa.gov/data/omi/
- NASA Giovanni: https://giovanni.gsfc.nasa.gov/
- NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov/
- NASA Earthdata CMR: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
- NASA Earthdata Login: https://urs.earthdata.nasa.gov
- Challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/

Other tools: React, Vite, TypeScript, Leaflet, FastAPI, Uvicorn, Pydantic, NumPy, SciPy, pandas, xarray, Requests, ReportLab, Matplotlib, pytest, earthaccess, h5netcdf, dask, and Google Fonts (Inter, Barlow Condensed, IBM Plex Mono).

NASA does not endorse this project. The website design takes inspiration from aerospace web design but is an original layout.

## AI assistance disclosure

This project's code and documentation were generated with the side help of an AI assistant (Claude, by Anthropic) and then reviewed and run by the team.
