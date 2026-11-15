"""r4: mean annual sunshine 1991-2020 (DERIVED) from Met Office historic station data files.
Usage: python -I r4_metoffice_sunshine.py <folder with <station>data.txt files>
Source files: https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/<station>data.txt
(Met Office, Open Government Licence v3.0). Only years 1991-2020 with 12 non-missing monthly sun values."""
import json, os, re, sys
d = sys.argv[1]
out = {}
for f in sorted(os.listdir(d)):
    if not f.endswith("data.txt"):
        continue
    L = open(os.path.join(d, f), encoding="latin-1").read().splitlines()
    m = re.search(r"Lat\s+(-?[\d.]+)\s*,?\s+Lon\s+(-?[\d.]+)", " ".join(L[1:3]))
    yrs = {}
    for ln in L:
        p = ln.split()
        if len(p) >= 7 and p[0].isdigit() and len(p[0]) == 4 and 1991 <= int(p[0]) <= 2020:
            v = p[6].replace("#", "").replace("*", "")
            try:
                yrs.setdefault(int(p[0]), []).append(float(v))
            except ValueError:
                yrs.setdefault(int(p[0]), []).append(None)
    full = [sum(v) for v in yrs.values() if len(v) == 12 and None not in v]
    out[f[:-8]] = {"lat": float(m.group(1)), "lon": float(m.group(2)), "years_complete": len(full),
                   "mean_annual_sun_h_1991_2020": round(sum(full) / len(full), 1) if full else None}
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "r4_metoffice_sunshine.json"), "w"), indent=1)
