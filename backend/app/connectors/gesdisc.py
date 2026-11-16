"""NASA GES DISC gridded connector (GPM IMERG monthly, MERRA-2 monthly land, GLDAS Noah monthly) via earthaccess + xarray.
Needs: pip install -r requirements-live.txt, and EARTHDATA_USER / EARTHDATA_PASS.
NOTE: short names, versions and variable names follow public NASA documentation but were NOT run against the live service.
Verify at https://disc.gsfc.nasa.gov/ (dataset landing pages list variables) before relying on them."""
import os
from ..gridded import cube_from_dataset

# per_day converts a per-time-unit rate to a per-day amount: mm/hr -> x24, kg m-2 s-1 (= mm/s) -> x86400.
PRODUCTS = {
    "pr": dict(short_name="GPM_3IMERGM", version="07", var="precipitation", per_day=24, unit="mm/month"),
    "sm": dict(short_name="M2TMNXLND", version="5.12.4", var="GWETROOT", per_day=None, unit="fraction"),
    "ro": dict(short_name="M2TMNXLND", version="5.12.4", var="RUNOFF", per_day=86400, unit="mm/month"),
    "et": dict(short_name="GLDAS_NOAH025_M", version="2.1", var="Evap_tavg", per_day=86400, unit="mm/month"),
}
MAX_GRANULES = 400

class GesDisc:
    def fetch_cube(self, spec, box, y0, y1, progress=lambda p, m: None):
        try:
            import earthaccess, xarray as xr
        except ImportError:
            raise RuntimeError("Live GES DISC access needs extra packages: pip install -r requirements-live.txt")
        u, p = os.environ.get("EARTHDATA_USER"), os.environ.get("EARTHDATA_PASS")
        if not u or not p: raise RuntimeError("Set EARTHDATA_USER and EARTHDATA_PASS environment variables on the backend.")
        os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"] = u, p
        auth = earthaccess.login(strategy="environment")
        if not getattr(auth, "authenticated", False): raise RuntimeError("Earthdata login was rejected.")
        progress(10, "Searching NASA CMR for granules")
        s, w, n, e = box
        res = earthaccess.search_data(short_name=spec["short_name"], version=spec["version"],
                                      temporal=(f"{y0}-01-01", f"{y1}-12-31"), bounding_box=(w, s, e, n))
        if not res: raise RuntimeError("No granules found for this product, period and area.")
        if len(res) > MAX_GRANULES: raise RuntimeError(f"{len(res)} granules found; shorten the period (limit {MAX_GRANULES}).")
        progress(25, f"Opening {len(res)} granules (this can take several minutes)")
        files = earthaccess.open(res)
        ds = xr.open_mfdataset(files, engine="h5netcdf", combine="by_coords")
        if spec["var"] not in ds: raise RuntimeError(f"Variable '{spec['var']}' not in the files. Available: {', '.join(list(ds.data_vars)[:15])}")
        progress(70, "Subsetting and converting")
        cube = cube_from_dataset(ds, spec, box); progress(95, "Done reading")
        return cube
