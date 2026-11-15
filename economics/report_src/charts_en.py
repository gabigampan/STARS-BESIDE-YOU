import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
D="../data/"  # run from report_src/
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False})
C1,C2="#c0392b","#2471a3"
# 1 pairs
p=pd.read_csv(D+"space_earth_pairs.csv")
short=["TRIDENT drill\n(direct)","Pathfinder\nairbags","Ingenuity","MOXIE","VSAT arrays\n(estimated)","Iris rover\n(estimated)","1 kg Moon vs\nNASA chamber","1 kg Moon vs\nuniv. chamber"]
x=np.arange(len(p));w=0.38
fig,ax=plt.subplots(figsize=(10,5))
ax.bar(x-w/2,p.space_cost_usd/1e6,w,color=C1,label="Test on the Moon/Mars")
ax.bar(x+w/2,p.earth_cost_usd/1e6,w,color=C2,label="Test on Earth")
ax.set_yscale("log");ax.set_ylim(0.01,600);ax.set_ylabel("Million USD (log scale)")
ax.set_xticks(x);ax.set_xticklabels(short,fontsize=8)
for i,r in enumerate(p.space_earth_ratio):
    ax.text(i,p.space_cost_usd[i]/1e6*1.35,f"×{r:g}",ha="center",fontweight="bold",fontsize=9)
ax.legend(frameon=False,loc="lower left");ax.set_title("Same artifact: cost of testing it in space vs. on Earth",fontweight="bold")
plt.tight_layout();plt.savefig("g1_pairs.png",dpi=160);plt.close()
# 2 kg
items=[("Moon: ispace (1 kg)",1.5e6,C1),("Moon: Astrobotic (1 kg)",1.2e6,C1),("Moon: CLPS IM-3 (1 kg, calc.)",0.846e6,C1),
("Earth: 1 week NASA vacuum chamber (est.)",58496,C2),("Earth: MDRS rotation, 6 people",21000,C2),("Earth: 1 week university TVAC",17500,C2),("Earth: 1 t LHS-1 simulant",29250,C2)]
fig,ax=plt.subplots(figsize=(10,4.2))
ax.barh([i[0] for i in items][::-1],[i[1]/1e3 for i in items][::-1],color=[i[2] for i in items][::-1])
ax.set_xscale("log");ax.set_xlabel("Thousand USD (log scale)")
for i,(n,v,c) in enumerate(items[::-1]): ax.text(v/1e3*1.1,i,f"{v/1e3:,.0f} k$",va="center",fontsize=9)
ax.set_title("What it costs to put 1 kg on the Moon vs. a complete test on Earth",fontweight="bold")
plt.tight_layout();plt.savefig("g2_kg.png",dpi=160);plt.close()
# 3 escalation
e=pd.read_csv(D+"macro_error_cost_escalation.csv")
fig,ax=plt.subplots(figsize=(10,4.2))
ax.bar(e.phase,e.systems_composite_max,color="#bbb",label="Maximum")
ax.bar(e.phase,e.systems_composite_min,color=C2,label="Minimum")
ax.set_yscale("log");ax.set_ylabel("Times the cost at requirements (log)")
for i,(a,b) in enumerate(zip(e.systems_composite_min,e.systems_composite_max)): ax.text(i,b*1.15,f"{a:g}–{b:g}×",ha="center",fontsize=9)
ax.legend(frameon=False);ax.set_title("Fixing an error costs more the later it is found (NASA, Stecklein 2004)",fontweight="bold",fontsize=10)
plt.tight_layout();plt.savefig("g3_escalation.png",dpi=160);plt.close()
# 4 cost per successful TRIDENT test
ps=np.linspace(0.2,1,81)
fig,ax=plt.subplots(figsize=(10,4.2))
ax.plot(ps*100,50/ps,color=C1,lw=2.5,label="Moon: 50 M$ CLPS delivery ÷ prob. of success")
ax.plot(ps*100,7.61/0.95*np.ones_like(ps),color=C2,lw=2.5,label="Earth: build and test 7.6 M$ (95 % success)")
for s,l in [(0.25,"CLPS: 1 of 4\nfully successful flights"),(0.5,"50 %")]:
    ax.scatter([s*100],[50/s],color=C1,zorder=5);ax.annotate(f"{l}\n{50/s:.0f} M$",(s*100,50/s),xytext=(10,6),textcoords="offset points",fontsize=8)
ax.set_xlabel("Probability that the test on the Moon succeeds (%)");ax.set_ylabel("Expected cost per valid test (M$)")
ax.set_ylim(0,260);ax.legend(frameon=False)
ax.set_title("TRIDENT drill: expected cost of obtaining a test that works",fontweight="bold")
plt.tight_layout();plt.savefig("g4_trident.png",dpi=160);plt.close()
# 5 break-even
m=pd.read_csv(D+"macro_illustrative_savings_model.csv")
m=m[m.C_T_MUSD_assumed==1.6]
fig,ax=plt.subplots(figsize=(10,4.2))
for (n,g),c in zip(m.groupby("reference_mission"),[C1,C2,"#27ae60","#8e44ad"]):
    ax.plot(g.q_assumed_detection*100,g.expected_net_savings_MUSD,lw=2,label=f"{n} (threshold q*={g.q_breakeven_threshold.iloc[0]*100:.2f} %)",color=c)
ax.axhline(0,color="k",lw=.8);ax.set_xlabel("q: % of failures detected by the Earth test (assumption)");ax.set_ylabel("Expected net savings (2025 M$)")
ax.legend(frameon=False,fontsize=8);ax.set_title("Expected savings of a 1.6 M$ campaign at an analog (Nomad, Atacama)",fontweight="bold")
plt.tight_layout();plt.savefig("g5_savings.png",dpi=160);plt.close()
# 6 surface failures by decade
f=pd.read_csv(D+"macro_mars_failures_by_decade.csv").dropna(subset=["pct_failure_or_partial_surface"])
fig,ax=plt.subplots(figsize=(10,3.8))
ax.bar(f.decade,f.pct_failure_or_partial_surface,color=C1)
for i,(v,n) in enumerate(zip(f.pct_failure_or_partial_surface,f.surface_n)): ax.text(i,v+2,f"{v:.0f} % (n={n})",ha="center",fontsize=9)
ax.set_ylabel("% failure or partial");ax.set_ylim(0,115);ax.set_title("Mars: surface elements that fail, by decade",fontweight="bold")
plt.tight_layout();plt.savefig("g6_failures.png",dpi=160);plt.close()
