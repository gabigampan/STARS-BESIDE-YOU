"""r4: writes data/benchmark/validation_sites_solar.csv and validation_sites_lunar_base.csv.

Deterministic. Inputs: research/out/r4_metoffice_sunshine.json (from r4_metoffice_sunshine.py) and the
verified rows of data/benchmark/analog_benchmark.csv (read only). Coordinates of BSRN stations are copied
from the BSRN station table (https://wiki.pangaea.de/wiki/BSRN, 'Sortable Table of Stations', accessed
2026-11-15). Run: python -I r4_build_site_lists.py
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.dirname(HERE)
BEN = os.path.join(TL, "data", "benchmark")
D = "2026-11-15"
BS = "https://wiki.pangaea.de/wiki/BSRN"
BSS = ("BSRN station table (Latitude/Longitude/Koppen columns); bsrn.awi.de: 'The Baseline Surface Radiation Network "
       "(BSRN) has provided the world's highest-accuracy surface radiation measurements'")
MO = "https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/{}data.txt"
COLS = ["site_id", "role", "name", "operator", "country", "lat", "lon", "coord_source", "recognised_for", "source_url",
        "sentence_relied_on", "date_accessed", "space_tie", "notes"]

SOLAR = [
    ("SP01", "Tamanrasset (BSRN TAM)", "Office National de la Meteorologie, BSRN station", "Algeria", 22.7903, 5.5292, "BWh arid desert hot; desert rock; 1385 m"),
    ("SP02", "Gobabeb (BSRN GOB)", "Gobabeb Namib Research Institute, BSRN station", "Namibia", -23.5614, 15.042, "BWh arid desert hot; desert gravel; 407 m"),
    ("SP03", "De Aar (BSRN DAA)", "South African Weather Service, BSRN station", "South Africa", -30.6667, 23.993, "BSk arid steppe cold; sand; 1287 m; inactive"),
    ("SP04", "Sede Boqer (BSRN SBO)", "BSRN station", "Israel", 30.8597, 34.7794, "BWh arid desert hot; desert rock; closed 2012"),
    ("SP05", "Solar Village (BSRN SOV)", "BSRN station", "Saudi Arabia", 24.91, 46.41, "BWh arid desert hot; desert sand; not maintained since 2002"),
    ("SP06", "Gandhinagar (BSRN GAN)", "BSRN station", "India", 23.1101, 72.6276, "BSh arid steppe hot; closed"),
    ("SP07", "Gurgaon (BSRN GUR)", "BSRN station", "India", 28.4249, 77.156, "BSh arid steppe hot; closed"),
    ("SP08", "Alice Springs (BSRN ASP)", "BSRN station", "Australia", -23.798, 133.888, "BWh arid desert hot; inactive"),
    ("SP09", "Desert Rock (BSRN DRA)", "NOAA SURFRAD, BSRN station", "USA", 36.626, -116.018, "BWk arid desert cold; desert gravel; 1007 m"),
    ("SP10", "Boulder Table Mountain (BSRN BOS)", "NOAA SURFRAD, BSRN station", "USA", 40.125, -105.237, "BSk arid steppe cold; 1689 m"),
    ("SP11", "Petrolina (BSRN PTR)", "BSRN station", "Brazil", -9.068, -40.319, "BSh arid steppe hot; inactive"),
    ("SP12", "Izana (BSRN IZA)", "BSRN station", "Spain (Tenerife)", 28.3093, -16.4993, "Csb; rock; mountain top 2373 m"),
    ("SP13", "Lampedusa (BSRN LMP)", "BSRN station", "Italy", 35.518, 12.63, "BSh arid steppe hot; small island"),
]
SOLAR_NEG = [("SN01", "lerwick", "Lerwick", "Shetland"), ("SN02", "eskdalemuir", "Eskdalemuir", "Scottish Borders"),
             ("SN03", "stornoway", "Stornoway", "Outer Hebrides"), ("SN04", "braemar", "Braemar", "Aberdeenshire"),
             ("SN05", "dunstaffnage", "Dunstaffnage", "Argyll"), ("SN06", "tiree", "Tiree", "Inner Hebrides")]
LB_POS = [("LP01", "OP01", "cold high plateau (3233 m), isolation analog"), ("LP02", "MA06", "polar desert; Haughton-Mars Project"),
          ("LP03", "MA07", "polar desert"), ("LP04", "MA08", "Arctic field site (AMASE)"), ("LP05", "MA19", "ice-sheet margin field site"),
          ("LP06", "MO05", "high mountain; lunar ISRU field tests"), ("LP07", "ES05", "high volcanic plateau; ESA lunar rover tests"),
          ("LP08", "MA05", "habitat analog; cold desert"), ("LP09", "MA10", "subarctic highland; astronaut geology training"),
          ("LP10", "MO04", "NASA Desert RATS exploration operations"), ("LP11", "MO07", "NASA SSERVI FINESSE lunar volcanic analog"),
          ("LP12", "ES02", "ESA PANGAEA astronaut training")]
LB_NEG = [("LN01", "Paramaribo (BSRN PAR)", "Surinam", 5.806, -55.2146, "Af tropical rainforest"),
          ("LN02", "Lanyu Station (BSRN LYU)", "Taiwan", 22.037, 121.5583, "Af tropical rainforest; island"),
          ("LN03", "Ishigakijima (BSRN ISH)", "Japan", 24.3367, 124.1644, "Af tropical rainforest; island"),
          ("LN04", "Rolim de Moura (BSRN RLM)", "Brazil", -11.582, -61.773, "Aw tropical savannah"),
          ("LN05", "Selegua (BSRN SEL)", "Mexico", 15.784, -91.9902, "Aw tropical savannah"),
          ("LN06", "Darwin (BSRN DAR)", "Australia", -12.425, 130.891, "Aw tropical savannah"),
          ("LN07", "Reunion Island University (BSRN RUN)", "Reunion (France)", -20.9014, 55.4836, "Am tropical monsoon; island")]


def main():
    sun = json.load(open(os.path.join(HERE, "out", "r4_metoffice_sunshine.json"), encoding="utf-8"))
    with open(os.path.join(BEN, "validation_sites_solar.csv"), "w", newline="", encoding="utf-8") as w:
        w.write("# validation_sites_solar.csv - r4 external validation for Solar panels (research r4, 2026-11-15; NOT the team benchmark).\n"
                "# role: positive = BSRN reference surface-radiation station in an arid Koppen class or on a high mountain top (as listed by BSRN);"
                " negative = official station data show persistently low sunshine (Met Office, mean annual sunshine 1991-2020 DERIVED by research/r4_metoffice_sunshine.py).\n"
                "# lat/lon exactly as published (coord_source). sentence_relied_on = text of the official source used. space_tie = link to space work where sourced.\n"
                "# Left out: Plataforma Solar de Almeria (official CIEMAT/DLR/ministry pages give an address, no coordinates; psa.es HTTP 503); NREL SRRL (midcdmz.nrel.gov not reachable from this session).\n")
        c = csv.writer(w)
        c.writerow(COLS)
        for s in SOLAR:
            c.writerow([s[0], "positive", s[1], s[2], s[3], s[4], s[5], "BSRN station table", "BSRN reference radiation station; " + s[6],
                        BS, BSS, D, "none sourced", ""])
        for i, k, n, r in SOLAR_NEG:
            v = sun[k]
            c.writerow([i, "negative", n + " (Met Office climate station)", "Met Office", "United Kingdom (" + r + ")", v["lat"], v["lon"],
                        "Location line of the Met Office station data file",
                        "low sunshine: mean %.1f h/yr 1991-2020 over %d complete years (DERIVED); Met Office UK 1991-2020 mean 1402.61 h"
                        % (v["mean_annual_sun_h_1991_2020"], v["years_complete"]),
                        MO.format(k), "monthly 'sun' hours column (Campbell Stokes or Kipp & Zonen); Open Government Licence v3.0", D, "none sourced", ""])
    bench = {r["id"]: r for r in csv.DictReader(open(os.path.join(BEN, "analog_benchmark.csv"), encoding="utf-8"))}
    with open(os.path.join(BEN, "validation_sites_lunar_base.csv"), "w", newline="", encoding="utf-8") as w:
        w.write("# validation_sites_lunar_base.csv - r4 external validation for Lunar base (research r4, 2026-11-15; NOT the team benchmark).\n"
                "# role: positive = station or analog field site used by space agencies or for space-analog research in a cold, high or thermally harsh place"
                " (verified rows of analog_benchmark.csv reused, id in notes; plus Neumayer, site of DLR's EDEN ISS greenhouse);"
                " negative = warm humid tropical place (BSRN station table Koppen class; a measured low thermal swing is not established from an official page).\n"
                "# lat/lon exactly as in coord_source. Benchmark rows flagged unverified (rule of audit/p3_validation.py: HI-SEAS, Axel Heiberg, Aquarius, ...) are not used.\n")
        c = csv.writer(w)
        c.writerow(COLS)
        for i, b, why in LB_POS:
            r = bench[b]
            c.writerow([i, "positive", r["name"], "see space_tie", r["country"], r["lat"], r["lon"],
                        "analog_benchmark.csv row %s (%s)" % (b, r["coord_quality"]), why + "; " + r["analog_property_for"], r["source_url"],
                        "benchmark tested_there: %s [source_status: %s]" % (r["tested_there"], r["source_status"]),
                        "2026-11-14 (benchmark fact-check)", r["tested_there"], "benchmark id " + b])
        c.writerow(["LP13", "positive", "Neumayer III / EDEN ISS greenhouse", "AWI (station); DLR (EDEN ISS)", "Antarctica", -70.65, -8.25,
                    "BSRN station table, Georg von Neumayer (GVN); DLR: the greenhouse was about 400 m from Neumayer III",
                    "Antarctic station; space-greenhouse analog 2018-2023", "https://www.dlr.de/en/research-and-transfer/projects-and-missions/eden-iss",
                    "DLR: 'located in Antarctica, near the Neumayer III Antarctic station'; 'designed to explore future food production on the Moon and Mars'",
                    D, "EDEN ISS (DLR): Moon and Mars food production", "ice shelf; coordinate is the BSRN radiation station"])
        for t in LB_NEG:
            c.writerow([t[0], "negative", t[1], "BSRN station", t[2], t[3], t[4], "BSRN station table", "warm humid tropical climate: " + t[5],
                        BS, "BSRN station table Koppen column: " + t[5], D, "none sourced", "low thermal swing not established from an official page"])


if __name__ == "__main__":
    main()
