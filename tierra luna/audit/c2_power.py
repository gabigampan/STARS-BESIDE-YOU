"""Point C (new fifteen), NASA POWER as a CHECK only (team-lead authorisation; nothing copied anywhere):
public POWER climatology API v2.10.x (keyless), community RE, at each cell centre.
Solar: ALLSKY_SFC_SW_DWN (CERES SYN1deg) and CLOUD_AMT (CERES SYN1deg, MODIS-based clouds: independent
of ISCCP-H). Lunar base: T2M_MIN, T2M_RANGE (MERRA-2). Output: out/c2_power.json
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c2_fetch import sites  # noqa: E402
from p6_common import OUT  # noqa: E402

EXT = "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/ext/power"
os.makedirs(EXT, exist_ok=True)
res = []
for s in sites():
    if s["mission"] not in ("solar", "lunar_base"):
        continue
    par = "ALLSKY_SFC_SW_DWN,CLOUD_AMT" if s["mission"] == "solar" else "ALLSKY_SFC_SW_DWN,T2M_MIN,T2M_RANGE"
    p = os.path.join(EXT, f"clim_{s['cell']}.json")
    if not os.path.exists(p):
        url = (f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters={par}&community=RE"
               f"&longitude={s['lon']}&latitude={s['lat']}&format=JSON")
        open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "generic-audit-client"}), timeout=60).read())
    d = json.load(open(p))
    pr = d["properties"]["parameter"]
    r = dict(cell=s["cell"], mission=s["mission"], lat=s["lat"], lon=s["lon"], api_version=d["header"]["api"]["version"],
             period=f"{d['header'].get('start')}-{d['header'].get('end')}", merra2_elev_m=d["geometry"]["coordinates"][2],
             power_allsky_ann=pr["ALLSKY_SFC_SW_DWN"]["ANN"], model_ground=s.get("bundle_irradiance_kwh_m2_day"))
    if s["mission"] == "solar":
        r.update(power_cloud_amt_ann_pct=pr["CLOUD_AMT"]["ANN"], power_clear_frac=round(1 - pr["CLOUD_AMT"]["ANN"] / 100, 4),
                 model_clear_frac_isccp=s.get("bundle_clear_frac_isccp"),
                 diff_clear=round(s["bundle_clear_frac_isccp"] - (1 - pr["CLOUD_AMT"]["ANN"] / 100), 4))
    else:
        mins = {k: v for k, v in pr["T2M_MIN"].items() if k != "ANN"}
        cm = min(mins, key=mins.get)
        r.update(power_coldest_month=cm, power_coldest_month_t2m_min=mins[cm], power_t2m_range_ann=pr["T2M_RANGE"]["ANN"],
                 model_tmin_c=s.get("bundle_tmin_c"), model_lst_amp_k=s.get("bundle_lst_diurnal_amp_k"),
                 diff_tmin=round(s["bundle_tmin_c"] - mins[cm], 2))
    res.append(r)
json.dump(res, open(os.path.join(OUT, "c2_power.json"), "w"), indent=1)
for r in res:
    print(r)
