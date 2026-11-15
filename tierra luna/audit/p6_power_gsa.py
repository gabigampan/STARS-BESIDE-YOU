"""Point C, second external contrasts (check only; nothing enters the model):
 - Global Solar Atlas (World Bank / ESMAP, Solargis model v2.2.68) long-term GHI at each of the 15
   Earth cell centres (single open point queries, cached in the scratchpad);
 - NASA POWER daily values saved from the session's read-only NASA connector (authorised use, point C
   only): E38464 for 2020 (CERES SYN1deg ALLSKY_SFC_SW_DWN and TOA_SW_DWN, MERRA-2 T2M_MIN and
   T2M_RANGE) and E17566 for January 2020 (MERRA-2 T2M_MIN, T2M_RANGE);
 - the GHCN-Daily station values for the SAME period, so POWER and station are compared like for like.
Run:  $PY -I "tierra luna/audit/p6_power_gsa.py"      Output: out/p6_power_gsa.json
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import OUT, REPO, dump, haversine_km, load_tables, toa_daily_mean_kwh  # noqa: E402

EXT = os.environ.get("P6_EXT", "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/ext")
GH = os.path.join(EXT, "ghcn")
e, _ = load_tables()
ei = e.set_index("cell_id")
top = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
cells = {}
for mis, x in top["missions"].items():
    for p in x["pairs"]:
        cells.setdefault(p["earth_cell_id"], (p["earth_place"]["cell_centre_lat"], p["earth_place"]["cell_centre_lon"], []))[2].append(f"{mis}#{p['rank']}")


def get(url, path):
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        req = urllib.request.Request(url, headers={"User-Agent": "generic-audit-client"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as fh:
            fh.write(r.read())
        time.sleep(1.0)
    return path


out = {"gsa": [], "power": {}}
os.makedirs(os.path.join(EXT, "gsa"), exist_ok=True)
for cid, (lat, lon, uses) in cells.items():
    p = get(f"https://api.globalsolaratlas.info/data/lta?loc={lat},{lon}", os.path.join(EXT, "gsa", f"{cid}.json"))
    d = json.load(open(p))
    a = d["annual"]["data"]
    meta = d["annual"]["metadata"]["layers"]["GHI"]
    ghi_day = a["GHI"] / 365.25 if a.get("GHI") is not None else None
    model = float(ei.at[cid, "irradiance_kwh_m2_day"])
    out["gsa"].append(dict(cell=cid, uses=uses, lat=lat, lon=lon, gsa_ghi_kwh_m2_yr=a.get("GHI"), gsa_ghi_kwh_m2_day=round(ghi_day, 3) if ghi_day else None,
                           gsa_ele_m=a.get("ELE"), gsa_version=meta.get("version"), gsa_updated=meta.get("updated"), gsa_period_to=meta["period"].get("to"),
                           model_ground_kwh_m2_day=model, diff=round(model - ghi_day, 3) if ghi_day else None,
                           rel_diff_pct=round(100 * (model - ghi_day) / ghi_day, 1) if ghi_day else None))


def station_period(sid, y0, y1, months=None):
    p = os.path.join(GH, sid + ".csv")
    p = get(f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{sid}.csv", p)
    d = pd.read_csv(p, usecols=lambda c: c in ("DATE", "TMAX", "TMIN"), low_memory=False)
    d["DATE"] = pd.to_datetime(d["DATE"])
    d = d[(d.DATE.dt.year >= y0) & (d.DATE.dt.year <= y1)]
    if months:
        d = d[d.DATE.dt.month.isin(months)]
    for c in ("TMAX", "TMIN"):
        d[c] = pd.to_numeric(d[c], errors="coerce") / 10
    g = d.groupby(d.DATE.dt.month).agg(tmin=("TMIN", "mean"), n=("TMIN", "count"))
    both = d.dropna(subset=["TMIN", "TMAX"])
    return dict(n_days_tmin=int(d.TMIN.notna().sum()), monthly_mean_tmin=g.tmin.round(2).to_dict(), n_by_month=g.n.to_dict(),
                coldest_month_mean_tmin=round(float(g[g.n >= 20].tmin.min()), 2) if (g.n >= 20).any() else None,
                mean_range=round(float((both.TMAX - both.TMIN).mean()), 2) if len(both) else None, n_days_range=int(len(both)))


# POWER, E38464, 2020
pw = pd.read_csv(os.path.join(EXT, "power", "E38464_2020.csv"), comment="#")
mon = pw.groupby("MO").T2M_MIN.mean()
st = pd.read_fwf(os.path.join(GH, "ghcnd-stations.txt"), colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (41, 71)], names=["id", "lat", "lon", "elev", "name"], header=None)
inv = pd.read_fwf(os.path.join(GH, "ghcnd-inventory.txt"), colspecs=[(0, 11), (31, 35), (36, 40), (41, 45)], names=["id", "el", "y0", "y1"], header=None)
ok = set(inv[(inv.el == "TMIN") & (inv.y0 <= 2020) & (inv.y1 >= 2020)].id)
s2 = st[st.id.isin(ok)].copy()
s2["km"] = haversine_km(-16.5, 124.5, s2.lat.values, s2.lon.values, 6371.0088)
near = s2.nsmallest(2, "km")
stv = []
for _, s in near.iterrows():
    v = station_period(s.id, 2020, 2020)
    stv.append(dict(station=s.id, name=s["name"], km=round(float(s.km), 1), elev_m=s.elev, **v))
out["power"]["E38464_2020"] = dict(
    query=dict(tool="mcp__nasa__nasa_power", community="RE", lat=-16.5, lon=124.5, period="2020-01-01..2020-12-31", time_standard="LST (default)",
               products="ALLSKY_SFC_SW_DWN and TOA_SW_DWN: CERES SYN1deg; T2M_MIN, T2M_RANGE: MERRA-2 (as printed in the POWER header)", merra2_elev_m=73.91),
    power_allsky_mean=round(float(pw.ALLSKY.mean()), 3), power_toa_mean=round(float(pw.TOA.mean()), 3),
    power_coldest_month=int(mon.idxmin()), power_coldest_month_mean_t2m_min=round(float(mon.min()), 2),
    power_mean_t2m_range=round(float(pw.T2M_RANGE.mean()), 2),
    model_ground=float(ei.at["E38464", "irradiance_kwh_m2_day"]), model_toa_formula_auditor=round(toa_daily_mean_kwh(-16.5), 4),
    model_toa_bundle_pair=9.6005, model_tmin_c=float(ei.at["E38464", "tmin_c"]), model_lst_amp=float(ei.at["E38464", "lst_diurnal_amp_k"]),
    stations_2020=stv)
# POWER, E17566, January 2020, against Hails (CHM00053231) January 2020
pj = pd.read_csv(os.path.join(EXT, "power", "E17566_202001.csv"), comment="#")
hv = station_period("CHM00053231", 2020, 2020, months=[1])
out["power"]["E17566_202001"] = dict(
    query=dict(tool="mcp__nasa__nasa_power", community="RE", lat=41.5, lon=106.5, period="2020-01-01..2020-01-31", products="T2M_MIN, T2M_RANGE: MERRA-2", merra2_elev_m=1335.72),
    power_jan_mean_t2m_min=round(float(pj.T2M_MIN.mean()), 2), power_jan_mean_t2m_range=round(float(pj.T2M_RANGE.mean()), 2),
    station="CHM00053231 HAILS (1510 m, 11.2 km from the cell centre)", station_jan2020=hv,
    model_tmin_c_1970_2000=float(ei.at["E17566", "tmin_c"]))
dump("p6_power_gsa.json", out)
print(json.dumps(out, indent=1, default=float)[:8000])
