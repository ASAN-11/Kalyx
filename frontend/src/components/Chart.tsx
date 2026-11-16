import type { Trend } from "../api";
export default function Chart({ d }: { d: Trend }) {
  const W = 900, H = 320, p = [56, 20, 20, 36];
  const xs = d.series.map(s => s.t), ys = d.series.map(s => s.v);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), pad = (y1 - y0) * .08 || 1;
  const sx = (t: number) => p[0] + (t - x0) / (x1 - x0) * (W - p[0] - p[1]);
  const sy = (v: number) => H - p[3] - (v - (y0 - pad)) / (y1 - y0 + 2 * pad) * (H - p[2] - p[3]);
  const n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = ys.reduce((a, b) => a + b) / n;
  let sxx = 0, sxy = 0; xs.forEach((x, i) => { sxx += (x - mx) ** 2; sxy += (x - mx) * (ys[i] - my); });
  const b = sxy / sxx, a = my - b * mx;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Time series of ${d.variable}`}>
      {[0, 1, 2, 3, 4].map(i => { const v = y0 - pad + (y1 - y0 + 2 * pad) * i / 4; return (<g key={i}><line x1={p[0]} x2={W - p[1]} y1={sy(v)} y2={sy(v)} stroke="#ffffff14" /><text x={p[0] - 6} y={sy(v) + 3} textAnchor="end" fontSize="10" fill="#9aa3a8">{v.toFixed(Math.abs(v) < 5 ? 2 : 0)}</text></g>); })}
      <polyline fill="none" stroke="#69D5E8" strokeWidth="1.2" points={d.series.map(s => `${sx(s.t).toFixed(1)},${sy(s.v).toFixed(1)}`).join(" ")} />
      <line x1={sx(x0)} x2={sx(x1)} y1={sy(a + b * x0)} y2={sy(a + b * x1)} stroke="#fff" strokeWidth="2" strokeDasharray="6 4" />
      <text x={p[0]} y="12" fontSize="10" fill="#9aa3a8">{d.unit} — cyan: observations, dashed: linear trend</text>
      {[x0, (x0 + x1) / 2, x1].map(t => <text key={t} x={sx(t)} y={H - 12} textAnchor="middle" fontSize="10" fill="#9aa3a8">{Math.round(t)}</text>)}
    </svg>
  );
}
