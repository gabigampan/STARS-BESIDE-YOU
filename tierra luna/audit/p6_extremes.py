"""Point B: the extreme Earth tmin_c cells (coldest and warmest coldest-month minimum) and the Antarctic
plateau against the nearest NOAA GHCN-Daily stations (coldest-month mean daily minimum, 1970-2000 and all
years), own code; reuses the downloader of p6_fetch_ext.py (cached files in the scratchpad).
Run:  $PY -I "tierra luna/audit/p6_extremes.py"      Output: out/p6_extremes.csv
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import OUT, haversine_km, load_tables  # noqa: E402
from p6_fetch_ext import station_stats, stations  # noqa: E402

e, _ = load_tables()
st = stations()
targets = {
    "coldest tmin cell (-89.5, 43.5)": (-89.5, 43.5),
    "cell nearest the South Pole station (-89.5, -24.5)": (-89.5, -24.5),
    "cell of Vostok station (-78.5, 106.5)": (-78.5, 106.5),
    "cell of Dome C (-75.5, 123.5)": (-75.5, 123.5),
    "warmest tmin cell (3.5, 73.5)": (3.5, 73.5),
}
cid_of = lambda la, lo: f"E{int(round(89.5 - la)) * 360 + int(round(lo + 179.5))}"
rows = []
ei = e.set_index("cell_id")
for label, (lat, lon) in targets.items():
    cid = cid_of(lat, lon)
    d = haversine_km(lat, lon, st.lat.values, st.lon.values, 6371.0088)
    cand = st.assign(km=d)
    cand = cand[cand.km <= 300].nsmallest(2, "km")
    for _, s in cand.iterrows():
        ss = station_stats(s["id"])
        for tag, v in ss.items():
            rows.append(dict(target=label, cell=cid, table_tmin_c=ei.at[cid, "tmin_c"], table_elev_m=ei.at[cid, "elevation_m"],
                             station=s["id"], name=s["name"], st_elev_m=s.elev, km=round(float(s.km), 1), period=tag, **(v or {})))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "p6_extremes.csv"), index=False)
print(df[["target", "table_tmin_c", "table_elev_m", "station", "name", "st_elev_m", "km", "period", "years", "coldest_month_mean_tmin_c", "mean_daily_range_k"]].to_string())
