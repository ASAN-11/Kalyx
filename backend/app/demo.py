import numpy as np

def simulate(v, lat, lon, y0, y1, trend=None, seed_extra=0):
    """SEEDED SIMULATION, not NASA data. Demonstrates the pipeline."""
    rng = np.random.default_rng(abs(int(lat*977 + lon*131)) + len(v["id"])*7919 + seed_extra)
    trend = v["trend"] if trend is None else trend
    t, m, vals, e = [], [], [], 0.0
    for y in range(y0, y1 + 1):
        for mo in range(12):
            e = .5*e + rng.normal(0, v["noise"])
            seas = np.cos((mo - 6.5)*np.pi/6) * v["amp"] * (-1 if lat < 0 else 1)
            val = v["base"] + trend*(y + mo/12 - y0)/10 + seas*(.5 if v["id"] == "pr" else 1) + e
            if v["id"] == "pr": val = max(0.0, val + v["amp"]*.5)
            t.append(y + mo/12); m.append(mo); vals.append(val)
    return np.array(t), np.array(m), np.array(vals)
