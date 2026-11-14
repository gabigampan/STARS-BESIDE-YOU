import glob, math, os
import numpy as np, pandas as pd
G = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/verify_gcp"
T = pd.read_csv("/home/user/stars-beside-you/tierra luna/output_real/moon_real_1deg.csv", keep_default_na=False, na_values=[""]).set_index(["row", "col"])
rng = np.random.default_rng(7)
out = []
for f in sorted(glob.glob(G + "/*.tab")):
    t = pd.read_csv(f, header=None, skiprows=1, skipinitialspace=True, usecols=[0, 1, 2, 10], names=["clon", "clat", "ltim", "tbol"])
    print(os.path.basename(f), "clat range", t.clat.min(), t.clat.max(), "clon range", t.clon.min(), t.clon.max(), "rows", len(t))
    latc = sorted(set(np.floor(t.clat.values).astype(int)))
    picks = [(int(rng.choice(latc)), int(rng.integers(-180, 180))) for _ in range(15)]
    if "40s30s" in f: picks += [(-44, -12)]  # Tycho is at 43.3S: not in this band; keep the band's own cells
    for la0, lo0 in picks:
        lat_c, lon_c = la0 + 0.5, lo0 + 0.5
        if not (t.clat.min() < lat_c < t.clat.max()): continue
        s = t[(t.clat > lat_c - 0.5) & (t.clat < lat_c + 0.5) & (t.clon > lon_c - 0.5) & (t.clon < lon_c + 0.5)]
        s = s[s.tbol > 0]
        vals = {"mean": [], "max": [], "min": [], "w": []}
        for (la, lo), g in s.groupby(["clat", "clon"]):
            k = np.rint((g.ltim.values - 0.125) / 0.25).astype(int)
            order = np.argsort(k); k = k[order]; tb = g.tbol.values[order]
            if len(k) < 40: continue
            if (np.diff(np.r_[k, k[0] + 96]).max() - 1) > 12: continue
            full = np.interp(np.arange(96), k, tb, period=96)
            vals["mean"].append(full.mean()); vals["max"].append(full.max()); vals["min"].append(full.min()); vals["w"].append(math.cos(math.radians(la)))
        r, c = int(89.5 - lat_c), int(lon_c + 179.5)
        y = T.loc[(r, c)]
        rec = {"band": os.path.basename(f)[21:27], "lat": lat_c, "lon": lon_c, "nsub": len(vals["w"])}
        if vals["w"]:
            w = np.array(vals["w"])
            for k2 in ("mean", "max", "min"):
                rec["mine_" + k2] = float((np.array(vals[k2]) * w).sum() / w.sum())
        rec.update({"tab_mean": y.temp_k, "tab_max": y.tmax_k, "tab_min": y.tmin_k, "tab_amp": y.lst_diurnal_amp_k, "tab_tmin_c": y.tmin_c})
        out.append(rec)
d = pd.DataFrame(out)
d["d_mean"] = d.mine_mean - d.tab_mean; d["d_max"] = d.mine_max - d.tab_max; d["d_min"] = d.mine_min - d.tab_min
d["d_amp"] = (d.mine_max - d.mine_min) - d.tab_amp; d["d_tminc"] = (d.mine_min - 273.15) - d.tab_tmin_c
print(d.to_string())
print("cells", len(d), "max abs diffs", d[["d_mean", "d_max", "d_min", "d_amp", "d_tminc"]].abs().max().to_dict())
d.to_csv("moon_temp_mine.csv", index=False)
