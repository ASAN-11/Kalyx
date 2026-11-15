"""Trend statistics: OLS, Mann-Kendall (autocorrelation-adjusted), Sen's slope, Benjamini-Hochberg."""
import numpy as np
from scipy import stats

def deseasonalize(months, y):
    out = np.asarray(y, float).copy()
    for m in range(12):
        k = months == m
        if k.any(): out[k] -= out[k].mean()
    return out

def ols(x, y):
    r = stats.linregress(x, y)
    tcrit = stats.t.ppf(0.975, len(x) - 2)
    return dict(slope=r.slope, intercept=r.intercept, ci95=tcrit * r.stderr, r2=r.rvalue**2, p=r.pvalue)

def lag1(y):
    d = y - y.mean(); den = (d**2).sum()
    return float((d[1:] * d[:-1]).sum() / den) if den else 0.0

def mann_kendall(x, y, adjust=True, sen=True):
    x, y = np.asarray(x, float), np.asarray(y, float); n = len(y)
    S = float(np.triu(np.sign(y[None, :] - y[:, None]), 1).sum())
    _, ties = np.unique(y, return_counts=True)
    var = (n*(n-1)*(2*n+5) - (ties*(ties-1)*(2*ties+5)).sum()) / 18
    r = lag1(y)
    if adjust and r > 0:
        var *= min((1 + r) / (1 - r), 6.0)  # effective-sample-size style inflation for positive autocorrelation
    z = 0.0 if S == 0 else (S - np.sign(S)) / np.sqrt(var)
    out = dict(S=S, z=float(z), p=float(2 * (1 - stats.norm.cdf(abs(z)))), tau=S / (n*(n-1)/2), lag1=r)
    if sen:
        i, j = np.triu_indices(n, 1); dx = x[j] - x[i]; k = dx != 0
        out["sen"] = float(np.median((y[j][k] - y[i][k]) / dx[k]))
    return out

def benjamini_hochberg(p, alpha):
    p = np.asarray(p); n = len(p); order = np.argsort(p)
    ok = p[order] <= alpha * (np.arange(1, n+1) / n)
    sig = np.zeros(n, bool)
    if ok.any(): sig[order[: np.max(np.nonzero(ok)[0]) + 1]] = True
    return sig

def verdict(n, p, S, alpha):
    if n < 60: return "Insufficient data"
    d = "increasing" if S > 0 else "decreasing"
    return f"Significant {d} trend" if p < alpha else f"{d.capitalize()} but not statistically significant"

def seasonal_mann_kendall(months, t, y, min_per_season=3):
    """Hirsch seasonal Mann-Kendall: S and variance summed over the 12 calendar months."""
    months, t, y = np.asarray(months), np.asarray(t, float), np.asarray(y, float)
    S = var = 0.0; slopes = []; used = 0
    for k in range(12):
        s = months == k; yk, tk = y[s], t[s]; n = len(yk)
        if n < min_per_season: continue
        used += 1
        S += np.triu(np.sign(yk[None, :] - yk[:, None]), 1).sum()
        _, c = np.unique(yk, return_counts=True)
        var += (n*(n-1)*(2*n+5) - (c*(c-1)*(2*c+5)).sum()) / 18
        i, j = np.triu_indices(n, 1); dx = tk[j] - tk[i]; ok = dx != 0
        slopes.append((yk[j][ok] - yk[i][ok]) / dx[ok])
    if used == 0 or var <= 0: return None
    z = 0.0 if S == 0 else (S - np.sign(S)) / np.sqrt(var)
    return dict(S=float(S), z=float(z), p=float(2 * (1 - stats.norm.cdf(abs(z)))),
                sen=float(np.median(np.concatenate(slopes))), seasons_used=used)
