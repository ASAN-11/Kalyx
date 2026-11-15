from typing import Literal, Optional
import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from . import aggregate, catalog, ingest, jobs, report, stats
from .connectors import PRODUCTS
from .connectors.cmr import search_collections
from .demo import simulate

app = FastAPI(title="KALYX API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Req(BaseModel):
    variable: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start_year: int = 2001
    end_year: int = 2025
    alpha: float = 0.05
    deseasonalize: bool = True
    test: Literal["mk", "seasonal"] = "mk"
    source: Literal["demo", "csv", "job"] = "demo"
    csv_text: Optional[str] = None
    job_id: Optional[str] = None
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    qc_col: Optional[str] = None
    qc_max: Optional[int] = None
    scale: float = 1.0
    offset: float = 0.0
    fill_value: Optional[float] = None
    aggregate: Literal["none", "mean", "sum"] = "mean"
    grid: int = Field(8, ge=2, le=16)

class PdfReq(Req):
    include_map: bool = False

class InspectReq(BaseModel):
    csv_text: str

class FetchReq(BaseModel):
    variable: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start_year: int = 2001
    end_year: int = 2025

def load(r, var):
    if r.end_year - r.start_year < 9: raise HTTPException(422, "Use at least 10 years of data.")
    info, quality = None, None
    try:
        if r.source == "demo":
            t, m, v = simulate(var, r.lat, r.lon, r.start_year, r.end_year)
        else:
            if r.source == "csv":
                p = ingest.parse_table(r.csv_text, r.date_col, r.value_col, r.qc_col, r.qc_max, r.scale, r.offset, r.fill_value)
            else:
                res = jobs.get_result(r.job_id or "")
                if not res: raise HTTPException(422, "Fetch job not found or not finished.")
                p = jobs.arrays(res); p["report"] = res["report"]
            quality = p["report"]
            if r.aggregate == "none": t, m, v = p["t"], p["months"], p["values"]
            else: t, m, v, info = aggregate.to_monthly(p["years"], p["months"], p["values"], r.aggregate)
    except ValueError as e:
        raise HTTPException(422, str(e))
    k = (t >= r.start_year) & (t < r.end_year + 1)
    if k.sum() < 24: raise HTTPException(422, "Need at least 24 valid observations in the selected period.")
    return t[k], m[k], v[k], info, quality

def analyse(r):
    var = catalog.get(r.variable)
    if not var: raise HTTPException(404, "Unknown variable")
    t, m, v, info, quality = load(r, var)
    y = stats.deseasonalize(m, v) if r.deseasonalize else v
    o, k = stats.ols(t, y), stats.mann_kendall(t, y); raw = stats.ols(t, v)
    sk = stats.seasonal_mann_kendall(m, t, v)
    use = sk if (r.test == "seasonal" and sk) else k
    return dict(
        variable=var["name"], unit=var["unit"], dataset=var["source"], n=len(t), alpha=r.alpha,
        data_origin={"demo": "SIMULATED demo series (not NASA measurements)", "csv": "user-imported CSV", "job": "NASA AppEEARS fetch"}[r.source],
        series=[dict(t=float(a), v=float(b)) for a, b in zip(t, v)],
        ols=dict(slope_per_decade=o["slope"]*10, ci95_per_decade=o["ci95"]*10, r2=o["r2"], intercept=o["intercept"],
                 slope_raw=raw["slope"], intercept_raw=raw["intercept"]),
        sen_per_decade=(use["sen"] if "sen" in use else k["sen"])*10,
        mann_kendall=dict(S=k["S"], z=k["z"], p=k["p"], tau=k["tau"], lag1=k["lag1"]),
        seasonal_mk=sk, test_used="Seasonal Mann-Kendall" if use is sk and sk else "Mann-Kendall (lag-1 adjusted)",
        deseasonalized=r.deseasonalize, aggregation=info, data_quality=quality,
        verdict=stats.verdict(len(t), use["p"], use["S"], r.alpha),
        seasonal_cycle=[float(v[m == i].mean()) if (m == i).any() else None for i in range(12)],
        caveat="A non-significant result does not prove that no change exists; association is not causation.")

def grid_analysis(r):
    var = catalog.get(r.variable)
    if not var: raise HTTPException(404, "Unknown variable")
    if r.source != "demo": raise HTTPException(422, "Pixel mode needs gridded data; only the demo grid is available.")
    N, cells, ps = r.grid, [], []
    rng = np.random.default_rng(int(abs(r.lat*31 + r.lon*17)) + 5); yrs = np.arange(r.start_year, r.end_year + 1)
    for i in range(N*N):
        g = ((i % N)/(N-1) - .5)*2*abs(var["trend"])*1.3 + (rng.random() - .5)*abs(var["trend"])
        t, m, v = simulate(var, r.lat + (i//N)*.25, r.lon + (i % N)*.25, r.start_year, r.end_year, trend=g, seed_extra=i)
        a = stats.deseasonalize(m, v); ann = np.array([a[(t >= y) & (t < y+1)].mean() for y in yrs])
        k = stats.mann_kendall(yrs, ann, sen=False)
        cells.append(dict(row=i//N, col=i % N, slope_per_decade=stats.ols(yrs, ann)["slope"]*10, p=k["p"])); ps.append(k["p"])
    sig = stats.benjamini_hochberg(ps, r.alpha)
    for c, s in zip(cells, sig): c["significant_fdr"] = bool(s)
    sl = [c["slope_per_decade"] for c in cells]
    return dict(cells=cells, grid=N, opposite_trends=bool(min(sl) < 0 < max(sl)), n_significant=int(sig.sum()),
                data_origin="SIMULATED demo grid (not NASA measurements)")

@app.get("/api/catalog")
def get_catalog(): return catalog.VARIABLES

@app.get("/api/catalog/{vid}")
def get_variable(vid: str):
    v = catalog.get(vid)
    if not v: raise HTTPException(404, "Unknown variable")
    return v

@app.get("/api/regions")
def get_regions(): return catalog.REGIONS

@app.post("/api/analysis/trend")
def trend(r: Req): return analyse(r)

@app.post("/api/analysis/spatial")
def spatial(r: Req): return grid_analysis(r)

@app.post("/api/data/inspect")
def inspect(r: InspectReq): return ingest.inspect_csv(r.csv_text)

@app.get("/api/data/products")
def products(): return {k: dict(product=v["product"], layer=v["layer"], unit=v["unit"]) for k, v in PRODUCTS.items()}

@app.post("/api/data/fetch")
def data_fetch(r: FetchReq, bg: BackgroundTasks):
    if r.variable not in PRODUCTS: raise HTTPException(422, f"No live connector for '{r.variable}'. Available: {', '.join(PRODUCTS)}.")
    jid = jobs.create(r.variable, r.lat, r.lon, r.start_year, r.end_year)
    bg.add_task(jobs.run, jid, r.variable, r.lat, r.lon, r.start_year, r.end_year)
    return dict(job_id=jid, status=jobs.JOBS[jid]["status"])

@app.get("/api/data/status/{jid}")
def data_status(jid: str):
    j = jobs.JOBS.get(jid)
    if not j: raise HTTPException(404, "Unknown job")
    res = j["result"]
    return dict(job_id=jid, status=j["status"], progress=j["progress"], message=j["message"], cached=j.get("cached", False),
                summary=(dict(report=res["report"], meta=res["meta"]) if res else None))

@app.get("/api/discover")
def discover(q: str, limit: int = 10):
    try: return search_collections(q, min(limit, 25))
    except Exception as e: raise HTTPException(502, f"CMR search failed: {e}")

@app.post("/api/reports/pdf")
def pdf(r: PdfReq):
    res = analyse(r); sp = grid_analysis(r) if (r.include_map and r.source == "demo") else None
    data = report.build_pdf(res, sp, r.model_dump())
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="kalyx-report.pdf"'})
