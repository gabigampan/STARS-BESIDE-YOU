import math, numpy as np, pandas as pd
M="/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/moon"
Z=np.fromfile(M+"/ldem_16.img",dtype="<i2").reshape(2880,5760)*0.5
T=pd.read_csv("/home/user/stars-beside-you/tierra luna/output_real/moon_real_1deg.csv",keep_default_na=False,na_values=[""]).set_index(["row","col"])
cells=pd.read_csv("moon_mine.csv")[["name","row","col"]]
R=1737400.0; dy=R*math.radians(1/16); out=[]
def row_at(i):
    if i<0: return np.roll(Z[-i-1],2880)
    if i>=2880: return np.roll(Z[2*2880-i-1],2880)
    return Z[i]
for _,c in cells.iterrows():
    sl=[]; w=[]
    j0=int(round(((-180+c.col)%360)*16))
    for k in range(16):
        i=c.row*16+k; lat=90-(i+0.5)/16; z=Z[i]; s=max(1.0,1/math.cos(math.radians(lat)))
        js=np.arange(j0,j0+16)
        def at(x):
            x0=np.floor(x).astype(int); f=x-x0; return z[x0%5760]*(1-f)+z[(x0+1)%5760]*f
        gx=(at(js+s)-at(js-s))/(2*s*dy*math.cos(math.radians(lat)))
        gy=(row_at(i-1)[js%5760]-row_at(i+1)[js%5760])/(2*dy)
        sl.append(np.degrees(np.arctan(np.hypot(gx,gy)))); w.append(np.full(16,math.cos(math.radians(lat))))
    sl=np.concatenate(sl); w=np.concatenate(w); y=T.loc[(c.row,c.col)]
    out.append((c["name"],(sl*w).sum()/w.sum()-y.slope_iso_deg,np.percentile(sl,90)-y.slope_iso_p90_deg))
d=pd.DataFrame(out,columns=["name","d_iso","d_iso_p90"]); print(len(d),"cells; max|d| slope_iso",d.d_iso.abs().max(),"p90",d.d_iso_p90.abs().max())
