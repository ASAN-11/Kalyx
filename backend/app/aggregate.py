"""Temporal aggregation of irregular or sub-monthly observations (e.g. 8-day MODIS composites) to monthly values."""
import numpy as np

def to_monthly(years, months, values, method="mean"):
    years, months, values = (np.asarray(a) for a in (years, months, values))
    keys = years.astype(int) * 12 + months.astype(int)
    uniq, inv = np.unique(keys, return_inverse=True)
    cnt = np.bincount(inv); tot = np.bincount(inv, weights=values)
    out = tot / cnt if method == "mean" else tot
    yr, mo = uniq // 12, uniq % 12
    span = int(uniq[-1] - uniq[0] + 1)
    info = dict(method=method, n_input=int(len(values)), n_months=int(len(uniq)), missing_months=span - len(uniq),
                mean_obs_per_month=float(cnt.mean()))
    if method == "sum":
        info["warning"] = "Monthly sums assume complete coverage within each month; months with missing observations are underestimated."
    return yr + mo / 12, mo, out, info
