"""Gridded data cubes: simulation, conversion from xarray datasets (NASA GES DISC), and disk cache."""
import json
from dataclasses import dataclass
import numpy as np
from . import geo
from .demo import simulate

@dataclass
class Cube:
    years: np.ndarray; months: np.ndarray; lats: np.ndarray; lons: np.ndarray; data: np.ndarray; unit: str = ""; meta: dict = None

    @property
    def t(self): return self.years + self.months / 12

def save(c, path):
    np.savez_compressed(path, years=c.years, months=c.months, lats=c.lats, lons=c.lons, data=c.data, unit=c.unit, meta=json.dumps(c.meta or {}))

def load(path):
    z = np.load(path, allow_pickle=False)
    return Cube(z["years"], z["months"], z["lats"], z["lons"], z["data"], str(z["unit"]), json.loads(str(z["meta"])))

def simulate_cube(var, box, y0, y1):
    """SEEDED SIMULATION over a bounding box (south, west, north, east). Trend varies across space, so opposite signs can occur."""
    s, w, n, e = box; cell = max(.25, max(n - s, e - w) / 14)
    lats = np.arange(s + cell / 2, max(n, s + 2 * cell), cell); lons = np.arange(w + cell / 2, max(e, w + 2 * cell), cell)
    rng = np.random.default_rng(int(abs(s * 31 + w * 17)) + 5); amp = abs(var["trend"]) or .1
    t0 = None; out = np.zeros((0,))
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            g = (j / max(len(lons) - 1, 1) - .5) * 2 * amp * 1.3 + (rng.random() - .5) * amp
            t, m, v = simulate(var, float(la), float(lo), y0, y1, trend=g, seed_extra=i * 100 + j)
            if t0 is None: t0, m0 = t, m; out = np.zeros((len(t), len(lats), len(lons)))
            out[:, i, j] = v
    return Cube(np.floor(t0 + 1e-6).astype(int), m0, lats, lons, out, var["unit"], dict(simulated=True))

def cube_from_dataset(ds, spec, box):
    """Subset an xarray Dataset (dims time/lat/lon in any order) to box, convert rates to monthly totals if the spec asks."""
    import pandas as pd
    s, w, n, e = box; da = ds[spec["var"]].transpose("time", "lat", "lon")
    da = da.sortby("lat").sortby("lon"); sub = da.sel(lat=slice(s, n), lon=slice(w, e))
    if sub.lat.size == 0 or sub.lon.size == 0:
        sub = da.sel(lat=[(s + n) / 2], lon=[(w + e) / 2], method="nearest")
    sub = sub.sortby("time"); idx = sub.indexes["time"]
    if hasattr(idx, "to_datetimeindex"): idx = idx.to_datetimeindex()  # cftime calendars
    idx = pd.DatetimeIndex(idx); data = sub.values.astype(float)
    data[np.abs(data) > 1e15] = np.nan
    if spec.get("per_day"): data = data * spec["per_day"] * np.asarray(idx.days_in_month)[:, None, None]
    return Cube(np.asarray(idx.year), np.asarray(idx.month) - 1, sub.lat.values.astype(float), sub.lon.values.astype(float), data, spec["unit"],
                dict(source="NASA GES DISC", short_name=spec["short_name"], version=spec["version"], variable=spec["var"]))

def cube_series(cube, poly=None):
    mask = geo.polygon_mask(cube.lats, cube.lons, poly) if poly else np.ones((len(cube.lats), len(cube.lons)), bool)
    v = geo.area_average(cube.data, cube.lats, mask); ok = ~np.isnan(v)
    return cube.t[ok], cube.months[ok], v[ok], dict(n_cells=int(mask.sum()), weighting="cos(latitude) area weights",
        bbox=[float(cube.lats.min()), float(cube.lons.min()), float(cube.lats.max()), float(cube.lons.max())])
