import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import NumInput from "../components/NumInput";
import Investigate from "../components/Investigate";
import Chart from "../components/Chart";
import MediaHolder from "../components/MediaHolder";
import Learn from "../components/Learn";
import { runTrend } from "../api";
import type { Trend } from "../api";

vi.mock("../components/MapPicker", () => ({ default: () => <div data-testid="map" /> }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const TREND: Trend = {
  variable: "Land Surface Temperature", unit: "°C", dataset: "MODIS", n: 300, data_origin: "SIMULATED demo series", verdict: "Significant increasing trend",
  caveat: "caveat", test_used: "Mann-Kendall (lag-1 adjusted)", series: Array.from({ length: 24 }, (_, i) => ({ t: 2001 + i / 12, v: 20 + i * .1 })),
  ols: { slope_per_decade: 0.35, ci95_per_decade: 0.1, intercept: 1, r2: .5, slope_raw: .03, intercept_raw: 1 }, sen_per_decade: .34,
  mann_kendall: { S: 10, z: 3, p: .002, tau: .5, lag1: .1 }, seasonal_mk: null, aggregation: null, data_quality: null, seasonal_cycle: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], area: null };

function mockApi(trendStatus = 200) {
  const calls: { url: string; body?: any }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: any) => {
    const body = init?.body ? JSON.parse(init.body) : undefined; calls.push({ url, body });
    const ok = (d: unknown, status = 200) => ({ ok: status < 400, status, json: async () => d, blob: async () => new Blob(["x"]) });
    if (url === "/api/catalog") return ok([{ id: "lst", name: "Land Surface Temperature", category: "Temperature", unit: "°C", source: "MODIS", spatial: "1 km", temporal: "8-day", coverage: "2000-" }]);
    if (url === "/api/regions") return ok([{ id: "r", name: "Basin", lat: 22.8, lon: 86.2 }]);
    if (url === "/api/data/products") return ok({ appeears: { lst: { product: "x", layer: "y", unit: "°C" } }, gesdisc: { pr: { product: "x", layer: "y", unit: "mm" } } });
    if (url === "/api/analysis/trend") return trendStatus === 200 ? ok(TREND) : ok({ detail: [{ loc: ["body", "alpha"], msg: "bad alpha" }] }, trendStatus);
    return ok({});
  }));
  return calls;
}

describe("NumInput", () => {
  it("accepts partial and negative decimals while typing", () => {
    const seen: (number | undefined)[] = []; render(<NumInput value={1} label="n" onChange={v => seen.push(v)} />);
    const el = screen.getByLabelText("n") as HTMLInputElement;
    for (const t of ["-", "-2", "-273.15", "0.", "0.02"]) fireEvent.change(el, { target: { value: t } });
    expect(el.value).toBe("0.02"); expect(seen).toContain(-273.15); expect(seen).toContain(0.02); expect(seen.some(v => Number.isNaN(v as number))).toBe(false);
  });
  it("only reports empty when allowed", () => {
    const a = vi.fn(); const { unmount } = render(<NumInput value={5} label="a" onChange={a} />);
    fireEvent.change(screen.getByLabelText("a"), { target: { value: "" } }); expect(a).not.toHaveBeenCalled(); unmount();
    const b = vi.fn(); render(<NumInput value={5} label="b" allowEmpty onChange={b} />);
    fireEvent.change(screen.getByLabelText("b"), { target: { value: "" } }); expect(b).toHaveBeenCalledWith(undefined);
  });
  it("follows external changes", () => {
    const { rerender } = render(<NumInput value={1} label="n" onChange={() => {}} />);
    rerender(<NumInput value={22.8} label="n" onChange={() => {}} />); expect((screen.getByLabelText("n") as HTMLInputElement).value).toBe("22.8");
  });
});

describe("api errors", () => {
  it("formats FastAPI validation errors", async () => {
    mockApi(422);
    await expect(runTrend({ variable: "lst", lat: 1, lon: 1, start_year: 2001, end_year: 2020, alpha: 9, deseasonalize: true, test: "mk", source: "demo", scale: 1, offset: 0, aggregate: "mean" })).rejects.toThrow("alpha: bad alpha");
  });
});

