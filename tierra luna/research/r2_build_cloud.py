"""r2: ISCCP-H HGM total cloud amount -> 1-degree supplement keyed by our cell id.
Raw: monthly files 2012-01..2016-12 in research-raw/isccp_hgm (argument 1). Deterministic."""
import sys, os, glob, csv
import numpy as np, netCDF4 as nc
RAW = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/research-raw/isccp_hgm"
TL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(TL, "real_data", "supplement")
files = sorted(glob.glob(os.path.join(RAW, "ISCCP-Basic.HGM.v01r00.GLOBAL.201[2-6].*.nc")))
assert len(files) == 60, len(files)
stack = []
for f in files:
    d = nc.Dataset(f)
    lat = d["lat"][:]; lon = d["lon"][:]
    assert np.allclose(lat, np.arange(-89.5, 90, 1)) and np.allclose(lon, np.arange(0.5, 360, 1))
    a = np.ma.filled(d["cldamt"][0].astype(float), np.nan)   # percent, south->north, lon 0..360
    d.close()
    a = a[::-1, :]                                            # row 0 = lat 89.5
    a = np.roll(a, 180, axis=1)                               # col 0 = lon -179.5
    stack.append(a)
S = np.array(stack)
nval = np.isfinite(S).sum(0)
mean = np.where(nval >= 48, np.nanmean(np.where(np.isfinite(S), S, np.nan), axis=0), np.nan) / 100.0
with open(os.path.join(OUTD, "earth_cloud_isccp_1deg.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["cell_id", "row", "col", "lat_deg", "lon_deg", "cloud_frac_isccp", "clear_frac_isccp", "n_months_isccp"])
    for r in range(180):
        for c in range(360):
            v = mean[r, c]
            w.writerow([f"E{r*360+c}", r, c, 89.5 - r, -179.5 + c,
                        "" if not np.isfinite(v) else f"{v:.4f}", "" if not np.isfinite(v) else f"{1-v:.4f}", int(nval[r, c])])
print("cells with value", int(np.isfinite(mean).sum()), "of", mean.size)
