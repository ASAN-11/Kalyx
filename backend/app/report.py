"""PDF scientific report (reportlab + matplotlib)."""
import io
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=160, bbox_inches="tight"); plt.close(fig); b.seek(0); return b

def _series_fig(res):
    t = np.array([s["t"] for s in res["series"]]); v = np.array([s["v"] for s in res["series"]])
    fig, ax = plt.subplots(figsize=(7.2, 2.8)); ax.plot(t, v, lw=.9, color="#1b8aa3", label="Observations")
    a = res["ols"]; ax.plot([t[0], t[-1]], [a["intercept_raw"] + a["slope_raw"] * t[0], a["intercept_raw"] + a["slope_raw"] * t[-1]], "--", color="k", label="Linear trend")
    ax.set_ylabel(res["unit"]); ax.legend(frameon=False, fontsize=8); ax.grid(alpha=.2); return _png(fig)

def _season_fig(res):
    fig, ax = plt.subplots(figsize=(3.4, 2.2)); c = [x if x is not None else np.nan for x in res["seasonal_cycle"]]
    ax.bar("JFMAMJJASOND", c, color="#1b8aa3"); ax.set_title("Seasonal cycle", fontsize=9); return _png(fig)

def _map_fig(sp):
    N = sp["grid"]; g = np.full((N, N), np.nan); sig = np.zeros((N, N), bool)
    for c in sp["cells"]: g[c["row"], c["col"]] = c["slope_per_decade"]; sig[c["row"], c["col"]] = c["significant_fdr"]
    m = np.nanmax(np.abs(g)) or 1; fig, ax = plt.subplots(figsize=(3.4, 3.2)); im = ax.imshow(g, cmap="RdBu_r", vmin=-m, vmax=m)
    ys, xs = np.nonzero(sig); ax.scatter(xs, ys, s=14, facecolors="none", edgecolors="k"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Trend per decade (circle = FDR-significant)", fontsize=8); fig.colorbar(im, fraction=.046); return _png(fig)

def build_pdf(res, spatial=None, params=None):
    S = getSampleStyleSheet(); body = S["BodyText"]; h = S["Heading2"]
    buf = io.BytesIO(); doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm, title="KALYX investigation report")
    mk, sm, ols = res["mann_kendall"], res.get("seasonal_mk"), res["ols"]; p = params or {}
    story = [Paragraph("KALYX Investigation Report", S["Title"]),
             Paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", body), Spacer(1, 6),
             Paragraph("1. Research question and setup", h),
             Paragraph(f"Is <b>{res['variable']}</b> changing at {p.get('lat')}, {p.get('lon')} between {p.get('start_year')} and {p.get('end_year')}?", body)]
    rows = [["Dataset", res["dataset"]], ["Data origin", res["data_origin"]], ["Observations (monthly)", str(res["n"])],
            ["Significance level", str(res["alpha"])], ["Test used for verdict", res["test_used"]],
            ["Seasonal cycle removed", "yes" if res["deseasonalized"] else "no"]]
    ag = res.get("aggregation")
    if ag: rows.append(["Aggregation", f"{ag['method']} of {ag['n_input']} observations into {ag['n_months']} months; {ag['missing_months']} months missing"])
    q = res.get("data_quality")
    if q: rows.append(["Data quality", f"{q['valid']} of {q['rows']} rows valid ({q['valid_fraction']*100:.0f}%); dropped: {q['unparsable']} unparsable, {q['fill']} fill, {q['quality']} low quality"])
    t = Table(rows, colWidths=[48*mm, 124*mm]); t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), .3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Paragraph("2. Finding", h), Paragraph(f"<b>{res['verdict']}</b>", body),
              Paragraph(f"Linear slope {ols['slope_per_decade']:+.4f} {res['unit']} per decade (95% interval +/-{ols['ci95_per_decade']:.4f}); Sen's slope {res['sen_per_decade']:+.4f} per decade. "
                        f"Mann-Kendall Z = {mk['z']:.2f}, p = {mk['p']:.4f}, lag-1 autocorrelation {mk['lag1']:.2f}."
                        + (f" Seasonal Mann-Kendall Z = {sm['z']:.2f}, p = {sm['p']:.4f} ({sm['seasons_used']} seasons)." if sm else ""), body),
              Paragraph("3. Time series", h), Image(_series_fig(res), width=172*mm, height=67*mm), Image(_season_fig(res), width=80*mm, height=52*mm)]
    if spatial: story += [Paragraph("4. Spatial trend map", h), Image(_map_fig(spatial), width=80*mm, height=75*mm),
                          Paragraph(f"{spatial['n_significant']} cells significant after Benjamini-Hochberg correction. "
                                    f"{'Opposite trends occur within the region.' if spatial['opposite_trends'] else 'All cells share one direction.'} {spatial['data_origin']}", body)]
    story += [Paragraph("5. Limitations", h), Paragraph(res["caveat"] + " Results depend on data quality filtering, aggregation and the record length. Statistical significance does not identify causes.", body)]
    if "SIMULATED" in res["data_origin"]: story += [Paragraph("<b>This report used simulated demonstration data, not NASA measurements.</b>", body)]
    story += [Paragraph("6. Method and references", h), Paragraph("Ordinary least squares; Mann-Kendall test with lag-1 variance adjustment; Sen's slope; seasonal Mann-Kendall (Hirsch); Benjamini-Hochberg false discovery rate. Cite the official DOI of the NASA dataset used.", body)]
    doc.build(story); return buf.getvalue()
