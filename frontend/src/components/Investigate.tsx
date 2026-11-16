import { useEffect, useRef, useState } from "react";
import { downloadPdf, getCatalog, getProducts, getRegions, jobStatus, runSpatial, runTrend, startFetch,
  type Connector, type JobStatus, type Params, type Region, type Spatial, type Trend, type Variable } from "../api";
import Chart from "./Chart";
import CsvPicker from "./CsvPicker";
import MapPicker from "./MapPicker";
import NumInput from "./NumInput";

export default function Investigate({ initialVar }: { initialVar?: string }) {
  const [vars, setVars] = useState<Variable[]>([]); const [regions, setRegions] = useState<Region[]>([]); const [live, setLive] = useState<Record<Connector, string[]>>({ appeears: [], gesdisc: [] });
  const [src, setSrc] = useState<"demo" | "csv" | Connector>("demo");
  const [p, setP] = useState<Params>({ variable: initialVar || "lst", lat: 22.8, lon: 86.2, start_year: 2001, end_year: 2025, alpha: 0.05,
    deseasonalize: true, test: "mk", source: "demo", scale: 1, offset: 0, aggregate: "mean" });
  const [pixel, setPixel] = useState(false); const [note, setNote] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [trend, setTrend] = useState<Trend | null>(null); const [sp, setSp] = useState<Spatial | null>(null); const [job, setJob] = useState<JobStatus | null>(null);
  const timer = useRef<number>();
  useEffect(() => { getCatalog().then(setVars).catch(e => setErr(e.message)); getRegions().then(setRegions).catch(() => {}); getProducts().then(x => setLive({ appeears: Object.keys(x.appeears), gesdisc: Object.keys(x.gesdisc) })).catch(() => {}); return () => clearInterval(timer.current); }, []);
  useEffect(() => { if (initialVar) setP(s => ({ ...s, variable: initialVar })); }, [initialVar]);
  // A fetched dataset belongs to one variable, place and period: drop it when any of them changes.
  useEffect(() => { clearInterval(timer.current); setJob(null); setP(s => (s.job_id ? { ...s, job_id: undefined } : s)); },
    [p.variable, p.lat, p.lon, p.start_year, p.end_year, p.polygon]);
  const set = <K extends keyof Params>(k: K, v: Params[K]) => setP(s => ({ ...s, [k]: v }));
  const guard = async (f: () => Promise<void>) => { setBusy(true); setErr(""); try { await f(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } };

  const fetchLive = () => guard(async () => {
    const c = src as Connector; const { job_id } = await startFetch(p, c); set("job_id", job_id); setJob({ job_id, status: "queued", progress: 0, message: "Queued", cached: false, kind: c === "gesdisc" ? "cube" : "point", connector: c });
    clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try { const s = await jobStatus(job_id); setJob(s); if (s.status === "done" || s.status === "error") { clearInterval(timer.current); if (s.status === "error") setErr(s.message); } }
      catch (e) { clearInterval(timer.current); setErr((e as Error).message); }
    }, 3000);
  });
  const run = () => guard(async () => {
    setSp(null); setNote(""); setTrend(await runTrend(p));
    if (pixel) { if (src === "demo" || src === "gesdisc") setSp(await runSpatial(p)); else setNote("Pixel maps need gridded data: choose the simulated source or NASA GES DISC."); }
  });
  const copy = (txt: string) => navigator.clipboard?.writeText(txt);
  const csv = () => trend ? "t,value\n" + trend.series.map(s => `${s.t.toFixed(3)},${s.v.toFixed(4)}`).join("\n") : "";
  const maxS = sp ? Math.max(...sp.cells.map(c => Math.abs(c.slope_per_decade))) || 1 : 1;
  const v = vars.find(x => x.id === p.variable);
  const canRun = src === "demo" || (src === "csv" && !!p.csv_text) || (job?.status === "done" && job.connector === src);
  const chooseSrc = (x: typeof src) => { setSrc(x); setJob(null); setTrend(null); setSp(null); setP(s => ({ ...s, source: x === "demo" ? "demo" : x === "csv" ? "csv" : "job", job_id: undefined })); };

  return (
    <div className="grid2">
      <aside className="panel">
        <h4>Variable</h4>
        <select value={p.variable} onChange={e => set("variable", e.target.value)}>{vars.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        {v && <p className="note">{v.source} · {v.spatial} · {v.temporal} · {v.unit}</p>}
        <h4>Location</h4>
        <select onChange={e => { const r = regions.find(x => x.id === e.target.value); if (r) setP(s => ({ ...s, lat: r.lat, lon: r.lon })); }}><option value="">Preset region</option>{regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
        <div className="row"><label>Latitude<NumInput value={p.lat} label="Latitude" onChange={v => v !== undefined && v >= -90 && v <= 90 && set("lat", v)} /></label><label>Longitude<NumInput value={p.lon} label="Longitude" onChange={v => v !== undefined && v >= -180 && v <= 180 && set("lon", v)} /></label></div>
        <h4>Period and method</h4>
        <div className="row"><label>Start<NumInput value={p.start_year} label="Start year" onChange={v => v !== undefined && set("start_year", Math.round(v))} /></label><label>End<NumInput value={p.end_year} label="End year" onChange={v => v !== undefined && set("end_year", Math.round(v))} /></label></div>
        <label>Significance level<select value={p.alpha} onChange={e => set("alpha", +e.target.value)}><option>0.05</option><option>0.01</option><option>0.1</option></select></label>
        <label>Trend test for verdict<select value={p.test} onChange={e => set("test", e.target.value as Params["test"])}><option value="mk">Mann-Kendall (lag-1 adjusted)</option><option value="seasonal">Seasonal Mann-Kendall</option></select></label>
        <label>Monthly aggregation<select value={p.aggregate} onChange={e => set("aggregate", e.target.value as Params["aggregate"])}><option value="mean">Mean (temperature, indices)</option><option value="sum">Sum (precipitation accumulation)</option><option value="none">None (use as given)</option></select></label>
        <label className="chk"><input type="checkbox" checked={p.deseasonalize} onChange={e => set("deseasonalize", e.target.checked)} /> Remove seasonal cycle</label>
        <label className="chk"><input type="checkbox" checked={pixel} onChange={e => setPixel(e.target.checked)} /> Pixel trend map with FDR (gridded data)</label>
        <h4>Data source</h4>
        <select value={src} onChange={e => chooseSrc(e.target.value as typeof src)}><option value="demo">Simulated demo (point or area)</option><option value="csv">Imported CSV (point)</option><option value="appeears">NASA AppEEARS (point: lst, ndvi)</option><option value="gesdisc">NASA GES DISC (area grid: pr, sm, ro, et)</option></select>
        {src === "csv" && <CsvPicker p={p} set={set} />}
        {(src === "appeears" || src === "gesdisc") && <>
          {!live[src].includes(p.variable) && <p className="note">No {src} connector for this variable. Available: {live[src].join(", ") || "none"}.</p>}
          <button className="btn" disabled={busy || !live[src].includes(p.variable)} onClick={fetchLive}>Fetch from {src === "appeears" ? "AppEEARS" : "GES DISC"}</button>
          {job && <div className="note" role="status"><div className="bar"><i style={{ width: `${job.progress}%` }} /></div>{job.status}: {job.message}{job.cached ? " (cache)" : ""}</div>}
          <p className="note">{src === "gesdisc" ? "Uses your drawn area, or a 1°×1° box around the point. Needs requirements-live.txt and Earthdata credentials on the backend; large areas and periods are slow." : "Point sample. Needs EARTHDATA_USER and EARTHDATA_PASS on the backend."}</p></>}
        <button className="btn solid" onClick={run} disabled={busy || !canRun}>{busy ? "Working…" : "Run analysis"}</button>
        {err && <p className="err" role="alert">{err}</p>}
        {note && <p className="note">{note}</p>}
      </aside>
      <div>
        <div className="panel"><h4>Region map (NASA GIBS): point or drawn area</h4><MapPicker lat={p.lat} lon={p.lon} polygon={p.polygon} spatial={sp} onPick={(la, lo) => setP(s => ({ ...s, lat: la, lon: lo }))} onPolygon={pg => setP(s => ({ ...s, polygon: pg }))} /></div>
        {!trend && <div className="panel empty">Choose a variable, click the map, then run the analysis.</div>}
        {trend && <>
          <div className="verdict"><h3>{trend.verdict}</h3><p>{trend.ols.slope_per_decade.toFixed(3)} {trend.unit} per decade (95% interval ±{trend.ols.ci95_per_decade.toFixed(3)}). {trend.test_used}: p = {(trend.test_used.startsWith("Seasonal") && trend.seasonal_mk ? trend.seasonal_mk.p : trend.mann_kendall.p).toFixed(4)}. {trend.caveat}</p></div>
          <div className="kpis">
            <div><span>OLS / decade</span><b>{trend.ols.slope_per_decade.toFixed(3)}</b></div>
            <div><span>Sen's slope / decade</span><b>{trend.sen_per_decade.toFixed(3)}</b></div>
            <div><span>MK Z / seasonal Z</span><b>{trend.mann_kendall.z.toFixed(2)} / {trend.seasonal_mk ? trend.seasonal_mk.z.toFixed(2) : "n/a"}</b></div>
            <div><span>Months / lag-1</span><b>{trend.n} / {trend.mann_kendall.lag1.toFixed(2)}</b></div>
          </div>
          {(trend.aggregation || trend.data_quality || trend.area) && <div className="panel note">
            {trend.area && <>Spatial support: area average over {trend.area.n_cells} grid cells ({trend.area.weighting}).<br /></>}
            {trend.aggregation && <>Aggregation: {trend.aggregation.method} of {trend.aggregation.n_input} observations into {trend.aggregation.n_months} months ({trend.aggregation.missing_months} missing, {trend.aggregation.mean_obs_per_month.toFixed(1)} obs/month). {trend.aggregation.warning}<br /></>}
            {trend.data_quality && <>Quality: {trend.data_quality.valid}/{trend.data_quality.rows} rows valid ({(trend.data_quality.valid_fraction * 100).toFixed(0)}%); dropped {trend.data_quality.unparsable} unparsable, {trend.data_quality.fill} fill, {trend.data_quality.quality} low quality.</>}</div>}
          <div className="panel"><h4>{trend.variable}</h4><Chart d={trend} /><p className="note">{trend.data_origin} · {trend.dataset}</p></div>
          {sp && <div className="panel note"><b style={{ color: "#fff" }}>Pixel trend map (shown on the map above).</b> {sp.n_tested} cells tested; {sp.n_significant} significant after Benjamini-Hochberg (white outline). Warm cells increase, cyan cells decrease; opacity shows magnitude. {sp.opposite_trends ? "Opposite trends occur inside this area, so the area average hides real differences." : "All tested cells share one direction."} {sp.data_origin}.</div>}
          <div className="row actions"><button className="btn" onClick={() => copy(csv())}>Copy CSV</button><button className="btn" onClick={() => copy(JSON.stringify({ ...trend, series: undefined }, null, 2))}>Copy JSON</button>
            <button className="btn solid" disabled={busy} onClick={() => guard(() => downloadPdf(p, !!sp))}>Download PDF report</button></div>
        </>}
      </div>
    </div>
  );
}
