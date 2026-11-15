from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DV","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
ss=getSampleStyleSheet()
B=ParagraphStyle("b",parent=ss["BodyText"],fontName="DV",fontSize=9.5,leading=13.5)
H1=ParagraphStyle("h1",parent=B,fontName="DVB",fontSize=17,leading=21,spaceAfter=6)
H2=ParagraphStyle("h2",parent=B,fontName="DVB",fontSize=12.5,leading=16,spaceBefore=8,spaceAfter=4,textColor=colors.HexColor("#1b4f72"))
S=ParagraphStyle("s",parent=B,fontSize=7.5,leading=10,textColor=colors.grey)
EQ=ParagraphStyle("eq",parent=B,fontName="DVB",backColor=colors.HexColor("#eef3f8"),borderPadding=5,spaceBefore=4,spaceAfter=6)
W=17*cm
def img(f,h=None): 
    from PIL import Image as I; w,hh=I.open(f).size; return Image(f,width=W,height=W*hh/w)
def tbl(rows,cw):
    t=Table([[Paragraph(str(c),ParagraphStyle("t",parent=B,fontSize=8,leading=10,fontName="DVB" if i==0 else "DV")) for c in r] for i,r in enumerate(rows)],colWidths=cw,repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d6e4f0")),("GRID",(0,0),(-1,-1),.3,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]));return t
s=[]
P=lambda t,st=B: s.append(Paragraph(t,st))
P("Testing on Earth or on the Moon and Mars: economic feasibility",H1)
P("NASA Space Apps Málaga 2026 · Stars Beside You · Planetary twin finder · Economic component",S)
P("Thesis",H2)
P("Testing a rover, a solar array or a drill on the Moon or Mars costs between <b>3 and 40 times</b> more than building and testing it on Earth, according to the documented pairs. In addition, the space test can itself fail: of NASA's first four commercial lunar flights (CLPS), only one was fully successful. Fixing an error discovered in operations costs between 29 and 1,615 times what it would cost in the requirements phase, versus 21–78 times if it is detected during testing. That is why a campaign at a terrestrial analog pays for itself by detecting a tiny fraction of failures (0.1–1 %), and a tool that picks better analogs raises that detection per euro spent.")
P("1. Data: the same artifact tested in space and on Earth",H2)
s.append(img("g1_pairs.png"))
rows=[["Artifact","Space","Earth","Ratio","Pair type"],
["TRIDENT drill (PRIME-1, Moon)","50 M$ CLPS delivery","7.6 M$ build and test","×6.6","Direct, same artifact"],
["Pathfinder airbags (Mars)","150 M$ lander","4 M$ airbag system","×37.5","Approximate"],
["Ingenuity helicopter (Mars)","85 M$ (80 construction + 5 operation)","23 M$ (1-year budget line)","×3.7","Weak approximation"],
["MOXIE, oxygen from CO₂ (Mars)","≈50 M$ (investigator's figure)","4 M$ long-duration stack test","×12.6","Successor technology"],
["VSAT vertical solar arrays (Moon)","120 M$ (100 kg × 1.2 M$/kg, hypothetical)","6.5 M$ prototype and environmental test","×18.6","Estimate"],
["Iris rover (CMU, Moon)","2.4 M$ (2 kg × rate)","0.8 M$ the entire rover","×3","Estimate"],
["1 kg on the Moon vs 1 week in a NASA vacuum chamber","1.2 M$","58 k$","×20.5","Generic"]]
s.append(tbl(rows,[4.2*cm,4*cm,3.8*cm,1.3*cm,3.7*cm]))
P("Sources: SAM.gov, GovTribe, NASA, Planetary Society, ILC Dover, PMI, SBIR, Astrobotic Payload User Guide, NASA–Sandia agreement. The ratio is nominal and not adjusted for inflation. 'Approximate' means the Earth cost is not exactly the same test.",S)
s.append(PageBreak())
P("2. The entry price: every kilo on the Moon",H2)
P("Public rates for delivering cargo to the lunar surface are around <b>0.85–1.5 M$ per kg</b> (Astrobotic 1.2 M$; ispace 1.5 M$; CLPS IM-3 ≈0.85 M$, our own calculation). On Earth, that money pays for a week in a NASA vacuum chamber (≈58 k$, estimated) about 20 times, or a week in a university chamber (17.5 k$) about 68 times.")
s.append(img("g2_kg.png"))
P("3. The test in space also fails",H2)
P("On Mars, 31 % of the surface elements launched since 1990 (landers, rovers, penetrators) failed: 5 of 16. On the Moon, of the first four CLPS flights only Blue Ghost was fully successful; IM-1 and IM-2 tipped over and Peregrine failed. The TRIDENT drill never got to drill because its lander tipped over.")
s.append(img("g6_failures.png"))
s.append(PageBreak())
P("4. Cost per valid test: the TRIDENT case",H2)
P("What matters is not the cost of the flight but the cost of obtaining a test that works: <b>cost ÷ probability of success</b>. At the CLPS rate (1 in 4), each valid lunar test comes to about 200 M$; with a 50 % success rate, 100 M$. On Earth, the same drill was built and tested for 7.6 M$, between 13 and 26 times less.")
s.append(img("g4_trident.png"))
P("5. Why detecting early saves so much",H2)
s.append(img("g3_escalation.png"))
P("NASA study (Stecklein et al., 2004): an error that costs 1 at requirements costs 21–78 in integration and test and 29–1,615 in operations. The upper end of 1,615 corresponds to errors that end in total loss of the system, which is exactly what happens on the Moon or Mars. Real cases: Mars Polar Lander (the leg test was not repeated), Schiaparelli, Beresheet, Curiosity's wheels (tested on smooth terrain) and InSight's mole (tested only with cohesionless sands).",B)
s.append(PageBreak())
P("6. Economic model",H2)
P("<b>Theory:</b> cost-effectiveness analysis, expected value of information (Raiffa and Schlaifer, 1961; Howard, 1966), real options (Dixit and Pindyck, 1994) and economies of scope.")
P("Expected cost without testing:  E₀ = C_M + p₀·C_M",EQ)
P("Expected cost with an Earth test:  E₁ = C_T + C_M + p₀·(1 − q)·C_M",EQ)
P("Net savings (value of information):  ΔE = p₀·q·C_M − C_T",EQ)
P("Break-even threshold:  q* = C_T / (p₀·C_M)",EQ)
P("Earth vs. space, with the same detection:  savings = C_T^space/(1 − p_T) − C_T^Earth",EQ)
P("Finder indicator:  similarity per euro = s / C_T(s)",EQ)
P("C_M is the mission cost, p₀ the probability of failure, q the fraction of failures the test detects (it grows with the analog's similarity s), C_T the cost of the test and p_T the probability that the space test itself fails. The mission's scientific value is ignored, so the calculation is conservative.")
s.append(img("g5_savings.png"))
P("With p₀ = 31.25 % and a 1.6 M$ campaign (Nomad rover, Atacama, 1997), the test pays for itself if it detects 0.13 % of failures on a Curiosity-type mission (4,021 M$ in 2025 dollars), 0.37 % on InSight or 0.84 % on Pathfinder. If it detected 10 %, on a Curiosity-type mission it would avoid about <b>124 M$</b> of expected loss.")
P("7. Where our project fits",H2)
P("The finder acts on both levers of the model: it <b>raises q</b>, because it picks more similar analogs (InSight's mole failed because it was tested in an unrepresentative soil), and it <b>lowers C_T</b>, because it adds a cost and accessibility layer. At NASA Marshall's lunar test bed, transport was more than 90 % of the cost. Wildcard sites (Moon and Mars at once) add economies of scope: a single campaign serves two destinations.")
P("8. Reliability and limits",H2)
P("• q has no empirical source: it is presented as a scenario with sensitivity analysis. • Only TRIDENT is a direct pair; the others are approximate or estimated and are labeled as such. • Nominal figures not adjusted for inflation; the adjustment does not change the order of magnitude. • Some per-kg rates come from search excerpts. • What is solid for the judges is the order of magnitude and the ranking, not the exact euro.")
P("Main sources: NASA OIG IG-24-013 (CLPS); SAM.gov and GovTribe (PRIME-1); Planetary Society, Science Mission Impact dataset; Stecklein et al. 2004 (NTRS 20100036670); Astrobotic Payload User Guide; NASA–Sandia agreement SAA-EA-23-39178; NASA Ames press release 97-50 (Nomad); GAO-20-405; Wikipedia, List of missions to Mars. Full data with URLs in the accompanying Excel file (Space_testing_cost_data.xlsx).",S)
SimpleDocTemplate("../Economic_feasibility_Earth_vs_space_testing.pdf",pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=1.6*cm,bottomMargin=1.6*cm,title="Testing on Earth or on the Moon and Mars: economic feasibility",author="Facundo Casalanguida, Stars Beside You").build(s)
