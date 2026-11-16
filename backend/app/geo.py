"""Polygon masks and area-weighted averaging on regular lat/lon grids."""
import numpy as np

def bbox(poly):
    la = [p[0] for p in poly]; lo = [p[1] for p in poly]
    return min(la), min(lo), max(la), max(lo)  # south, west, north, east

def check_polygon(poly):
    if poly is None: return None
    if len(poly) < 3: raise ValueError("A polygon needs at least 3 vertices.")
    if any(len(v) != 2 for v in poly): raise ValueError("Each polygon vertex must be [latitude, longitude].")
    for la, lo in poly:
        if not (-90 <= la <= 90 and -180 <= lo <= 180): raise ValueError("Polygon vertex outside valid latitude/longitude range.")
    s, w, n, e = bbox(poly)
    if n - s > 20 or e - w > 20: raise ValueError("Area too large: keep the polygon within 20 degrees in each direction.")
    return [(float(a), float(b)) for a, b in poly]

def polygon_mask(lats, lons, poly):
    """True where a cell centre lies inside the polygon (ray casting). Falls back to the nearest cell for tiny polygons."""
    LA, LO = np.meshgrid(lats, lons, indexing="ij"); inside = np.zeros(LA.shape, bool)
    for i in range(len(poly)):
        y1, x1 = poly[i]; y2, x2 = poly[(i + 1) % len(poly)]
        inside ^= ((y1 > LA) != (y2 > LA)) & (LO < (x2 - x1) * (LA - y1) / (y2 - y1 + 1e-300) + x1)
    if not inside.any():
        cy = np.mean([p[0] for p in poly]); cx = np.mean([p[1] for p in poly])
        inside[np.abs(lats - cy).argmin(), np.abs(lons - cx).argmin()] = True
    return inside

def area_average(data, lats, mask):
    """Area-weighted (cos latitude) mean of data[time, lat, lon] over mask; NaN cells are ignored per time step."""
    w = (np.cos(np.radians(lats))[:, None] * np.ones((1, data.shape[2]))) * mask
    valid = ~np.isnan(data); W = w[None] * valid
    num = (np.where(valid, data, 0) * W).sum(axis=(1, 2)); den = W.sum(axis=(1, 2))
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
