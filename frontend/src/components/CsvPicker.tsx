import { useState } from "react";
import { inspectCsv, type Inspect, type Params } from "../api";

export default function CsvPicker({ p, set }: { p: Params; set: <K extends keyof Params>(k: K, v: Params[K]) => void }) {
  const [info, setInfo] = useState<Inspect | null>(null); const [err, setErr] = useState("");
  const load = async (text: string) => {
    set("csv_text", text); setErr("");
    try {
      const i = await inspectCsv(text); setInfo(i);
      set("date_col", i.date_col ?? undefined); set("value_col", i.value_col ?? undefined); set("qc_col", i.qc_col ?? undefined);
      set("qc_max", i.qc_col ? 1 : undefined);
    } catch (e) { setErr((e as Error).message); }
  };
  const cols = info?.columns ?? [];
  const num = (k: "scale" | "offset" | "fill_value" | "qc_max") => (e: React.ChangeEvent<HTMLInputElement>) =>
    set(k as keyof Params, (e.target.value === "" ? undefined : +e.target.value) as never);
  return (<>
    <input type="file" accept=".csv,.txt,.tsv" onChange={async e => { const f = e.target.files?.[0]; if (f) load(await f.text()); }} />
    <textarea rows={3} placeholder="Or paste CSV here" value={p.csv_text ?? ""} onBlur={e => e.target.value && load(e.target.value)} onChange={e => set("csv_text", e.target.value)} />
    {err && <p className="err">{err}</p>}
    {info && cols.length > 0 && <>
      <p className="note">{info.n_rows} rows detected. Check the columns:</p>
      <label>Date column<select value={p.date_col ?? ""} onChange={e => set("date_col", e.target.value)}>{cols.map(c => <option key={c}>{c}</option>)}</select></label>
      <label>Value column<select value={p.value_col ?? ""} onChange={e => set("value_col", e.target.value)}>{cols.map(c => <option key={c}>{c}</option>)}</select></label>
      <label>Quality column (optional)<select value={p.qc_col ?? ""} onChange={e => set("qc_col", e.target.value || undefined)}><option value="">None</option>{cols.map(c => <option key={c}>{c}</option>)}</select></label>
      {p.qc_col && <label>Keep quality value up to (MODIS: 1)<input type="number" value={p.qc_max ?? ""} onChange={num("qc_max")} /></label>}
      <div className="row"><label>Scale factor<input type="number" step="any" value={p.scale} onChange={e => set("scale", +e.target.value || 1)} /></label><label>Offset<input type="number" step="any" value={p.offset} onChange={e => set("offset", +e.target.value || 0)} /></label></div>
      <label>Fill value to drop (optional)<input type="number" step="any" value={p.fill_value ?? ""} onChange={num("fill_value")} /></label>
      <div className="preview"><table><thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{info.preview.map((r, i) => <tr key={i}>{cols.map(c => <td key={c}>{r[c]}</td>)}</tr>)}</tbody></table></div>
    </>}
  </>);
}
