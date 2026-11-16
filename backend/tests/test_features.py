import numpy as np
from fastapi.testclient import TestClient
from app import aggregate, ingest, jobs, stats
from app.main import app
from app.connectors import CONNECTORS
from app.connectors import cmr
c = TestClient(app)

GIOVANNI = """Title,Time Series, Area-Averaged
Units,mm/hr
time,mean_GPM_3IMERGM_07_precipitation
2001-01-01T00:00:00Z,0.1
2001-02-01T00:00:00Z,0.2
2001-03-01T00:00:00Z,0.3
"""
APPEEARS = "ID,Latitude,Longitude,Date,MOD11A2_061_LST_Day_1km,MOD11A2_061_QC_Day\n" + "\n".join(
    f"0,22.8,86.2,{2001+i//46}-{1+(i%46)//4:02d}-{1+(i%4)*7:02d},{15000+i if i%9 else 0},{0 if i%7 else 2}" for i in range(46*10))

def test_inspect_giovanni():
    g = ingest.inspect_csv(GIOVANNI)
    assert g["date_col"] == "time" and g["value_col"].startswith("mean_") and g["n_rows"] == 3

def test_parse_scale_fill_quality():
    p = ingest.parse_table(APPEEARS, "Date", "MOD11A2_061_LST_Day_1km", "MOD11A2_061_QC_Day", 1, .02, -273.15, 0)
    r = p["report"]; assert r["fill"] > 0 and r["quality"] > 0 and r["valid"] < r["rows"]
    assert 20 < p["values"].mean() < 40  # 0.02 * ~15000 - 273.15 ~ 27 C

def test_monthly_aggregation():
    t, m, v, info = aggregate.to_monthly([2001]*4, [0, 0, 1, 1], [1, 3, 5, 7], "mean")
    assert v.tolist() == [2, 6] and info["n_months"] == 2
    assert aggregate.to_monthly([2001]*2, [0, 0], [1, 3], "sum")[2].tolist() == [4]

def test_seasonal_mk_detects_trend_and_ignores_season():
    n = 20; t = np.repeat(np.arange(n), 12) + np.tile(np.arange(12), n) / 12; m = np.tile(np.arange(12), n)
    rng = np.random.default_rng(3)
    y = 10*np.cos(m*np.pi/6) + .3*t + rng.normal(0, .5, len(t))
    r = stats.seasonal_mann_kendall(m, t, y); assert r["p"] < 1e-6 and abs(r["sen"] - .3) < .1
    flat = 10*np.cos(m*np.pi/6) + rng.normal(0, .5, len(t)); assert stats.seasonal_mann_kendall(m, t, flat)["p"] > .01

def test_api_csv_with_picker_and_seasonal():
    n = 15; rows = ["time,val,qa"] + [f"{2001+i}-{j+1:02d}-15,{20+.1*i+5*np.sin(j)},0" for i in range(n) for j in range(12)]
    b = dict(variable="lst", lat=1, lon=1, start_year=2001, end_year=2015, source="csv", csv_text="\n".join(rows),
             date_col="time", value_col="val", qc_col="qa", qc_max=1, test="seasonal")
    r = c.post("/api/analysis/trend", json=b).json()
    assert r["test_used"] == "Seasonal Mann-Kendall" and r["seasonal_mk"]["p"] < .001 and r["aggregation"]["n_months"] == 180
    bad = c.post("/api/analysis/trend", json={**b, "value_col": "nope"}); assert bad.status_code == 422

def test_job_flow_with_fake_connector(tmp_path, monkeypatch):
    class Fake:
        def fetch_csv(self, spec, lat, lon, y0, y1, progress): progress(50, "half"); return APPEEARS
    monkeypatch.setitem(CONNECTORS, "appeears", Fake()); monkeypatch.setattr(jobs, "CACHE", tmp_path)
    r = c.post("/api/data/fetch", json=dict(variable="lst", lat=22.8, lon=86.2, start_year=2001, end_year=2010)).json()
    s = c.get(f"/api/data/status/{r['job_id']}").json(); assert s["status"] == "done"
    a = c.post("/api/analysis/trend", json=dict(variable="lst", lat=22.8, lon=86.2, start_year=2001, end_year=2010, source="job", job_id=r["job_id"])).json()
    assert a["data_origin"] == "NASA live fetch"
    r2 = c.post("/api/data/fetch", json=dict(variable="lst", lat=22.8, lon=86.2, start_year=2001, end_year=2010)).json()
    assert c.get(f"/api/data/status/{r2['job_id']}").json()["cached"] is True
    assert c.post("/api/data/fetch", json=dict(variable="pr", lat=1, lon=1, connector="appeears")).status_code == 422

def test_missing_credentials_message(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "CACHE", tmp_path); monkeypatch.delenv("EARTHDATA_USER", raising=False)
    j = jobs.create("appeears", "lst", 5.0, 5.0, 2001, 2002); jobs.JOBS[j]["key"] = "x"
    jobs.run(j, "appeears", "lst", 5.0, 5.0, 2001, 2002)
    assert jobs.JOBS[j]["status"] == "error" and "EARTHDATA_USER" in jobs.JOBS[j]["message"]

def test_cmr_parse():
    class R:
        def raise_for_status(self): pass
        def json(self): return {"feed": {"entry": [{"id": "C1", "title": "GPM IMERG", "short_name": "GPM_3IMERGM", "version_id": "07", "data_center": "GES_DISC", "summary": "x"}]}}
    class S:
        def get(self, *a, **k): return R()
    assert cmr.search_collections("imerg", session=S())[0]["short_name"] == "GPM_3IMERGM"

def test_pdf():
    r = c.post("/api/reports/pdf", json=dict(variable="pr", lat=22.8, lon=86.2, include_map=True, test="seasonal"))
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 20000
