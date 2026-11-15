"""Background fetch jobs with an in-memory registry and an on-disk cache."""
import hashlib, json, os, uuid
from pathlib import Path
import numpy as np
from . import ingest
from .connectors import CONNECTORS, PRODUCTS
from .connectors.appeears import column_names

CACHE = Path(os.environ.get("KALYX_CACHE", Path(__file__).resolve().parent.parent / "data_cache"))
JOBS = {}

def key(var, lat, lon, y0, y1): return hashlib.sha1(f"{var}|{lat:.4f}|{lon:.4f}|{y0}|{y1}".encode()).hexdigest()[:16]

def _result(parsed, meta):
    return dict(years=parsed["years"].tolist(), months=parsed["months"].tolist(), t=parsed["t"].tolist(),
                values=parsed["values"].tolist(), report=parsed["report"], meta=meta)

def get_result(job_id):
    j = JOBS.get(job_id)
    return j["result"] if j and j["status"] == "done" else None

def arrays(res): return {k: np.array(res[k]) for k in ("years", "months", "t", "values")}

def create(var, lat, lon, y0, y1):
    k = key(var, lat, lon, y0, y1); jid = uuid.uuid4().hex[:12]
    f = CACHE / f"{k}.json"
    if f.exists():
        JOBS[jid] = dict(status="done", progress=100, message="Loaded from cache", result=json.loads(f.read_text()), cached=True)
    else:
        JOBS[jid] = dict(status="queued", progress=0, message="Queued", result=None, key=k)
    return jid

def run(jid, var, lat, lon, y0, y1):
    j = JOBS[jid]
    if j["status"] == "done": return
    def prog(p, m): j.update(status="running", progress=p, message=m)
    try:
        spec = PRODUCTS[var]; prog(1, "Starting")
        text = CONNECTORS["appeears"].fetch_csv(spec, lat, lon, y0, y1, prog)
        v, q = column_names(text, spec)
        if not v: raise RuntimeError("Expected data column not found in the AppEEARS results.")
        parsed = ingest.parse_table(text, "Date", v, q, spec["qc_max"], spec["scale"], spec["offset"], spec["fill"])
        meta = dict(product=spec["product"], layer=spec["layer"], unit=spec["unit"], lat=lat, lon=lon, source="NASA AppEEARS",
                    scale=spec["scale"], offset=spec["offset"], aggregate=spec["aggregate"])
        res = _result(parsed, meta); CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{j['key']}.json").write_text(json.dumps(res))
        j.update(status="done", progress=100, message="Done", result=res)
    except Exception as e:  # surfaced to the UI
        j.update(status="error", message=str(e))
