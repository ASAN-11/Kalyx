"""CSV inspection and parsing with a column picker, scale/offset, fill-value and quality filtering."""
import csv, io
from datetime import datetime
import numpy as np

FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m", "%Y%m%d")

def parse_date(s):
    s = (s or "").strip().strip('"').rstrip("Z")
    if not s: return None
    try: return datetime.fromisoformat(s)
    except ValueError: pass
    for f in FORMATS:
        try: return datetime.strptime(s, f)
        except ValueError: continue
    return None

def to_float(s):
    try: return float(str(s).strip())
    except ValueError: return None

def read_rows(text):
    lines = [l for l in (text or "").splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines: return []
    try: d = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t").delimiter
    except csv.Error: d = ","
    return [[c.strip() for c in r] for r in csv.reader(lines, delimiter=d)]

def split_header(rows):
    """Return (columns, data_rows). Works with/without a header and skips metadata lines above it."""
    if not rows: return [], []
    if any(parse_date(c) for c in rows[0]):
        return [f"col{i+1}" for i in range(len(rows[0]))], rows
    for i in range(len(rows) - 1):
        nxt = rows[i + 1]
        if len(rows[i]) >= 2 and len(rows[i]) == len(nxt) and any(parse_date(c) for c in nxt):
            return rows[i], rows[i + 1:]
    return [], []

def inspect_csv(text):
    cols, data = split_header(read_rows(text))
    if not cols: return dict(columns=[], preview=[], n_rows=0, date_col=None, value_col=None, qc_col=None)
    def frac(j, fn): return sum(fn(r[j]) is not None for r in data if j < len(r)) / max(len(data), 1)
    date_col = next((c for j, c in enumerate(cols) if frac(j, parse_date) > .8), None)
    nums = [c for j, c in enumerate(cols) if c != date_col and frac(j, to_float) > .8]
    qc = next((c for c in nums if "qc" in c.lower() or "quality" in c.lower()), None)
    val = next((c for c in nums if c != qc and c.lower() not in ("latitude", "longitude", "lat", "lon", "id")), None)
    return dict(columns=cols, preview=[dict(zip(cols, r)) for r in data[:5]], n_rows=len(data),
                date_col=date_col, value_col=val, qc_col=qc)

def parse_table(text, date_col=None, value_col=None, qc_col=None, qc_max=None, scale=1.0, offset=0.0, fill_value=None):
    cols, data = split_header(read_rows(text))
    if not cols: raise ValueError("Could not find a table with a date column in this CSV.")
    g = inspect_csv(text)
    date_col, value_col = date_col or g["date_col"], value_col or g["value_col"]
    for c in (date_col, value_col, qc_col):
        if c and c not in cols: raise ValueError(f"Column '{c}' not found. Available: {', '.join(cols)}")
    if not date_col or not value_col: raise ValueError("Choose a date column and a value column.")
    di, vi, qi = cols.index(date_col), cols.index(value_col), (cols.index(qc_col) if qc_col else None)
    yrs, mos, ts, vals = [], [], [], []
    rep = dict(rows=len(data), unparsable=0, fill=0, quality=0)
    for r in data:
        d = parse_date(r[di]) if di < len(r) else None; x = to_float(r[vi]) if vi < len(r) else None
        if d is None or x is None: rep["unparsable"] += 1; continue
        if fill_value is not None and x == fill_value: rep["fill"] += 1; continue
        if qi is not None and qc_max is not None:
            q = to_float(r[qi]) if qi < len(r) else None
            if q is None or (int(q) & 3) > qc_max: rep["quality"] += 1; continue
        yrs.append(d.year); mos.append(d.month - 1); ts.append(d.year + (d.timetuple().tm_yday - 1) / 365); vals.append(x * scale + offset)
    rep["valid"] = len(vals); rep["valid_fraction"] = len(vals) / max(len(data), 1)
    if not vals: raise ValueError("No valid observations after parsing and filtering.")
    o = np.argsort(ts)
    return dict(years=np.array(yrs)[o], months=np.array(mos)[o], t=np.array(ts)[o], values=np.array(vals)[o], report=rep)
