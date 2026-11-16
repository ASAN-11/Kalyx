import { useEffect, useState } from "react";
import MediaHolder from "./components/MediaHolder";
import Investigate from "./components/Investigate";
import Learn from "./components/Learn";
import { discover, getCatalog, type Collection, type Variable } from "./api";

export default function App() {
  const [vars, setVars] = useState<Variable[]>([]); const [cat, setCat] = useState("All"); const [pick, setPick] = useState<string>(); const [q, setQ] = useState(""); const [hits, setHits] = useState<Collection[]>([]); const [qerr, setQerr] = useState("");
  const [apiErr, setApiErr] = useState("");
  useEffect(() => { getCatalog().then(setVars).catch(() => setApiErr("Could not reach the KALYX API. Start the backend (uvicorn app.main:app --reload) and reload.")); }, []);
  const cats = ["All", ...new Set(vars.map(v => v.category))];
  return (<>
    <nav><b>KALYX</b><div><a href="#discover">Discover</a><a href="#investigate">Investigate</a><a href="#learn">Learn</a></div></nav>
    <MediaHolder name="hero" className="hero"><div className="wrap hero-in"><p className="eye">NASA Space Apps Challenge 2026</p><h1>Reach<br />Infinity</h1><p className="sub">Turn Earth observation data into evidence of environmental change.</p><a className="btn solid" href="#investigate">Start an investigation</a></div></MediaHolder>
    <section className="wrap split"><h2>One workflow.<br />Real statistics.</h2><div><div className="q"><h3>What is changing, and where?</h3><p>Pick a variable and a region, from a single point to a grid of cells.</p></div><div className="q"><h3>How much, and is it significant?</h3><p>Linear and Sen's slopes, Mann-Kendall testing, autocorrelation and false-discovery control.</p></div></div></section>
    <MediaHolder name="band" tone="earth2" className="band"><div className="wrap"><h2>Never call a trend<br />significant by eye.</h2></div></MediaHolder>
    <section id="discover" className="wrap"><h2>Discover</h2>
      <div className="chips">{cats.map(c => <button key={c} className={`chip ${c === cat ? "on" : ""}`} onClick={() => setCat(c)}>{c}</button>)}</div>
      {apiErr && <p className="err" role="alert">{apiErr}</p>}
      <div className="cat">{vars.filter(v => cat === "All" || v.category === cat).map(v => <div className="vc" key={v.id}><small>{v.category}</small><h3>{v.name}</h3><p className="note">{v.source}<br />{v.spatial} · {v.temporal} · {v.coverage}<br />Unit: {v.unit}</p><button className="btn" onClick={() => { setPick(v.id); location.hash = "investigate"; }}>Investigate</button></div>)}</div></section>
    <section className="wrap"><h2>Search NASA datasets</h2><p className="note">Live search of NASA Earthdata CMR.</p>
      <form className="row search" onSubmit={e => { e.preventDefault(); setQerr(""); discover(q).then(setHits).catch(x => setQerr(x.message)); }}><input value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. IMERG precipitation monthly" aria-label="Search datasets" /><button className="btn solid" type="submit">Search</button></form>
      {qerr && <p className="err">{qerr}</p>}
      <div className="cat">{hits.map(h => <div className="vc" key={h.id}><small>{h.provider} · {h.short_name} v{h.version}</small><h3>{h.title}</h3><p className="note">{h.start?.slice(0, 10)} to {h.end?.slice(0, 10) || "present"}{h.doi ? ` · doi ${h.doi}` : ""}<br />{h.summary}</p></div>)}</div></section>
    <section id="investigate" className="dash"><div className="wrap"><h2>Investigate</h2><Investigate initialVar={pick} /></div></section>
    <Learn />
    <footer><div className="wrap">KALYX. Explore the data. Detect the trend. Understand the change.</div></footer>
  </>);
}
