import { useEffect, useState } from "react";
/** Numeric text field that keeps what the user types ("-", "0.", "0.02") and reports only valid numbers. */
export default function NumInput({ value, onChange, allowEmpty = false, label }: { value: number | undefined; onChange: (v: number | undefined) => void; allowEmpty?: boolean; label?: string }) {
  const show = (v: number | undefined) => (v === undefined ? "" : String(v));
  const [txt, setTxt] = useState(show(value));
  useEffect(() => { if (txt.trim() === "" ? value !== undefined : Number(txt) !== value) setTxt(show(value)); }, [value]); // external change (e.g. map click)
  return <input type="text" inputMode="decimal" aria-label={label} value={txt} onChange={e => {
    const t = e.target.value; setTxt(t);
    if (t.trim() === "") { if (allowEmpty) onChange(undefined); return; }
    const n = Number(t); if (Number.isFinite(n)) onChange(n);
  }} />;
}
