"""Compare the renderer's straight-down view of the near terrain patch with the shaded relief
computed directly from the elevation patch (prepare.py). Writes a side-by-side PNG and prints the
correlation of the two images (both lit from the north-west at 25 deg, north up).
usage: python3 -I tools/check_relief.py <work_dir>/<name>
"""
import sys, os
import numpy as np
from PIL import Image

d = sys.argv[1]
hs = Image.open(os.path.join(d, "hillshade_near.png")).convert("L")
td = Image.open(os.path.join(d, "check_topdown_render.png")).convert("L")
W, H = td.size
crop = td.crop(((W - H) // 2, 0, (W - H) // 2 + H, H))
hs_r = hs.resize((H, H), Image.BILINEAR)
a = np.asarray(hs_r, dtype=float); b = np.asarray(crop, dtype=float)
m = 20  # ignore the outer border
r = np.corrcoef(a[m:-m, m:-m].ravel(), b[m:-m, m:-m].ravel())[0, 1]
out = Image.new("L", (2 * H + 20, H), 0)
out.paste(hs_r, (0, 0)); out.paste(crop, (H + 20, 0))
p = os.path.join(d, "check_relief_side_by_side.png")
out.save(p)
print("correlation hillshade vs render: %.3f -> %s" % (r, p))
