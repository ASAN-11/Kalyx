import numpy as np, xarray as xr, pandas as pd
from fastapi.testclient import TestClient
from app import geo, gridded, jobs, stats
from app.connectors import CONNECTORS
from app.connectors.gesdisc import PRODUCTS as GP
from app.main import app
c = TestClient(app)
POLY = [[22.0, 85.5], [22.0, 87.0], [23.5, 87.0], [23.5, 85.5]]

def test_polygon_mask_and_fallback():
    lats = np.arange(20.125, 25, .25); lons = np.arange(84.125, 89, .25)
    m = geo.polygon_mask(lats, lons, POLY)
    assert m.any() and not m.all() and lats[np.nonzero(m.any(1))[0]].min() >= 22 - 1e-9
    tiny = geo.polygon_mask(lats, lons, [[22.01, 85.01], [22.02, 85.01], [22.02, 85.02]])
    assert tiny.sum() == 1

def test_polygon_validation():
    assert c.post("/api/analysis/trend", json=dict(variable="lst", lat=1, lon=1, polygon=[[0, 0], [1, 1]])).status_code == 422
    assert c.post("/api/analysis/trend", json=dict(variable="lst", lat=1, lon=1, polygon=[[0, 0], [0, 40], [40, 40]])).status_code == 422

def test_area_weighting():
    lats = np.array([0., 60.]); data = np.array([[[10.], [20.]]])
    v = geo.area_average(data, lats, np.ones((2, 1), bool))
    assert abs(v[0] - (10 * 1 + 20 * .5) / 1.5) < 1e-9  # cos(60) = 0.5

def test_area_average_ignores_nan():
    data = np.array([[[1., np.nan], [3., 5.]]]); v = geo.area_average(data, np.array([0., 0.]), np.ones((2, 2), bool))
    assert abs(v[0] - 3.0) < 1e-9

def test_demo_area_analysis_and_pixel_map():
    b = dict(variable="lst", lat=22.8, lon=86.2, polygon=POLY, test="seasonal")
    a = c.post("/api/analysis/trend", json=b).json(); assert a["area"]["n_cells"] > 4 and a["n"] == 300
    s = c.post("/api/analysis/spatial", json=b).json()
    assert s["n_tested"] == len(s["cells"]) > 4 and s["dlat"] > 0 and all(geo_in(c_) for c_ in s["cells"])
    assert c.post("/api/analysis/spatial", json={**b, "source": "csv", "csv_text": "a"}).status_code == 422

def geo_in(cell): return 22 <= cell["lat"] <= 23.5 and 85.5 <= cell["lon"] <= 87

def synthetic_ds(descending=True):
    lat = np.arange(20.25, 25, .5)[::-1] if descending else np.arange(20.25, 25, .5); lon = np.arange(84.25, 89, .5)
    time = pd.date_range("2001-01-01", periods=240, freq="MS"); rng = np.random.default_rng(0)
    base = rng.normal(0, .1, (len(time), len(lon), len(lat)))
    return xr.Dataset({"precipitation": (("time", "lon", "lat"), base + 0.01)}, coords=dict(time=time, lon=lon, lat=lat))

def test_cube_from_dataset_conversion_and_subset():
    ds = synthetic_ds(); ds["precipitation"][:] = 0.01; cube = gridded.cube_from_dataset(ds, GP["pr"], (21.0, 85.0, 23.0, 87.0))
    assert cube.data.shape[0] == 240 and cube.lats[0] < cube.lats[-1] and cube.lats.min() >= 21 and cube.lons.max() <= 87
    assert abs(np.nanmean(cube.data[0]) - 0.01 * 24 * 31) < 1e-6  # mm/hr -> mm/month (January: 31 days)
    one = gridded.cube_from_dataset(ds, GP["pr"], (22.01, 85.01, 22.02, 85.02)); assert one.data.shape[1:] == (1, 1)

def test_per_cell_opposite_trends_detected_with_fdr(tmp_path, monkeypatch):
    ds = synthetic_ds(False); n = 240; ramp = np.linspace(0, 1, n)[:, None, None]
    sign = np.where(ds.lon.values[None, :, None] < 86.5, 1.0, -1.0)  # west rises, east falls
    ds["precipitation"] = ds["precipitation"] + sign * ramp * 0.15
    spec = dict(GP["pr"], per_day=None); cube = gridded.cube_from_dataset(ds, spec, (20, 84, 25, 89))
    class Fake:
        def fetch_cube(self, *a, **k): return cube
    monkeypatch.setitem(CONNECTORS, "gesdisc", Fake()); monkeypatch.setattr(jobs, "CACHE", tmp_path)
    if True:
        r = c.post("/api/data/fetch", json=dict(connector="gesdisc", variable="pr", lat=22.5, lon=86.5, polygon=[[20.5, 84.5], [20.5, 88.5], [24.5, 88.5], [24.5, 84.5]])).json()
        st = c.get(f"/api/data/status/{r['job_id']}").json(); assert st["status"] == "done" and st["kind"] == "cube"
        b = dict(variable="pr", lat=22.5, lon=86.5, source="job", job_id=r["job_id"], start_year=2001, end_year=2020,
                 polygon=[[20.5, 84.5], [20.5, 88.5], [24.5, 88.5], [24.5, 84.5]])
        sp = c.post("/api/analysis/spatial", json=b).json()
        assert sp["opposite_trends"] and sp["n_significant"] > 10 and sp["data_origin"] == "NASA GES DISC gridded data"
        a = c.post("/api/analysis/trend", json=b).json(); assert a["data_origin"] == "NASA live fetch" and a["area"]["n_cells"] > 10
        r2 = c.post("/api/data/fetch", json=dict(connector="gesdisc", variable="pr", lat=22.5, lon=86.5, polygon=b["polygon"])).json()
        assert c.get(f"/api/data/status/{r2['job_id']}").json()["cached"] is True
        assert c.post("/api/data/fetch", json=dict(connector="gesdisc", variable="lst", lat=1, lon=1)).status_code == 422

def test_gesdisc_without_extras_or_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "CACHE", tmp_path); monkeypatch.delenv("EARTHDATA_USER", raising=False)
    j = jobs.create("gesdisc", "sm", 22.5, 86.5, 2001, 2005); jobs.run(j, "gesdisc", "sm", 22.5, 86.5, 2001, 2005)
    assert jobs.JOBS[j]["status"] == "error" and ("EARTHDATA_USER" in jobs.JOBS[j]["message"] or "requirements-live" in jobs.JOBS[j]["message"])

def test_pdf_with_area_map():
    r = c.post("/api/reports/pdf", json=dict(variable="pr", lat=22.8, lon=86.2, polygon=POLY, include_map=True))
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
