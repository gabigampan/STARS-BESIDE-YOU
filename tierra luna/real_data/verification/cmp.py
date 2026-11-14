import sys, numpy as np, pandas as pd
mine = pd.read_csv(sys.argv[1], keep_default_na=False, na_values=[""])
tab = pd.read_csv(sys.argv[2], keep_default_na=False, na_values=[""])
cols = sys.argv[3].split(",")
t = tab.set_index(["row", "col"])
rows = []
for v in cols:
    if v not in mine: continue
    diffs = []; mism = 0; n = 0; worst = None
    for _, m in mine.iterrows():
        tv = t.loc[(m.row, m.col), v]; mv = m[v]
        if isinstance(mv, str) or isinstance(tv, str):
            mv = "" if (not isinstance(mv, str)) else mv; tv = "" if (not isinstance(tv, str)) else tv
            n += 1
            if mv != tv: mism += 1; worst = (m["name"], mv, tv)
            continue
        if pd.isna(mv) and pd.isna(tv): continue
        n += 1
        if pd.isna(mv) != pd.isna(tv): mism += 1; worst = (m["name"], mv, tv); continue
        d = abs(float(tv) - float(mv)); diffs.append(d)
        if worst is None or (isinstance(worst[1], float) and d > abs(worst[2]-worst[1])): worst = (m["name"], float(mv), float(tv))
    print(f"{v:24s} n={n:3d} presence/class mismatches={mism:2d} max|diff|={max(diffs) if diffs else 0:.4g} median={np.median(diffs) if diffs else 0:.3g} worst={worst}")
