export type Variable = { id: string; name: string; category: string; unit: string; source: string; spatial: string; temporal: string; coverage: string };
export type Region = { id: string; name: string; lat: number; lon: number };
export type Params = {
  variable: string; lat: number; lon: number; start_year: number; end_year: number; alpha: number; deseasonalize: boolean;
  test: "mk" | "seasonal"; source: "demo" | "csv" | "job"; csv_text?: string; job_id?: string; polygon?: [number, number][];
  date_col?: string; value_col?: string; qc_col?: string; qc_max?: number; scale: number; offset: number; fill_value?: number;
  aggregate: "none" | "mean" | "sum";
};
export type Quality = { rows: number; valid: number; valid_fraction: number; unparsable: number; fill: number; quality: number };
export type Trend = {
  variable: string; unit: string; dataset: string; n: number; data_origin: string; verdict: string; caveat: string; test_used: string;
  series: { t: number; v: number }[];
  ols: { slope_per_decade: number; ci95_per_decade: number; intercept: number; r2: number; slope_raw: number; intercept_raw: number };
  sen_per_decade: number; mann_kendall: { S: number; z: number; p: number; tau: number; lag1: number };
  seasonal_mk: { z: number; p: number; sen: number; seasons_used: number } | null;
  aggregation: { method: string; n_input: number; n_months: number; missing_months: number; mean_obs_per_month: number; warning?: string } | null;
  data_quality: Quality | null; seasonal_cycle: (number | null)[];
  area: { n_cells: number; weighting: string; bbox: number[] } | null;
};
export type Cell = { row: number; col: number; lat: number; lon: number; slope_per_decade: number; p: number; significant_fdr: boolean };
export type Spatial = { nrows: number; ncols: number; dlat: number; dlon: number; opposite_trends: boolean; n_significant: number; n_tested: number; data_origin: string; unit: string; cells: Cell[] };
export type Inspect = { columns: string[]; preview: Record<string, string>[]; n_rows: number; date_col: string | null; value_col: string | null; qc_col: string | null };
export type JobStatus = { job_id: string; status: "queued" | "running" | "done" | "error"; progress: number; message: string; cached: boolean; kind: "point" | "cube"; connector: string };
export type Connector = "appeears" | "gesdisc";
export type Collection = { id: string; title: string; short_name: string; version: string; provider: string; start: string; end: string; summary: string; doi?: string };

async function req(url: string, body?: unknown): Promise<Response> {
  const r = await fetch(url, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    const d = e.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x: { loc?: (string | number)[]; msg?: string }) => `${(x.loc ?? []).slice(1).join(".")}: ${x.msg}`).join("; ") : `Request failed (${r.status})`;
    throw new Error(msg);
  }
  return r;
}
const call = async <T,>(url: string, body?: unknown) => (await req(url, body)).json() as Promise<T>;
export const getCatalog = () => call<Variable[]>("/api/catalog");
export const getRegions = () => call<Region[]>("/api/regions");
export const getProducts = () => call<Record<Connector, Record<string, { product: string; layer: string; unit: string }>>>("/api/data/products");
export const runTrend = (p: Params) => call<Trend>("/api/analysis/trend", p);
export const runSpatial = (p: Params) => call<Spatial>("/api/analysis/spatial", p);
export const inspectCsv = (csv_text: string) => call<Inspect>("/api/data/inspect", { csv_text });
export const startFetch = (p: Params, connector: Connector) => call<{ job_id: string }>("/api/data/fetch", { connector, variable: p.variable, lat: p.lat, lon: p.lon, start_year: p.start_year, end_year: p.end_year, polygon: p.polygon });
export const jobStatus = (id: string) => call<JobStatus>(`/api/data/status/${id}`);
export const discover = (q: string) => call<Collection[]>(`/api/discover?q=${encodeURIComponent(q)}`);
export async function downloadPdf(p: Params, includeMap: boolean) {
  const { csv_text, ...rest } = p; // csv is sent again so the report matches the analysis
  const blob = await (await req("/api/reports/pdf", { ...rest, csv_text, include_map: includeMap })).blob();
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "kalyx-report.pdf"; a.click(); URL.revokeObjectURL(a.href);
}
