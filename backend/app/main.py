from typing import Literal, Optional
import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from . import aggregate, catalog, geo, gridded, ingest, jobs, report, stats
from .connectors import GRID_PRODUCTS, PRODUCTS
from .connectors.cmr import search_collections
from .demo import simulate

app = FastAPI(title="KALYX API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Req(BaseModel):
    variable: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start_year: int = Field(2001, ge=1950, le=2100)
    end_year: int = Field(2025, ge=1950, le=2100)
    alpha: float = Field(0.05, gt=0, lt=1)
    deseasonalize: bool = True
    test: Literal["mk", "seasonal"] = "mk"
    source: Literal["demo", "csv", "job"] = "demo"
    csv_text: Optional[str] = Field(None, max_length=10_000_000)
    job_id: Optional[str] = None
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    qc_col: Optional[str] = None
    qc_max: Optional[int] = None
    scale: float = 1.0
    offset: float = 0.0
    fill_value: Optional[float] = None
    aggregate: Literal["none", "mean", "sum"] = "mean"
    polygon: Optional[list[list[float]]] = None  # [[lat, lon], ...]

class PdfReq(Req):
    include_map: bool = False

class InspectReq(BaseModel):
    csv_text: str

class FetchReq(BaseModel):
    connector: Literal["appeears", "gesdisc"] = "appeears"
    polygon: Optional[list[list[float]]] = None
    variable: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start_year: int = Field(2001, ge=1950, le=2100)
    end_year: int = Field(2025, ge=1950, le=2100)

def poly_of(r):
    try: return geo.check_polygon(r.polygon)
    except ValueError as e: raise HTTPException(422, str(e))

def clean(o):
    """Replace non-finite floats with None so responses are always valid JSON."""
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)): return float(o) if np.isfinite(o) else None
    return o

def job_for(r):
    j = jobs.get_done(r.job_id)
    if not j: raise HTTPException(422, "Fetch job not found or not finished.")
    if j["variable"] != r.variable: raise HTTPException(422, "This fetch job was for a different variable. Fetch the data again.")
    if j["kind"] == "point" and (abs(j["lat"] - r.lat) > 1e-3 or abs(j["lon"] - r.lon) > 1e-3): raise HTTPException(422, "This fetch job was for a different location. Fetch the data again.")
    return j

def load(r, var):
    if r.end_year - r.start_year < 9: raise HTTPException(422, "Use at least 10 years of data.")
    poly = poly_of(r); ctx = dict(info=None, quality=None, area=None, unit=var["unit"])
    try:
        if r.source == "demo":
            if poly:
                t, m, v, ctx["area"] = gridded.cube_series(gridded.simulate_cube(var, geo.bbox(poly), r.start_year, r.end_year), poly)
            else: t, m, v = simulate(var, r.lat, r.lon, r.start_year, r.end_year)
        elif r.source == "csv":
            p = ingest.parse_table(r.csv_text, r.date_col, r.value_col, r.qc_col, r.qc_max, r.scale, r.offset, r.fill_value)
            ctx["quality"] = p["report"]
            if r.aggregate == "none": t, m, v = p["t"], p["months"], p["values"]
            else: t, m, v, ctx["info"] = aggregate.to_monthly(p["years"], p["months"], p["values"], r.aggregate)
        else:
            j = job_for(r)
            if j["kind"] == "cube":
                t, m, v, ctx["area"] = gridded.cube_series(j["cube"], poly); ctx["unit"] = j["cube"].unit
            else:
                res = j["result"]; p = jobs.arrays(res); ctx["quality"] = res["report"]; ctx["unit"] = res["meta"]["unit"]
                if r.aggregate == "none": t, m, v = p["t"], p["months"], p["values"]
                else: t, m, v, ctx["info"] = aggregate.to_monthly(p["years"], p["months"], p["values"], r.aggregate)
    except ValueError as e:
        raise HTTPException(422, str(e))
    k = (t >= r.start_year) & (t < r.end_year + 1)
    if k.sum() < 24: raise HTTPException(422, "Need at least 24 valid observations in the selected period.")
    return t[k], m[k], v[k], ctx

def analyse(r):
    var = catalog.get(r.variable)
    if not var: raise HTTPException(404, "Unknown variable")
    t, m, v, ctx = load(r, var)
    y = stats.deseasonalize(m, v) if r.deseasonalize else v
    o, k = stats.ols(t, y), stats.mann_kendall(t, y); raw = stats.ols(t, v)
    sk = stats.seasonal_mann_kendall(m, t, v)
    use = sk if (r.test == "seasonal" and sk) else k
    return clean(dict(
        variable=var["name"], unit=ctx["unit"], dataset=var["source"], n=len(t), alpha=r.alpha,
        data_origin={"demo": "SIMULATED demo series (not NASA measurements)", "csv": "user-imported CSV",
                     "job": "NASA live fetch"}[r.source],
        series=[dict(t=float(a), v=float(b)) for a, b in zip(t, v)],
        ols=dict(slope_per_decade=o["slope"]*10, ci95_per_decade=o["ci95"]*10, r2=o["r2"], intercept=o["intercept"],
                 slope_raw=raw["slope"], intercept_raw=raw["intercept"]),
        sen_per_decade=(use["sen"] if "sen" in use else k["sen"])*10,
        mann_kendall=dict(S=k["S"], z=k["z"], p=k["p"], tau=k["tau"], lag1=k["lag1"]),
        seasonal_mk=sk, test_used="Seasonal Mann-Kendall" if use is sk and sk else "Mann-Kendall (lag-1 adjusted)",
        deseasonalized=r.deseasonalize, aggregation=ctx["info"], data_quality=ctx["quality"], area=ctx["area"],
        verdict=stats.verdict(len(t), use["p"], use["S"], r.alpha),
        seasonal_cycle=[float(v[m == i].mean()) if (m == i).any() else None for i in range(12)],
        caveat="A non-significant result does not prove that no change exists; association is not causation."))

