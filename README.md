# KALYX: Reach Infinity

**Turn Earth observation data into evidence of environmental change.**

KALYX is a full-stack web application for investigating how the Earth is changing. A user picks an environmental variable, a place and a period, and KALYX builds the time series, estimates the rate of change, tests whether the trend is statistically significant, and maps where the change differs inside the region.

Built for the NASA Space Apps Challenge 2026, **Be an Earth System Trend Detective!**

> **Data status:** the built-in `demo` source is a seeded **simulation**, labelled as such in every API response and on screen. It demonstrates the pipeline and is not NASA data. For real results, import a CSV exported from NASA Giovanni or AppEEARS. An AppEEARS connector and CMR search are implemented but have not been run against the live services; see [Live NASA connectors](#live-nasa-connectors).

---

## Contents

1. [What it answers](#what-it-answers)
2. [Features](#features)
3. [How the statistics work](#how-the-statistics-work)
4. [Architecture](#architecture)
5. [Project structure](#project-structure)
6. [Getting started](#getting-started)
7. [Using real NASA data](#using-real-nasa-data)
8. [API reference](#api-reference)
9. [Media assets](#media-assets)
10. [Testing](#testing)
11. [Scientific safeguards and limitations](#scientific-safeguards-and-limitations)
12. [Roadmap](#roadmap)
13. [Data sources and credits](#data-sources-and-credits)
14. [AI assistance disclosure](#ai-assistance-disclosure)

---

## What it answers

| Question | How KALYX answers it |
|---|---|
| What is changing? | A catalogue of eight Earth-system variables |
| Where? | Preset regions or coordinates, plus a pixel-level trend map |
| How is it changing? | Increasing, decreasing, or not significant |
| How much? | Ordinary least squares and Sen's slope, in units per decade |
| Is it significant? | Mann-Kendall test with autocorrelation adjustment, and false-discovery correction across map cells |

## Features

- **Variable explorer:** eight variables with source product, spatial and temporal resolution, units and coverage. Examples: GPM IMERG precipitation, MODIS land surface temperature, MERRA-2 soil wetness and runoff, OMI ozone, MODIS NDVI, sea surface temperature, GLDAS evapotranspiration.
- **Investigation workspace:** choose variable, region (preset or latitude/longitude), period, significance level, and whether to remove the seasonal cycle.
- **Statistical engine:** linear regression with a 95% confidence interval, Sen's slope, Mann-Kendall test, lag-1 autocorrelation, and a plain-language verdict.
- **Pixel mode:** an 8x8 grid where every cell is tested separately and corrected with Benjamini-Hochberg. Opposite trends inside one region are flagged.
- **CSV import:** upload or paste a `date,value` time series.
- **Real satellite map:** Leaflet with NASA GIBS imagery (MODIS true colour, land surface temperature, Blue Marble). Click to set the analysis point.
- **Column picker and quality control:** scale, offset, fill value and quality-flag filtering with a data-quality summary.
- **Monthly aggregation** and **seasonal Mann-Kendall.**
- **Live fetch:** AppEEARS background jobs with progress and caching; CMR dataset search.
- **Export:** download a PDF report (setup, finding, charts, trend map, limitations), copy CSV, copy JSON metadata.
- **Media holders:** the landing page loads video or image backgrounds from `frontend/public/assets/`.
- **Responsive and accessible:** works from phone to desktop, with visible keyboard focus and reduced-motion support.

## How the statistics work

Time `t` is in decimal years. Results are reported per decade.

1. **Seasonality (optional).** For each calendar month, subtract that month's long-term mean, leaving anomalies.
2. **Linear regression.** `Y(t) = b0 + b1 t + e`. The slope `b1` and its 95% confidence interval come from `scipy.stats.linregress` with a t critical value.
3. **Mann-Kendall test.** `S` sums the signs of all pairwise differences. The variance includes a correction for tied values. The standardised statistic `Z` gives a two-sided p-value from the normal distribution. H0: no monotonic trend.
4. **Seasonal Mann-Kendall (Hirsch).** S and its variance are computed within each calendar month and summed, so the seasonal cycle cannot create or hide a trend. Choose it as the verdict test in the UI. Both tests are always reported.
5. **Autocorrelation adjustment.** If lag-1 autocorrelation `r` is positive, the variance is multiplied by `(1 + r)/(1 - r)`, capped at 6. This is a simple effective-sample-size style correction. It is not the full Hamed-Rao or Yue-Wang procedure.
5. **Sen's slope.** The median of all pairwise slopes. It is robust to outliers.
6. **Benjamini-Hochberg.** Used across pixels. Cells are ranked by p-value, and the false discovery rate is controlled at the chosen alpha.
7. **Verdict.**
   - fewer than 60 observations: "Insufficient data";
   - `p < alpha`: "Significant increasing/decreasing trend";
   - otherwise: "Increasing/Decreasing but not statistically significant".

A non-significant result is not proof that no change exists. Association is not causation.

## Architecture

```
Browser (React + TypeScript + Vite)
    |  JSON over /api (Vite dev proxy to :8000)
    v
FastAPI backend
    |-- catalog.py   variable and region metadata
    |-- demo.py      seeded simulation (labelled as simulated)
    |-- stats.py     OLS, Mann-Kendall, Sen, BH, deseasonalisation
    |-- main.py      endpoints, validation, CSV parsing
    v
(planned) connectors/  AppEEARS, GES DISC, CMR
```

Charts and trend maps are drawn as plain SVG in React. There is no charting library.

## Project structure

```
kalyx/
├── README.md
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py        API endpoints
│   │   ├── stats.py       statistical engine
│   │   ├── aggregate.py   monthly aggregation
│   │   ├── ingest.py      CSV inspection and parsing
│   │   ├── jobs.py        background jobs and cache
│   │   ├── report.py      PDF report
│   │   ├── connectors/    appeears.py, cmr.py
│   │   ├── catalog.py     variables and regions
│   │   └── demo.py        simulated series
│   └── tests/
│       └── test_stats.py
|       └── test_features.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── public/assets/     hero and band media go here
    └── src/
        ├── main.tsx
        ├── App.tsx        landing page and catalogue
        ├── api.ts         typed API client
        ├── styles.css
        └── components/
            ├── Investigate.tsx
            ├── Chart.tsx
            ├── MapPicker.tsx  Leaflet + NASA GIBS
            ├── CsvPicker.tsx  column picker
            └── MediaHolder.tsx
```

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

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Requests to `/api` are proxied to the backend.

### 3. Production build

```bash
cd frontend && npm run build     # output in frontend/dist
```

For deployment, host `dist/` on a static host (Vercel, Netlify) and the backend on a Python host (Render, Railway). Set the frontend to call your backend URL, or add a rewrite for `/api`.

## Using real NASA data
Two routes:

**A. Import a CSV (no login in the app).** Export from NASA Giovanni (Time Series, Area-Averaged) or AppEEARS, then choose **Imported CSV**. The **column picker** detects the date and value columns (it skips metadata lines above the header), and lets you set the quality column, a scale factor, an offset and a fill value to drop. Example for MODIS LST from AppEEARS: scale `0.02`, offset `-273.15`, fill `0`, quality column `QC_Day`, keep quality up to `1`.

**B. Live fetch (AppEEARS).** See below.

Always check units, scale factors and quality flags before trusting a result.

### Monthly aggregation
8-day, 16-day or daily observations are aggregated to monthly values: **mean** for temperature and indices, **sum** for accumulated precipitation, or **none**. The response and PDF record the number of input observations, months produced, missing months and observations per month. Sums warn that months with missing observations are underestimated.

### Live NASA connectors
Set credentials as environment variables on the backend (never in the frontend or repo):

```bash
export EARTHDATA_USER=your_username
export EARTHDATA_PASS=your_password
```

- **AppEEARS** (`backend/app/connectors/appeears.py`): point-sample tasks for MODIS LST (`MOD11A2.061`) and NDVI (`MOD13Q1.061`). The UI starts a background job, polls its progress, then analyses the result. Results are cached in `backend/data_cache/` (set `KALYX_CACHE` to move it).
- **CMR** (`connectors/cmr.py`): the "Search NASA datasets" box queries NASA Earthdata CMR collections. No login needed.

These connectors follow the public API documentation, and the code paths are covered by tests using fake responses. They have **not been run against the live NASA services** in development. Verify product and layer names at https://appeears.earthdatacloud.nasa.gov/api/ and expect to adjust details on first run.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/catalog` | List variables |
| GET | `/api/catalog/{id}` | One variable |
| GET | `/api/regions` | Preset regions |
| POST | `/api/analysis/trend` | Regional time series and trend statistics |
| POST | `/api/analysis/spatial` | Pixel-level grid with FDR correction (demo source only) |
| POST | `/api/data/inspect` | Detect columns in a CSV for the column picker |
| GET | `/api/data/products` | Products with a live connector |
| POST | `/api/data/fetch` | Start an AppEEARS background job (returns `job_id`) |
| GET | `/api/data/status/{id}` | Job status and progress |
| GET | `/api/discover?q=` | Search NASA CMR collections |
| POST | `/api/reports/pdf` | Download the PDF report |

**Request body** (both POST endpoints):

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
  "grid": 8
}
```

`source` is `"demo"`, `"csv"` (put the file in `csv_text`, optionally `date_col`, `value_col`, `qc_col`, `qc_max`, `scale`, `offset`, `fill_value`) or `"job"` (use a finished `job_id`). `test` is `"mk"` or `"seasonal"`; `aggregate` is `"mean"`, `"sum"` or `"none"`. `grid` applies to the spatial endpoint (2 to 16).

**Example:**

```bash
curl -X POST http://localhost:8000/api/analysis/trend \
  -H "Content-Type: application/json" \
  -d '{"variable":"pr","lat":22.8,"lon":86.2}'
```

**Trend response (abridged):**

```json
{
  "variable": "Precipitation",
  "unit": "mm/month",
  "dataset": "GPM IMERG",
  "n": 300,
  "data_origin": "SIMULATED demo series (not NASA measurements)",
  "ols": { "slope_per_decade": -7.9, "ci95_per_decade": 3.1, "r2": 0.01, "intercept": 0.0 },
  "sen_per_decade": -7.6,
  "mann_kendall": { "S": 0, "z": 0, "p": 0, "tau": 0, "lag1": 0 },
  "verdict": "Significant decreasing trend",
  "seasonal_cycle": [],
  "caveat": "A non-significant result does not prove that no change exists; association is not causation."
}
```

Values above are illustrative. Real calls return computed numbers. Errors return a JSON `detail` message with status 404 or 422, for example when the period is shorter than 10 years or fewer than 24 valid observations remain.

## Media assets

Put these files in `frontend/public/assets/`:

| File | Used for |
|---|---|
| `hero.mp4` or `hero.jpg` | Landing page hero background |
| `band.mp4` or `band.jpg` | Full-width mid-page band |

If a file is missing, a gradient is shown instead. Use videos that are muted, short and compressed. Check the license and credit line for any NASA or third-party imagery before publishing.

## Testing

```bash
cd backend
pytest
```

Thirteen tests cover the statistics (including seasonal Mann-Kendall), aggregation, CSV inspection and filtering, the job and cache flow with a fake connector, CMR parsing, and PDF generation. There are no frontend tests yet.

## Scientific safeguards and limitations
**Built in**

- Seasonal cycle removal and a seasonal Mann-Kendall test.
- Mann-Kendall variance adjusted for positive lag-1 autocorrelation (simplified).
- Multiple-testing correction across map cells.
- Quality-flag, fill-value and scale handling for imported data, with a data-quality summary.
- Short records flagged as insufficient data. Simulated data labelled wherever it appears.

**Limitations**

- Live NASA connectors are untested against the real services. GPM IMERG, MERRA-2 and GLDAS have no live connector yet; use CSV import.
- The pixel map works only on the simulated grid. The analysis uses a single point, not an area average.
- The seasonal Mann-Kendall test has no autocorrelation correction. The lag-1 adjustment is not the full Hamed-Rao or Yue-Wang method.
- Monthly sums assume complete coverage. AppEEARS jobs are held in memory and lost on restart (cached data survives).
- GIBS layer ids and zoom levels should be checked against https://nasa-gibs.github.io/gibs-api-docs/. Imagery is visual context only.
- No accounts, database or saved investigations. No frontend tests.
- Trend significance is statistical evidence only. It does not identify causes.

## Roadmap
- GES DISC access for GPM IMERG, MERRA-2 and GLDAS through `earthaccess` and `xarray`
- Area (polygon) sampling and real gridded pixel maps
- Polygon drawing and clickable cells on the map
- Region comparison and multi-variable correlation
- Fuller autocorrelation correction; persistent job store (Redis)
- Trend Atlas of cached results; PostgreSQL with PostGIS for saved investigations

## Data sources and credits

KALYX is designed around these NASA products. Follow each dataset's citation, license and attribution requirements, and cite the official dataset DOI from its landing page.

- GPM IMERG precipitation: https://gpm.nasa.gov/data/directory
- MODIS MOD11A2 land surface temperature: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD11A2
- MERRA-2 land surface diagnostics (M2TMNXLND), NASA GMAO: https://disc.gsfc.nasa.gov/
- GLDAS: https://ldas.gsfc.nasa.gov/gldas
- OMI/MLS tropospheric ozone: https://ozoneaq.gsfc.nasa.gov/data/omi/
- NASA Giovanni: https://giovanni.gsfc.nasa.gov/
- NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov/
- NASA GIBS (satellite imagery tiles): https://nasa-gibs.github.io/gibs-api-docs/
- NASA Earthdata CMR: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
- Challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/

NASA does not endorse this project. Website design takes inspiration from aerospace web design but is an original layout.

## AI assistance disclosure

This project's code and documentation were generated with the side help of an AI assistant (Claude, by Anthropic) and then reviewed & modified and run by the team.