describe("Investigate", () => {
  it("runs an analysis and shows the verdict, then clears nothing it should keep", async () => {
    const calls = mockApi(); render(<Investigate />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Land Surface Temperature" })).toBeTruthy());
    fireEvent.click(screen.getByText("Run analysis"));
    await waitFor(() => expect(screen.getByText("Significant increasing trend")).toBeTruthy());
    const call = calls.find(c => c.url === "/api/analysis/trend")!; expect(call.body.source).toBe("demo"); expect(call.body.lat).toBe(22.8);
    expect(screen.getByText("Download PDF report")).toBeTruthy();
  });
  it("shows API errors", async () => {
    mockApi(422); render(<Investigate />); await waitFor(() => screen.getByText("Run analysis"));
    fireEvent.click(screen.getByText("Run analysis")); await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("bad alpha"));
  });
  it("blocks a live-source run until data is fetched", async () => {
    mockApi(); render(<Investigate />); await waitFor(() => screen.getByText("Run analysis"));
    fireEvent.change(screen.getByDisplayValue("Simulated demo (point or area)"), { target: { value: "gesdisc" } });
    expect((screen.getByText("Run analysis") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/No gesdisc connector for this variable/)).toBeTruthy();
  });
  it("drops a fetched job when the variable or place changes", async () => {
    const calls = mockApi(); render(<Investigate />); await waitFor(() => screen.getByText("Run analysis"));
    fireEvent.change(screen.getByDisplayValue("Simulated demo (point or area)"), { target: { value: "appeears" } });
    calls.length = 0; (globalThis.fetch as any).mockImplementation(async (url: string, init?: any) => {
      calls.push({ url, body: init?.body ? JSON.parse(init.body) : undefined });
      const ok = (d: unknown) => ({ ok: true, status: 200, json: async () => d });
      if (url === "/api/data/fetch") return ok({ job_id: "j1" });
      if (url.startsWith("/api/data/status")) return ok({ job_id: "j1", status: "done", progress: 100, message: "Done", cached: false, kind: "point", connector: "appeears" });
      return ok({});
    });
    fireEvent.click(screen.getByText("Fetch from AppEEARS"));
    await waitFor(() => expect((screen.getByText("Run analysis") as HTMLButtonElement).disabled).toBe(false), { timeout: 5000 });
    fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "30" } });
    await waitFor(() => expect((screen.getByText("Run analysis") as HTMLButtonElement).disabled).toBe(true));
  });
  it("lets a user type a negative latitude", async () => {
    mockApi(); render(<Investigate />); await waitFor(() => screen.getByText("Run analysis"));
    const lat = screen.getByLabelText("Latitude") as HTMLInputElement; fireEvent.change(lat, { target: { value: "-" } }); fireEvent.change(lat, { target: { value: "-3.5" } });
    expect(lat.value).toBe("-3.5");
  });
});

describe("static components", () => {
  it("draws the chart", () => { const { container } = render(<Chart d={TREND} />); expect(container.querySelector("polyline")).toBeTruthy(); });
  it("chart survives a flat series", () => { const { container } = render(<Chart d={{ ...TREND, series: TREND.series.map(s => ({ ...s, v: 5 })) }} />); expect(container.innerHTML).not.toContain("NaN"); });
  it("media holder falls back when files are missing", () => {
    const { container } = render(<MediaHolder name="hero" />);
    const img = container.querySelector("img")!; const vid = container.querySelector("video")!; fireEvent.error(img); fireEvent.error(vid);
    expect(container.querySelector("img")).toBeNull(); expect(container.querySelector("video")).toBeNull(); expect(container.querySelector(".holder")).toBeTruthy();
  });
  it("renders the Learn guide", () => { render(<Learn />); expect(document.querySelectorAll("details").length).toBe(14); });
});