def get_cube(r, var):
    poly = poly_of(r)
    if r.source == "demo":
        box = geo.bbox(poly) if poly else (r.lat - 1, r.lon - 1, r.lat + 1, r.lon + 1)
        return gridded.simulate_cube(var, box, r.start_year, r.end_year), poly, "SIMULATED demo grid (not NASA measurements)"
    j = job_for(r) if r.source == "job" else None
    if j and j["kind"] == "cube": return j["cube"], poly, "NASA GES DISC gridded data"
    raise HTTPException(422, "Pixel maps need gridded data: use the simulated source or a NASA GES DISC fetch (pr, sm, ro, et).")

def grid_analysis(r):
    var = catalog.get(r.variable)
    if not var: raise HTTPException(404, "Unknown variable")
    cube, poly, origin = get_cube(r, var)
    mask = geo.polygon_mask(cube.lats, cube.lons, poly) if poly else np.ones((len(cube.lats), len(cube.lons)), bool)
    sel = (cube.t >= r.start_year) & (cube.t < r.end_year + 1)
    yrs, mon, data = cube.years[sel], cube.months[sel], cube.data[sel]
    years = np.unique(yrs); cells, ps = [], []
    for i in range(len(cube.lats)):
        for j in range(len(cube.lons)):
            if not mask[i, j]: continue
            x = data[:, i, j]; ok = ~np.isnan(x)
            if ok.sum() < 0.7 * len(x) or ok.sum() < 60: continue
            a = stats.deseasonalize(mon[ok], x[ok]); yy = yrs[ok]
            ann = [(y, a[yy == y].mean()) for y in years if (yy == y).sum() >= 6]
            if len(ann) < 10: continue
            ay, av = np.array([q[0] for q in ann], float), np.array([q[1] for q in ann])
            k = stats.mann_kendall(ay, av, sen=False)
            cells.append(dict(row=i, col=j, lat=float(cube.lats[i]), lon=float(cube.lons[j]), slope_per_decade=stats.ols(ay, av)["slope"]*10, p=k["p"])); ps.append(k["p"])
    if not cells: raise HTTPException(422, "No grid cells with enough valid data in this area and period.")
    sig = stats.benjamini_hochberg(ps, r.alpha)
    for c, s in zip(cells, sig): c["significant_fdr"] = bool(s)
    sl = [c["slope_per_decade"] for c in cells]
    dlat = float(abs(np.diff(cube.lats)[0])) if len(cube.lats) > 1 else .25; dlon = float(abs(np.diff(cube.lons)[0])) if len(cube.lons) > 1 else .25
    return clean(dict(cells=cells, nrows=len(cube.lats), ncols=len(cube.lons), dlat=dlat, dlon=dlon, opposite_trends=bool(min(sl) < 0 < max(sl)),
                n_significant=int(sig.sum()), n_tested=len(cells), data_origin=origin, unit=cube.unit))

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
def products():
    return dict(appeears={k: dict(product=v["product"], layer=v["layer"], unit=v["unit"]) for k, v in PRODUCTS.items()},
                gesdisc={k: dict(product=v["short_name"], layer=v["var"], unit=v["unit"]) for k, v in GRID_PRODUCTS.items()})

@app.post("/api/data/fetch")
def data_fetch(r: FetchReq, bg: BackgroundTasks):
    avail = PRODUCTS if r.connector == "appeears" else GRID_PRODUCTS
    if r.variable not in avail: raise HTTPException(422, f"{r.connector} has no connector for '{r.variable}'. Available: {', '.join(avail)}.")
    try: poly = geo.check_polygon(r.polygon)
    except ValueError as e: raise HTTPException(422, str(e))
    if r.connector == "appeears": poly = None  # point sampling only
    jid = jobs.create(r.connector, r.variable, r.lat, r.lon, r.start_year, r.end_year, poly)
    bg.add_task(jobs.run, jid, r.connector, r.variable, r.lat, r.lon, r.start_year, r.end_year, poly)
    return dict(job_id=jid, status=jobs.JOBS[jid]["status"])

@app.get("/api/data/status/{jid}")
def data_status(jid: str):
    j = jobs.JOBS.get(jid)
    if not j: raise HTTPException(404, "Unknown job")
    return dict(job_id=jid, status=j["status"], progress=j["progress"], message=j["message"], cached=j["cached"], kind=j["kind"], connector=j["connector"])

@app.get("/api/discover")
def discover(q: str = Query(..., min_length=2, max_length=100), limit: int = Query(10, ge=1, le=25)):
    try: return search_collections(q, limit)
    except Exception as e: raise HTTPException(502, f"CMR search failed: {e}")

@app.post("/api/reports/pdf")
def pdf(r: PdfReq):
    res = analyse(r); sp = grid_analysis(r) if r.include_map else None
    data = report.build_pdf(res, sp, r.model_dump())
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="kalyx-report.pdf"'})
