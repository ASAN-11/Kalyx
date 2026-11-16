import numpy as np
from fastapi.testclient import TestClient
from app import ingest, jobs, stats
from app.connectors import CONNECTORS
from app.main import app
c = TestClient(app)
B = dict(variable="lst", lat=22.8, lon=86.2)

def test_nan_and_inf_values_are_dropped_not_crashing():
    rows = ["date,v"] + [f"{2001+i//12}-{i%12+1:02d}-15,{'nan' if i%50==0 else 'inf' if i%77==0 else 20+i*.01}" for i in range(240)]
    p = ingest.parse_table("\n".join(rows)); assert np.isfinite(p["values"]).all() and p["report"]["unparsable"] > 0
    r = c.post("/api/analysis/trend", json={**B, "source": "csv", "csv_text": "\n".join(rows), "start_year": 2001, "end_year": 2020})
    assert r.status_code == 200

def test_constant_series_gives_valid_json_and_no_trend():
    rows = ["date,v"] + [f"{2001+i//12}-{i%12+1:02d}-15,5.0" for i in range(240)]
    r = c.post("/api/analysis/trend", json={**B, "source": "csv", "csv_text": "\n".join(rows), "start_year": 2001, "end_year": 2020})
    assert r.status_code == 200 and r.json()["verdict"].startswith("No trend")

def test_verdict_zero_s():
    assert stats.verdict(100, 1.0, 0, .05).startswith("No trend")

def test_request_validation():
    assert c.post("/api/analysis/trend", json={**B, "alpha": 5}).status_code == 422
    assert c.post("/api/analysis/trend", json={**B, "start_year": 1, "end_year": 99999999}).status_code == 422
    assert c.post("/api/analysis/trend", json={**B, "polygon": [[0, 0, 5], [1, 1, 5], [2, 2, 5]]}).status_code == 422
    assert c.get("/api/discover?q=a").status_code == 422

def test_job_variable_mismatch_rejected(monkeypatch, tmp_path):
    csv = "ID,Latitude,Longitude,Date,MOD11A2_061_LST_Day_1km,MOD11A2_061_QC_Day\n" + "\n".join(f"0,22.8,86.2,{2001+i//12}-{i%12+1:02d}-10,{15000+i},0" for i in range(240))
    class Fake:
        def fetch_csv(self, *a, **k): return csv
    monkeypatch.setitem(CONNECTORS, "appeears", Fake()); monkeypatch.setattr(jobs, "CACHE", tmp_path)
    j = c.post("/api/data/fetch", json=dict(**B, start_year=2001, end_year=2020)).json()["job_id"]
    ok = c.post("/api/analysis/trend", json={**B, "source": "job", "job_id": j, "start_year": 2001, "end_year": 2020}); assert ok.status_code == 200
    assert c.post("/api/analysis/trend", json={**B, "variable": "ndvi", "source": "job", "job_id": j}).status_code == 422
    assert c.post("/api/analysis/trend", json={**B, "lat": 30, "source": "job", "job_id": j}).status_code == 422

def test_job_registry_is_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "CACHE", tmp_path)
    for i in range(60):
        k = jobs.create("appeears", "lst", float(i), 0.0, 2001, 2010); jobs.JOBS[k]["status"] = "done"
    assert len(jobs.JOBS) <= 31
