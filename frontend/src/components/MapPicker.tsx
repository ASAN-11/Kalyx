import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Spatial } from "../api";

// NASA GIBS WMTS (EPSG:3857). Verify layer ids / max zoom at https://nasa-gibs.github.io/gibs-api-docs/
const LAYERS = {
  truecolor: { id: "MODIS_Terra_CorrectedReflectance_TrueColor", ext: "jpg", max: 9, time: true, label: "MODIS true colour" },
  lst: { id: "MODIS_Terra_Land_Surface_Temp_Day", ext: "png", max: 7, time: true, label: "MODIS land surface temp (day)" },
  blue: { id: "BlueMarble_ShadedRelief_Bathymetry", ext: "jpeg", max: 8, time: false, label: "Blue Marble" },
} as const;
type Key = keyof typeof LAYERS; type LL = [number, number];
const url = (k: Key, date: string) => { const l = LAYERS[k];
  return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${l.id}/default/${l.time ? date + "/" : ""}GoogleMapsCompatible_Level${l.max}/{z}/{y}/{x}.${l.ext}`; };
const isoDaysAgo = (d: number) => new Date(Date.now() - d * 864e5).toISOString().slice(0, 10);
const CY = "#69D5E8";

type Props = { lat: number; lon: number; polygon?: LL[]; onPick: (lat: number, lon: number) => void; onPolygon: (p?: LL[]) => void; spatial?: Spatial | null };

export default function MapPicker({ lat, lon, polygon, onPick, onPolygon, spatial }: Props) {
  const el = useRef<HTMLDivElement>(null); const map = useRef<L.Map>(); const tile = useRef<L.TileLayer>(); const dot = useRef<L.CircleMarker>();
  const polyLayer = useRef<L.LayerGroup>(); const draftLayer = useRef<L.LayerGroup>(); const cellLayer = useRef<L.LayerGroup>();
  const [layer, setLayer] = useState<Key>("truecolor"); const [date, setDate] = useState(isoDaysAgo(5));
  const [drawing, setDrawing] = useState(false); const [draft, setDraft] = useState<LL[]>([]);
  const cb = useRef({ onPick, drawing }); cb.current = { onPick, drawing };

  useEffect(() => {
    const m = L.map(el.current!, { center: [lat, lon], zoom: 6, minZoom: 2, worldCopyJump: true });
    m.on("click", e => {
      const ll: LL = [+e.latlng.lat.toFixed(3), +e.latlng.lng.toFixed(3)];
      if (cb.current.drawing) setDraft(d => [...d, ll]); else cb.current.onPick(ll[0], ll[1]);
    });
    polyLayer.current = L.layerGroup().addTo(m); draftLayer.current = L.layerGroup().addTo(m); cellLayer.current = L.layerGroup().addTo(m);
    dot.current = L.circleMarker([lat, lon], { radius: 6, color: CY, fillColor: CY, fillOpacity: .5 }).addTo(m);
    map.current = m; return () => { m.remove(); };
  }, []);
  useEffect(() => {
    tile.current?.remove();
    tile.current = L.tileLayer(url(layer, date), { maxNativeZoom: LAYERS[layer].max, maxZoom: 12, attribution: "Imagery: NASA GIBS / EOSDIS" }).addTo(map.current!);
    tile.current.bringToBack();
  }, [layer, date]);
  useEffect(() => { dot.current?.setLatLng([lat, lon]); }, [lat, lon]);
  useEffect(() => { const m = map.current; if (!m) return; if (drawing) m.doubleClickZoom.disable(); else m.doubleClickZoom.enable(); }, [drawing]);
  useEffect(() => {
    polyLayer.current?.clearLayers();
    if (polygon && polygon.length > 2) { const pg = L.polygon(polygon, { color: CY, weight: 2, fillOpacity: .08 }).addTo(polyLayer.current!); map.current?.fitBounds(pg.getBounds().pad(.3)); }
  }, [polygon]);
  useEffect(() => {
    draftLayer.current?.clearLayers(); if (!draft.length) return;
    L.polyline(draft, { color: "#fff", weight: 2, dashArray: "4 4" }).addTo(draftLayer.current!);
    draft.forEach(p => L.circleMarker(p, { radius: 4, color: "#fff", fillOpacity: 1 }).addTo(draftLayer.current!));
  }, [draft]);
  useEffect(() => {
    cellLayer.current?.clearLayers(); if (!spatial) return;
    const mx = Math.max(...spatial.cells.map(c => Math.abs(c.slope_per_decade))) || 1;
    spatial.cells.forEach(c => {
      const col = c.slope_per_decade > 0 ? "#ff785a" : CY;
      L.rectangle([[c.lat - spatial.dlat / 2, c.lon - spatial.dlon / 2], [c.lat + spatial.dlat / 2, c.lon + spatial.dlon / 2]],
        { stroke: c.significant_fdr, color: "#fff", weight: 1.5, fillColor: col, fillOpacity: .2 + .6 * Math.abs(c.slope_per_decade) / mx })
        .bindTooltip(`${c.slope_per_decade.toFixed(3)} ${spatial.unit}/decade · p=${c.p.toFixed(3)}${c.significant_fdr ? " · significant (FDR)" : ""}`).addTo(cellLayer.current!);
    });
  }, [spatial]);

  const finish = () => {
    if (draft.length < 3) return;
    onPolygon(draft); onPick(+(draft.reduce((a, p) => a + p[0], 0) / draft.length).toFixed(3), +(draft.reduce((a, p) => a + p[1], 0) / draft.length).toFixed(3));
    setDrawing(false); setDraft([]);
  };
  return (<div>
    <div className="row mapbar">
      <label>Imagery<select value={layer} onChange={e => setLayer(e.target.value as Key)}>{(Object.keys(LAYERS) as Key[]).map(k => <option key={k} value={k}>{LAYERS[k].label}</option>)}</select></label>
      {LAYERS[layer].time && <label>Date<input type="date" value={date} max={isoDaysAgo(1)} onChange={e => setDate(e.target.value)} /></label>}
    </div>
    <div className="row tools">
      {!drawing ? <button className="btn s" onClick={() => { setDrawing(true); setDraft([]); }}>Draw area</button>
        : <><button className="btn s solid" disabled={draft.length < 3} onClick={finish}>Finish ({draft.length} points)</button><button className="btn s" onClick={() => { setDrawing(false); setDraft([]); }}>Cancel</button></>}
      {polygon && !drawing && <button className="btn s" onClick={() => onPolygon(undefined)}>Clear area</button>}
    </div>
    <div ref={el} className={`leaflet-box ${drawing ? "drawing" : ""}`} aria-label="Map: click to choose a point, or draw an area" />
    <p className="note">{drawing ? "Click to add corners (at least 3), then Finish." : polygon ? `Area: ${polygon.length} corners. Analysis averages grid cells inside it (cos-latitude weighted). Max 20° across.` : `Point: ${lat}, ${lon}. Click to move it, or draw an area for an area average.`}</p>
  </div>);
}
