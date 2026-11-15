import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// NASA GIBS WMTS (EPSG:3857). Verify layer ids / max zoom at https://nasa-gibs.github.io/gibs-api-docs/
const LAYERS = {
  truecolor: { id: "MODIS_Terra_CorrectedReflectance_TrueColor", ext: "jpg", max: 9, time: true, label: "MODIS true colour" },
  lst: { id: "MODIS_Terra_Land_Surface_Temp_Day", ext: "png", max: 7, time: true, label: "MODIS land surface temp (day)" },
  blue: { id: "BlueMarble_ShadedRelief_Bathymetry", ext: "jpeg", max: 8, time: false, label: "Blue Marble" },
} as const;
type Key = keyof typeof LAYERS;
const url = (k: Key, date: string) => {
  const l = LAYERS[k];
  return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${l.id}/default/${l.time ? date + "/" : ""}GoogleMapsCompatible_Level${l.max}/{z}/{y}/{x}.${l.ext}`;
};
const isoDaysAgo = (d: number) => new Date(Date.now() - d * 864e5).toISOString().slice(0, 10);

export default function MapPicker({ lat, lon, onPick }: { lat: number; lon: number; onPick: (lat: number, lon: number) => void }) {
  const el = useRef<HTMLDivElement>(null); const map = useRef<L.Map>(); const tile = useRef<L.TileLayer>(); const dot = useRef<L.CircleMarker>();
  const pick = useRef(onPick); pick.current = onPick;
  const [layer, setLayer] = useState<Key>("truecolor"); const [date, setDate] = useState(isoDaysAgo(5));
  useEffect(() => {
    const m = L.map(el.current!, { center: [lat, lon], zoom: 5, minZoom: 2, worldCopyJump: true });
    m.on("click", e => pick.current(+e.latlng.lat.toFixed(3), +e.latlng.lng.toFixed(3)));
    dot.current = L.circleMarker([lat, lon], { radius: 7, color: "#69D5E8", fillColor: "#69D5E8", fillOpacity: .4 }).addTo(m);
    map.current = m; return () => { m.remove(); };
  }, []);
  useEffect(() => {
    tile.current?.remove();
    tile.current = L.tileLayer(url(layer, date), { maxNativeZoom: LAYERS[layer].max, maxZoom: 12, attribution: "Imagery: NASA GIBS / EOSDIS" }).addTo(map.current!);
  }, [layer, date]);
  useEffect(() => { dot.current?.setLatLng([lat, lon]); }, [lat, lon]);
  return (<div>
    <div className="row mapbar">
      <label>Imagery<select value={layer} onChange={e => setLayer(e.target.value as Key)}>{(Object.keys(LAYERS) as Key[]).map(k => <option key={k} value={k}>{LAYERS[k].label}</option>)}</select></label>
      {LAYERS[layer].time && <label>Date<input type="date" value={date} max={isoDaysAgo(1)} onChange={e => setDate(e.target.value)} /></label>}
    </div>
    <div ref={el} className="leaflet-box" aria-label="Map: click to choose the analysis point" />
    <p className="note">Click the map to set the analysis point ({lat}, {lon}). Imagery is for context; analysis uses the point value.</p>
  </div>);
}
