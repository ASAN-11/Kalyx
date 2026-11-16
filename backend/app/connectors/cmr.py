"""NASA Earthdata CMR collection search (dataset discovery). Public, no login needed."""
import requests
URL = "https://cmr.earthdata.nasa.gov/search/collections.json"

def search_collections(keyword, limit=10, session=None):
    s = session or requests
    r = s.get(URL, params=dict(keyword=keyword, page_size=limit, sort_key="-usage_score"), timeout=30)
    r.raise_for_status()
    out = []
    for e in r.json().get("feed", {}).get("entry", []):
        out.append(dict(id=e.get("id"), title=e.get("title"), short_name=e.get("short_name"), version=e.get("version_id"),
                        provider=e.get("data_center"), start=e.get("time_start"), end=e.get("time_end"),
                        summary=(e.get("summary") or "")[:280], doi=e.get("doi")))
    return out
