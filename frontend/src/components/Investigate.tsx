import { useEffect, useRef, useState } from "react";
import { downloadPdf, getCatalog, getProducts, getRegions, jobStatus, runSpatial, runTrend, startFetch,
  type JobStatus, type Params, type Region, type Spatial, type Trend, type Variable } from "../api";
import Chart from "./Chart";
import CsvPicker from "./CsvPicker";
import MapPicker from "./MapPicker";

export default function Investigate({ initialVar }: { initialVar?: string }) {
  const [vars, setVars] = useState<Variable[]>([]); const [regions, setRegions] = useState<Region[]>([]); const [live, setLive] = useState<string[]>([]);
  const [p, setP] = useState<Params>({ variable: initialVar || "lst", lat: 22.8, lon: 86.2, start_year: 2001, end_year: 2025, alpha: 0.05,
    deseasonalize: true, test: "mk", source: "demo", scale: 1, offset: 0, aggregate: "mean" });
  const [pixel, setPixel] = useState(false); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [trend, setTrend] = useState<Trend | null>(null); const [sp, setSp] = useState<Spatial | null>(null); const [job, setJob] = useState<JobStatus | null>(null);
  const timer = useRef<number>();
  useEffect(() => { getCatalog().then(setVars).catch(e => setErr(e.message)); getRegions().then(setRegions).catch(() => {}); getProducts().then(x => setLive(Object.keys(x))).catch(() => {}); return () => clearInterval(timer.current); }, []);
  useEffect(() => { if (initialVar) setP(s => ({ ...s, variable: initialVar })); }, [initialVar]);
  const set = <K extends keyof Params>(k: K, v: Params[K]) => setP(s => ({ ...s, [k]: v }));
  const guard = async (f: () => Promise<void>) => { setBusy(true); setErr(""); try { await f(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } };

  const fetchLive = () => guard(async () => {
    const { job_id } = await startFetch(p); set("job_id", job_id); setJob({ job_id, status: "queued", progress: 0, message: "Queued", cached: false });
    clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try { const s = await jobStatus(job_id); setJob(s); if (s.status === "done" || s.status === "error") { clearInterval(timer.current); if (s.status === "error") setErr(s.message); } }
      catch (e) { clearInterval(timer.current); setErr((e as Error).message); }
    }, 3000);
  });
  const run = () => guard(async () => {
    setSp(null); setTrend(await runTrend(p));
    if (pixel && p.source === "demo") setSp(await runSpatial(p));
  });
  const copy = (txt: string) => navigator.clipboard?.writeText(txt);
  const csv = () => trend ? "t,value\n" + trend.series.map(s => `${s.t.toFixed(3)},${s.v.toFixed(4)}`).join("\n") : "";
  const maxS = sp ? Math.max(...sp.cells.map(c => Math.abs(c.slope_per_decade))) || 1 : 1;
  const v = vars.find(x => x.id === p.variable);
  const canRun = p.source === "demo" || (p.source === "csv" && !!p.csv_text) || (p.source === "job" && job?.status === "done");

  return (
    <div className="grid2">
      <aside className="panel">
        <h4>Variable</h4>
        <select value={p.variable} onChange={e => set("variable", e.target.value)}>{vars.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        {v && <p className="note">{v.source} · {v.spatial} · {v.temporal} · {v.unit}</p>}
        <h4>Location</h4>
        <select onChange={e => { const r = regions.find(x => x.id === e.target.value); if (r) setP(s => ({ ...s, lat: r.lat, lon: r.lon })); }}><option value="">Preset region</option>{regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
        <div className="row"><label>Latitude<input type="number" step="any" value={p.lat} onChange={e => set("lat", +e.target.value)} /></label><label>Longitude<input type="number" step="any" value={p.lon} onChange={e => set("lon", +e.target.value)} /></label></div>
        <h4>Period and method</h4>
        <div className="row"><label>Start<input type="number" value={p.start_year} onChange={e => set("start_year", +e.target.value)} /></label><label>End<input type="number" value={p.end_year} onChange={e => set("end_year", +e.target.value)} /></label></div>
        <label>Significance level<select value={p.alpha} onChange={e => set("alpha", +e.target.value)}><option>0.05</option><option>0.01</option><option>0.1</option></select></label>
        <label>Trend test for verdict<select value={p.test} onChange={e => set("test", e.target.value as Params["test"])}><option value="mk">Mann-Kendall (lag-1 adjusted)</option><option value="seasonal">Seasonal Mann-Kendall</option></select></label>
        <label>Monthly aggregation<select value={p.aggregate} onChange={e => set("aggregate", e.target.value as Params["aggregate"])}><option value="mean">Mean (temperature, indices)</option><option value="sum">Sum (precipitation accumulation)</option><option value="none">None (use as given)</option></select></label>
        <label className="chk"><input type="checkbox" checked={p.deseasonalize} onChange={e => set("deseasonalize", e.target.checked)} /> Remove seasonal cycle</label>
        <label className="chk"><input type="checkbox" checked={pixel} onChange={e => setPixel(e.target.checked)} /> Pixel map with FDR (demo only)</label>
        <h4>Data source</h4>
        <select value={p.source} onChange={e => set("source", e.target.value as Params["source"])}><option value="demo">Simulated demo series</option><option value="csv">Imported CSV</option><option value="job">NASA AppEEARS (live)</option></select>
        {p.source === "csv" && <CsvPicker p={p} set={set} />}
        {p.source === "job" && <>
          {!live.includes(p.variable) && <p className="note">No live connector for this variable. Live: {live.join(", ") || "none"}.</p>}
          <button className="btn" disabled={busy || !live.includes(p.variable)} onClick={fetchLive}>Fetch from AppEEARS</button>
          {job && <div className="note" role="status"><div className="bar"><i style={{ width: `${job.progress}%` }} /></div>{job.status}: {job.message}{job.cached ? " (cache)" : ""}</div>}
          <p className="note">Needs EARTHDATA_USER and EARTHDATA_PASS set on the backend. Tasks can take minutes.</p></>}
        <button className="btn solid" onClick={run} disabled={busy || !canRun}>{busy ? "Working…" : "Run analysis"}</button>
        {err && <p className="err" role="alert">{err}</p>}
      </aside>
      <div>
        <div className="panel"><h4>Region map (NASA GIBS)</h4><MapPicker lat={p.lat} lon={p.lon} onPick={(la, lo) => setP(s => ({ ...s, lat: la, lon: lo }))} /></div>
        {!trend && <div className="panel empty">Choose a variable, click the map, then run the analysis.</div>}
        {trend && <>
          <div className="verdict"><h3>{trend.verdict}</h3><p>{trend.ols.slope_per_decade.toFixed(3)} {trend.unit} per decade (95% interval ±{trend.ols.ci95_per_decade.toFixed(3)}). {trend.test_used}: p = {(trend.test_used.startsWith("Seasonal") && trend.seasonal_mk ? trend.seasonal_mk.p : trend.mann_kendall.p).toFixed(4)}. {trend.caveat}</p></div>
          <div className="kpis">
            <div><span>OLS / decade</span><b>{trend.ols.slope_per_decade.toFixed(3)}</b></div>
            <div><span>Sen's slope / decade</span><b>{trend.sen_per_decade.toFixed(3)}</b></div>
            <div><span>MK Z / seasonal Z</span><b>{trend.mann_kendall.z.toFixed(2)} / {trend.seasonal_mk ? trend.seasonal_mk.z.toFixed(2) : "n/a"}</b></div>
            <div><span>Months / lag-1</span><b>{trend.n} / {trend.mann_kendall.lag1.toFixed(2)}</b></div>
          </div>
          {(trend.aggregation || trend.data_quality) && <div className="panel note">
            {trend.aggregation && <>Aggregation: {trend.aggregation.method} of {trend.aggregation.n_input} observations into {trend.aggregation.n_months} months ({trend.aggregation.missing_months} missing, {trend.aggregation.mean_obs_per_month.toFixed(1)} obs/month). {trend.aggregation.warning}<br /></>}
            {trend.data_quality && <>Quality: {trend.data_quality.valid}/{trend.data_quality.rows} rows valid ({(trend.data_quality.valid_fraction * 100).toFixed(0)}%); dropped {trend.data_quality.unparsable} unparsable, {trend.data_quality.fill} fill, {trend.data_quality.quality} low quality.</>}</div>}
          <div className="panel"><h4>{trend.variable}</h4><Chart d={trend} /><p className="note">{trend.data_origin} · {trend.dataset}</p></div>
          {sp && <div className="panel"><h4>Trend map, {sp.grid}×{sp.grid} cells</h4>
            <svg viewBox={`0 0 ${sp.grid * 20} ${sp.grid * 20}`} style={{ maxWidth: 360 }}>{sp.cells.map((c, i) => <rect key={i} x={c.col * 20} y={c.row * 20} width="19" height="19" fill={`rgba(${c.slope_per_decade > 0 ? "255,120,90" : "105,213,232"},${(.15 + .85 * Math.abs(c.slope_per_decade) / maxS).toFixed(2)})`} stroke={c.significant_fdr ? "#fff" : "none"} strokeWidth="1.2"><title>{c.slope_per_decade.toFixed(3)} per decade, p={c.p.toFixed(3)}</title></rect>)}</svg>
            <p className="note">Warm: increasing. Cyan: decreasing. Outline: significant after Benjamini-Hochberg. {sp.n_significant} cells significant. {sp.opposite_trends ? "Opposite trends occur inside this region." : "All cells share one direction."} {sp.data_origin}</p></div>}
          <div className="row actions"><button className="btn" onClick={() => copy(csv())}>Copy CSV</button><button className="btn" onClick={() => copy(JSON.stringify({ ...trend, series: undefined }, null, 2))}>Copy JSON</button>
            <button className="btn solid" disabled={busy} onClick={() => guard(() => downloadPdf(p, !!sp))}>Download PDF report</button></div>
        </>}
      </div>
    </div>
  );
}
