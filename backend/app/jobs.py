"""Background fetch jobs (point = AppEEARS, cube = GES DISC) with an in-memory registry and on-disk cache."""
import hashlib, json, os, uuid
from pathlib import Path
import numpy as np
from . import geo, gridded, ingest
from .connectors import CONNECTORS, GRID_PRODUCTS, PRODUCTS
from .connectors.appeears import column_names

CACHE = Path(os.environ.get("KALYX_CACHE") or Path(__file__).resolve().parent.parent / "data_cache")
JOBS = {}

def box_for(lat, lon, poly):
    return geo.bbox(poly) if poly else (lat - .5, lon - .5, lat + .5, lon + .5)

def key(conn, var, lat, lon, y0, y1, poly):
    b = [round(x, 3) for x in box_for(lat, lon, poly)]
    return hashlib.sha1(f"{conn}|{var}|{b}|{y0}|{y1}".encode()).hexdigest()[:16]

def _trim(keep=30):
    """Bound memory: drop the oldest finished jobs (cubes can be large)."""
    for k in [k for k, j in JOBS.items() if j["status"] in ("done", "error")][:-keep] if len(JOBS) > keep else []:
        JOBS.pop(k, None)

def get_done(jid):
    j = JOBS.get(jid or "")
    return j if j and j["status"] == "done" else None

def arrays(res): return {k: np.array(res[k]) for k in ("years", "months", "t", "values")}

def create(conn, var, lat, lon, y0, y1, poly=None):
    _trim()
    k = key(conn, var, lat, lon, y0, y1, poly); jid = uuid.uuid4().hex[:12]
    kind = "cube" if conn == "gesdisc" else "point"
    j = dict(status="queued", progress=0, message="Queued", kind=kind, key=k, connector=conn, variable=var, lat=lat, lon=lon, result=None, cube=None, cached=False)
    f = CACHE / (k + (".npz" if kind == "cube" else ".json"))
    if f.exists():
        if kind == "cube": j["cube"] = gridded.load(f)
        else: j["result"] = json.loads(f.read_text())
        j.update(status="done", progress=100, message="Loaded from cache", cached=True)
    JOBS[jid] = j; return jid

def run(jid, conn, var, lat, lon, y0, y1, poly=None):
    j = JOBS[jid]
    if j["status"] == "done": return
    def prog(p, m): j.update(status="running", progress=p, message=m)
    try:
        prog(1, "Starting"); CACHE.mkdir(parents=True, exist_ok=True)
        if conn == "appeears":
            spec = PRODUCTS[var]; text = CONNECTORS["appeears"].fetch_csv(spec, lat, lon, y0, y1, prog)
            v, q = column_names(text, spec)
            if not v: raise RuntimeError("Expected data column not found in the AppEEARS results.")
            p = ingest.parse_table(text, "Date", v, q, spec["qc_max"], spec["scale"], spec["offset"], spec["fill"])
            res = dict(years=p["years"].tolist(), months=p["months"].tolist(), t=p["t"].tolist(), values=p["values"].tolist(), report=p["report"],
                       meta=dict(product=spec["product"], layer=spec["layer"], unit=spec["unit"], lat=lat, lon=lon, source="NASA AppEEARS", aggregate=spec["aggregate"]))
            (CACHE / f"{j['key']}.json").write_text(json.dumps(res)); j["result"] = res
        else:
            spec = GRID_PRODUCTS[var]; cube = CONNECTORS["gesdisc"].fetch_cube(spec, box_for(lat, lon, poly), y0, y1, prog)
            gridded.save(cube, CACHE / f"{j['key']}.npz"); j["cube"] = cube
        j.update(status="done", progress=100, message="Done")
    except Exception as e:  # surfaced to the UI
        j.update(status="error", message=str(e))
