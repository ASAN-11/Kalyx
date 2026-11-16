import numpy as np
from fastapi.testclient import TestClient
from app import stats
from app.main import app

def test_detects_clear_trend():
    x = np.arange(240) / 12; y = 0.5 * x + np.random.default_rng(1).normal(0, .5, 240)
    k = stats.mann_kendall(x, y)
    assert k["p"] < 0.001 and abs(k["sen"] - 0.5) < 0.05
    assert abs(stats.ols(x, y)["slope"] - 0.5) < 0.05

def test_no_trend_not_significant():
    x = np.arange(240) / 12; y = np.random.default_rng(2).normal(0, 1, 240)
    assert stats.mann_kendall(x, y)["p"] > 0.01

def test_bh():
    assert stats.benjamini_hochberg(np.array([.001, .009, .04, .5, .9]), .05).tolist() == [True, True, False, False, False]

def test_api():
    c = TestClient(app)
    r = c.post("/api/analysis/trend", json=dict(variable="lst", lat=22.8, lon=86.2)).json()
    assert "verdict" in r and r["n"] == 300
    s = c.post("/api/analysis/spatial", json=dict(variable="lst", lat=22.8, lon=86.2)).json()
    assert len(s["cells"]) > 4 and "lat" in s["cells"][0]
