"""NASA AppEEARS point-sample connector (MODIS). Needs EARTHDATA_USER / EARTHDATA_PASS in the environment.
NOTE: written against the public AppEEARS API docs; verify product/layer names and bundle file names against
https://appeears.earthdatacloud.nasa.gov/api/ before relying on it."""
import os, time
import requests

API = "https://appeears.earthdatacloud.nasa.gov/api"
# QC: MODIS QC bits 0-1 -> 0 good, 1 other quality; values >1 are cloud/no-data and are dropped (qc_max=1)
PRODUCTS = {
    "lst": dict(product="MOD11A2.061", layer="LST_Day_1km", qc="QC_Day", scale=0.02, offset=-273.15, fill=0, qc_max=1, aggregate="mean", unit="°C"),
    "ndvi": dict(product="MOD13Q1.061", layer="_250m_16_days_NDVI", qc="_250m_16_days_pixel_reliability", scale=0.0001, offset=0.0, fill=-3000, qc_max=1, aggregate="mean", unit="index"),
}

class AppEEARS:
    def __init__(self, session=None, poll=10, timeout=1800):
        self.s = session or requests.Session(); self.poll = poll; self.timeout = timeout

    def _headers(self):
        u, p = os.environ.get("EARTHDATA_USER"), os.environ.get("EARTHDATA_PASS")
        if not u or not p: raise RuntimeError("Set EARTHDATA_USER and EARTHDATA_PASS environment variables on the backend.")
        r = self.s.post(f"{API}/login", auth=(u, p), timeout=30)
        if r.status_code in (401, 403): raise RuntimeError("Earthdata login was rejected.")
        r.raise_for_status()
        return {"Authorization": "Bearer " + r.json()["token"]}

    def fetch_csv(self, spec, lat, lon, y0, y1, progress=lambda pct, msg: None):
        h = self._headers(); progress(5, "Logged in to AppEEARS")
        layers = [dict(product=spec["product"], layer=spec["layer"])] + ([dict(product=spec["product"], layer=spec["qc"])] if spec.get("qc") else [])
        task = dict(task_type="point", task_name=f"kalyx_{int(time.time())}", params=dict(
            dates=[dict(startDate=f"01-01-{y0}", endDate=f"12-31-{y1}")], layers=layers,
            coordinates=[dict(id="0", longitude=lon, latitude=lat, category="kalyx")]))
        r = self.s.post(f"{API}/task", json=task, headers=h, timeout=60); r.raise_for_status()
        tid = r.json()["task_id"]; progress(15, "Task submitted"); start = time.time()
        while True:
            st = self.s.get(f"{API}/task/{tid}", headers=h, timeout=30); st.raise_for_status(); st = st.json()
            status = st.get("status")
            if status == "done": break
            if status in ("error", "deleted"): raise RuntimeError(f"AppEEARS task ended with status '{status}'.")
            if time.time() - start > self.timeout: raise RuntimeError("AppEEARS task timed out.")
            progress(min(80, 15 + int((time.time() - start) / self.timeout * 65)), f"AppEEARS status: {status}")
            time.sleep(self.poll)
        files = self.s.get(f"{API}/bundle/{tid}", headers=h, timeout=30); files.raise_for_status()
        f = next((x for x in files.json()["files"] if x["file_name"].lower().endswith("results.csv")), None)
        if not f: raise RuntimeError("AppEEARS bundle has no results CSV.")
        progress(90, "Downloading results")
        d = self.s.get(f"{API}/bundle/{tid}/{f['file_id']}", headers=h, timeout=300); d.raise_for_status()
        return d.text

def column_names(csv_text, spec):
    """AppEEARS names columns like MOD11A2_061_LST_Day_1km; match by layer suffix."""
    from ..ingest import inspect_csv
    cols = inspect_csv(csv_text)["columns"]
    v = next((c for c in cols if c.endswith(spec["layer"])), None)
    q = next((c for c in cols if spec.get("qc") and c.endswith(spec["qc"])), None)
    return v, q
