"""Write scenarios/solar.json for the Solar panels video from the shipped bundle.

usage: python3 -I tools/solar_pair.py [--template scenarios/solar.template.json] [--out scenarios/solar.json]
       python3 -I tools/solar_pair.py --preview-earth 40184 --preview-moon 23206 --out <scratch>/solar.json

The pair is read, never typed: the first id of missions.json missions[solar].top5.ids when that field
exists, else the rank 1 item of explain.json missions.solar; that item must be in explain.json. Every
pair-dependent field (cells, coordinates, place names, table values, the card, the captions' numbers,
the Sun's season, the caption cue times) is filled from the bundle and the two 1-degree tables.
prepare.py then checks the result against the same files and render.js refuses to start on a mismatch.

--preview-*: a PREVIEW scenario for a pair that is not (yet) in the bundle, from the tables only, for
preview stills and terrain preparation. It is marked "preview": true; prepare.py skips the bundle
check for it and render.js refuses to render more than stills or a timeline from it.
"""
import os, sys, json, csv, math, argparse
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(HERE, "..", "public", "data", "v2")
TABLES = os.path.join(HERE, "..", "..", "tierra luna", "output_real")


def row(fname, cell):
    with open(os.path.join(TABLES, fname), newline="") as f:
        for r in csv.DictReader(f):
            if r["cell_id"] == cell:
                return r
    raise SystemExit("cell %s not in %s" % (cell, fname))


def num(s):
    v = float(s)
    return int(v) if v == int(v) and "." not in s else v


def ll(lat, lon, dec="."):
    f = lambda x: ("%g" % abs(x)).replace(".", dec)
    return "%s° %s %s° %s" % (f(lat), "N" if lat >= 0 else "S", f(lon), ("E" if lon >= 0 else ("W" if dec == "." else "O")))


def es(x):
    return str(x).replace(".", ",")


def sun_elev(lat, d, H):
    p, d, H = math.radians(lat), math.radians(d), math.radians(H)
    U = math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(H)
    return math.degrees(math.asin(max(-1, min(1, U))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=os.path.join(HERE, "scenarios", "solar.template.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "scenarios", "solar.json"))
    ap.add_argument("--preview-earth", type=int); ap.add_argument("--preview-moon", type=int)
    ap.add_argument("--timeline", help="<work>/solar/timeline.json from render.js --timeline: adds a cue at every other label change (real terrain hiding the Sun)")
    a = ap.parse_args()
    sc = json.load(open(a.template))
    gen = sc.pop("generator")
    ex = json.load(open(os.path.join(BUNDLE, "explain.json")))["missions"]["solar"]
    ms = [m for m in json.load(open(os.path.join(BUNDLE, "missions.json")))["missions"] if m.get("id") == "solar"][0]
    simj = json.load(open(os.path.join(BUNDLE, "similarity.json")))
    mz = json.load(open(os.path.join(BUNDLE, "mission_zones.json")))
    vj = {v["name"]: v for v in json.load(open(os.path.join(BUNDLE, "variables.json")))["variables"]}
    simv = {v["variable"]: v for v in ms["similarity"]["variables"]}
    preview = a.preview_earth is not None
    if preview:
        eid, mid, it = a.preview_earth, a.preview_moon, None
        sel = "PREVIEW: pair given on the command line (not read from the bundle)"
    else:
        top5 = (ms.get("top5") or {}).get("ids")
        eid = top5[0] if top5 else [x for x in ex if x["rank"] == 1][0]["id"]
        sel = "missions.json missions[solar].top5.ids[0]" if top5 else "explain.json missions.solar rank 1"
        its = [x for x in ex if x["id"] == eid]
        if not its:
            raise SystemExit("pair %d (%s) is not in explain.json missions.solar" % (eid, sel))
        it = its[0]; mid = it["similarity"]["twin"]["id"]
    mrow, erow = row("moon_real_1deg.csv", "M%d" % mid), row("earth_real_1deg.csv", "E%d" % eid)
    mlat, mlon, elat, elon = float(mrow["lat_deg"]), float(mrow["lon_deg"]), float(erow["lat_deg"]), float(erow["lon_deg"])
    zone = ms["similarity"]["zone"]; code = mz["mission_zone_regions"]["solar"][0]
    zlabel = [r for r in mz["regions"] if r["code"] == code][0]["label"]

    # ---- table values (levels from variables.json; slope_iso_deg is the mission's slope_deg)
    def lev(var, body):
        n = "slope_deg" if var == "slope_iso_deg" else var
        return vj[n]["bodies"][body]["level"] if n in vj else "DERIVED"
    tv = {"moon": {k: {"value": num(mrow[k]), "level": lev(k, "MOON"), "unit": u} for k, u in gen["moon_table_vars"].items()},
          "earth": {k: {"value": num(erow[k]), "level": lev(k, "EARTH"), "unit": u} for k, u in gen["earth_table_vars"].items()}}
    if preview:
        feat, fkm = "(feature pending)", None
        place = dict(country="(pending)", region=None, nearest_place="(pending)", nearest_place_km=None)
    else:
        feat, fkm = it["similarity"]["twin"]["feature"], it["similarity"]["twin"]["feature_km"]
        place = it["place"]
    sc["site"] = {"body": "MOON", "cell_id": "M%d" % mid, "lat_deg": mlat, "lon_deg": mlon, "label": ll(mlat, mlon),
                  "place": "%s km from %s" % (fkm, feat) if fkm is not None else "near %s" % feat,
                  "place_ref": {"feature": feat, "distance_km": fkm, "source": "explain.json solar item, similarity.twin.feature / feature_km (IAU/USGS Gazetteer of Planetary Nomenclature)"},
                  "zone": {"name": zlabel, "region_code": code, "abs_lat_max": zone["abs_lat_max"], "elevation_max_m": zone["elevation_max_m"],
                           "cells": zone["cells"], "bundle_rule_name": zone["name"],
                           "source": "mission_zones.json region %s label; rule and cell count from missions.json missions[solar].similarity.zone" % code},
                  "card_name": "near %s" % feat}
    ename = ", ".join(x for x in (place["region"], place["country"]) if x)
    sc["earth_site"] = {"body": "EARTH", "cell_id": "E%d" % eid, "lat_deg": elat, "lon_deg": elon, "name": ename,
                        "nearest_place": place["nearest_place"], "nearest_place_km": place["nearest_place_km"],
                        "source": "explain.json solar item 'place'; selected by " + sel}
    sc["table_values"] = tv
    # ---- Sun: the season of the cell's hemisphere's summer, so the noon Sun reaches the table's sun_elev_max_deg
    obl = sc["constants"]["moon_obliquity_deg"]["value"]
    d = obl if mlat >= 0 else -obl
    sc["sun"]["declination_deg"] = d
    smax = tv["moon"]["sun_elev_max_deg"]["value"]
    if abs((90 - abs(mlat) + obl) - smax) > 0.02:
        raise SystemExit("noon Sun %.2f does not reach the table's sun_elev_max_deg %s" % (90 - abs(mlat) + obl, smax))
    # ---- Earth at its mean position (sub-Earth point 0 N 0 E), geometric estimate
    la, lo = math.radians(mlat), math.radians(mlon)
    arc = math.degrees(math.acos(math.cos(la) * math.cos(lo)))
    az = math.degrees(math.atan2(math.sin(-lo), -math.sin(la) * math.cos(-lo))) % 360
    sc["earth_visibility"] = {"draw": False, "elev_mean_deg": round(90 - arc, 1), "az_mean_deg": round(az, 1),
                              "decision": "Not drawn. Geometric estimate of the Earth's mean position: elevation 90 deg minus the %.1f deg arc from the site to the sub-Earth point (0 N 0 E), azimuth %.1f deg; parallax and libration ignored." % (arc, az)}
    sc["panel_text"]["earth_row"] = "not drawn (~%d° up, mean pos.)" % round(90 - arc)
    # ---- pair values and card
    if preview:
        sc["preview"] = True
        sc["pair_values"] = {"mission": "solar", "preview": True, "note": "PREVIEW: not in the shipped bundle; the card is not rendered from it"}
        sc["card"]["subtitle"] = "PREVIEW: pair not in the shipped bundle"; sc["card"]["legend"] = "PREVIEW"
    else:
        sim = it["similarity"]
        A = lambda x: float(str(np.float32(x)))
        def tenths(x):
            s = "%.12f" % A(x); i = s.index(".")
            return int(s[:i]) * 10 + int(s[i + 1]) + (1 if int(s[i + 2]) >= 5 else 0)
        At, Gt = tenths(sim["atmosphere"]["toa_kwh_m2_day"]), tenths(sim["atmosphere"]["ground_kwh_m2_day"])
        loss = (200 * (At - Gt) + At) // (2 * At)
        lv = {}
        for var in [v["variable"] for v in sim["variables"]] + ["irradiance_kwh_m2_day"] + list(sim["not_part_of_similarity"]):
            lv[var] = {b.lower(): (simv[var]["sides"][b]["level"] if var in simv else vj[var]["bodies"][b]["level"]) for b in ("EARTH", "MOON")}
        sc["pair_values"] = {
            "source": "app/public/data/v2/explain.json missions.solar item %d (selected by %s); similarity.json; missions.json; mission_zones.json; variables.json. Written by tools/solar_pair.py and checked again by prepare.py before every run." % (eid, sel),
            "mission": "solar", "selected_by": sel, "rule": sim["rule"], "rank": it["rank"], "earth_id": eid, "moon_id": mid,
            "suitability": it["suitability"], "similarity": sim["value"], "final": it["final"],
            "variables": {v["variable"]: {k: v[k] for k in ("earth", "moon", "difference", "tolerance", "role", "weight")} for v in sim["variables"]},
            "not_part_of_similarity": sim["not_part_of_similarity"],
            "atmosphere": dict(sim["atmosphere"], toa_display="%d.%d" % divmod(At, 10), ground_display="%d.%d" % divmod(Gt, 10),
                               loss_pct_display=loss, loss_rule=simj["texts"]["solar_limitation"]["placeholders"]["loss_pct"]["rule"]),
            "pair_sentence": sim["pair_sentence"], "saturation_note": simj["texts"]["solar_similarity_saturation"]["text"],
            "synodic_days_bundle": simj["real_value"]["lunar_day_earth_days"], "levels": lv,
            "populations": {"earth_paired": ms["similarity"]["paired_count"], "source": "missions.json missions[solar].similarity.paired_count"}}
        sc["card"]["title"] = "Earth analog and lunar twin: solar panels, pair number %d" % it["rank"]
        sc["card"]["subtitle"] = ("Suitability %s, similarity %s, final %s. The lunar cell lies in the %s, the Solar panels zone: within %g° of the equator and at or below −%s m. "
                                  "Values from the project tables (1-degree cells); each carries its level.") % (
            it["suitability"], sim["value"], it["final"], zlabel[0].lower() + zlabel[1:], zone["abs_lat_max"], "{:,.0f}".format(-zone["elevation_max_m"]))
        sc["card"]["legend"] = sc["card"].pop("legend_head") + " " + sc["pair_values"]["saturation_note"]
    sc["card"].pop("legend_head", None)

    # ---- caption cue times: the frames where the label changes (same rule as page/main.js solarStatus,
    # with the Sun clear of the terrain; render.js checks the cues against the rendered labels)
    fps, S, A_ = sc["fps"], sc["sun_status"], sc["array"]
    s0, s1, T = sc["sun"]["hour_angle_start_deg"], sc["sun"]["hour_angle_end_deg"], sc["sun"]["sim_end_s"]
    el = lambda f: sun_elev(mlat, d, s0 + (s1 - s0) * min(1, f / fps / T))
    first = lambda cond, f0, f1: next(f for f in range(f0, f1) if cond(f))
    nf = int(round(T * fps))
    f_low_end = first(lambda f: el(f) >= S["low_deg"], 0, nf)
    f_high = first(lambda f: el(f) >= S["high_deg"], 0, nf)
    f_high_end = first(lambda f: f > f_high and el(f) < S["high_deg"], f_high, nf)
    f_low2 = first(lambda f: f > f_high_end and el(f) < S["low_deg"], f_high_end, nf)
    t_noon = round((0 - s0) / (s1 - s0) * T, 3)
    fr = lambda f: round(f / fps, 3)
    dep0, dep1, hold = A_["deploy_start_s"], A_["deploy_end_s"], A_["done_hold_s"]
    if not (fr(f_low_end) < dep0 and dep1 + hold < fr(f_high) < t_noon < fr(f_high_end) < 30 < fr(f_low2) < T):
        raise SystemExit("caption cue order does not hold for this latitude; adjust the template")
    card0 = sc["duration_s"] - sc["card_s"]
    sc["captions"]["cue_times"] = [0, fr(f_low_end), dep0, dep1, dep1 + hold, fr(f_high), t_noon, fr(f_high_end), 30, fr(f_low2), card0, card0 + 3]

    # ---- caption texts (numbers from the scenario values above)
    m, e = sc["site"], sc["earth_site"]
    en = [
        "3D simulation driven by table data, not real footage. Sunrise over the real relief (SLDEM2015, LOLA and Kaguya) of lunar cell %s, %s, %s, in the %s. The Sun is just above the eastern horizon; the exposure is raised for the low Sun (not to scale). The camera descends to the stowed panels." % (m["cell_id"], m["label"], m["place"], zlabel[0].lower() + zlabel[1:]),
        "The Sun climbs above %d°; the shadows shorten." % S["low_deg"],
        "The mast rises and two wings of hinged panels unfold upwards.",
        "The panels lie flat, facing the sky; energy is counted from now.",
        "Morning: the Sun climbs in the east. The power of a flat panel follows the Sun's elevation (model, before cell efficiency).",
        "The Sun is above %d°: short shadows and the most power." % S["high_deg"],
        "Local noon: the Sun stands in the %s at the cell's highest elevation in the table (%s°)." % ("south" if mlat > d else "north", smax),
        "Afternoon: the Sun descends towards the west; the shadows lengthen.",
        "The power falls as the Sun gets lower. The lunar day lasts 29.5 Earth days and about half of it is night: after sunset a panel here gets no sunlight for about two Earth weeks (shaded on the graph).",
        "Low Sun in the west: long shadows; the exposure is raised again (not to scale). Sunset and the lunar night follow."]
    esl = [
        "Simulación 3D basada en datos de las tablas, no son imágenes reales. Amanecer sobre el relieve real (SLDEM2015, LOLA y Kaguya) de la celda lunar %s, %s, a %s km de %s, en las %s. El Sol acaba de asomar por el horizonte este; la exposición se aumenta por el Sol bajo (no a escala). La cámara desciende hasta los paneles plegados." % (m["cell_id"], ll(mlat, mlon, ","), es(m["place_ref"]["distance_km"]), m["place_ref"]["feature"], "llanuras ecuatoriales bajas (los mares)"),
        "El Sol pasa de %d°; las sombras se acortan." % S["low_deg"],
        "El mástil sube y dos alas de paneles con bisagras se despliegan hacia arriba.",
        "Los paneles quedan en horizontal, mirando al cielo; la energía se cuenta desde ahora.",
        "Mañana: el Sol sube por el este. La potencia de un panel plano sigue la altura del Sol (modelo, antes de la eficiencia de las células).",
        "El Sol pasa de %d°: sombras cortas y la máxima potencia." % S["high_deg"],
        "Mediodía local: el Sol está al %s, a la altura máxima de la celda según la tabla (%s°)." % ("sur" if mlat > d else "norte", es(smax)),
        "Tarde: el Sol baja hacia el oeste; las sombras se alargan.",
        "La potencia cae a medida que el Sol baja. El día lunar dura 29,5 días terrestres y aproximadamente la mitad es de noche: tras la puesta de Sol un panel aquí no recibe luz durante unas dos semanas terrestres (sombreado en la gráfica).",
        "Sol bajo al oeste: sombras largas; la exposición vuelve a aumentarse (no a escala). Después llegan la puesta de Sol y la noche lunar."]
    if zlabel != "Low equatorial plains (the maria)":
        raise SystemExit("zone label changed in the bundle (%s): update the Spanish caption" % zlabel)
    if preview:
        en += ["PREVIEW", "PREVIEW"]; esl += ["PREVIEW", "PREVIEW"]
    else:
        pv = sc["pair_values"]; V = pv["variables"]; at = pv["atmosphere"]; npv = pv["not_part_of_similarity"]
        toa, sl, ro = V["irradiance_toa_kwh_m2_day"], V["slope_deg"], V["roughness_m"]
        tk, sw = npv["temp_k"], npv["lst_diurnal_amp_k"]
        en += [
            "Closing card: the Earth analog in %s (cell %s, %s, %s km from %s) and its lunar twin, cell %s %s, matched on sunlight above the atmosphere: %s against %s kWh/m² per day (difference %s, tolerance %s). At the Earth site only %s kWh/m² per day reach the ground (modelled): %s of %s, %d %% is lost in the atmosphere; the Moon has no atmosphere. Slope %s° against %s°; roughness %s m against %s m. Suitability %s, similarity %s, final %s." % (
                e["name"], e["cell_id"], ll(elat, elon), e["nearest_place_km"], e["nearest_place"], m["cell_id"], m["card_name"], toa["earth"], toa["moon"], toa["difference"], toa["tolerance"],
                at["ground_kwh_m2_day"], at["ground_display"], at["toa_display"], at["loss_pct_display"], sl["earth"], sl["moon"], ro["earth"], ro["moon"], pv["suitability"], pv["similarity"], pv["final"]),
            "A panel at the Earth site does not receive what a panel on the Moon receives: only the sunlight that reaches the ground arrives there, while the Moon's day lasts 29.5 Earth days, about half of them dark. Mean surface temperature %s K against %s K and daily swing %s K against %s K are not part of the similarity. 3D simulation driven by table data. Not real footage." % (tk["earth"], tk["moon"], sw["earth"], sw["moon"])]
        esl += [
            "Tarjeta final: el análogo terrestre en %s (celda %s, %s, a %s km de %s) y su gemela lunar, la celda %s cerca de %s, emparejadas por la luz solar por encima de la atmósfera: %s frente a %s kWh/m² al día (diferencia %s, tolerancia %s). En el punto terrestre solo %s kWh/m² al día llegan al suelo (modelado): %s de %s, se pierde un %d %% en la atmósfera; la Luna no tiene atmósfera. Pendiente %s° frente a %s°; rugosidad %s m frente a %s m. Idoneidad %s, similitud %s, final %s." % (
                e["name"], e["cell_id"], ll(elat, elon, ","), es(e["nearest_place_km"]), e["nearest_place"], m["cell_id"], m["place_ref"]["feature"], es(toa["earth"]), es(toa["moon"]), es(toa["difference"]), es(toa["tolerance"]),
                es(at["ground_kwh_m2_day"]), es(at["ground_display"]), es(at["toa_display"]), at["loss_pct_display"], es(sl["earth"]), es(sl["moon"]), es(ro["earth"]), es(ro["moon"]), es(pv["suitability"]), es(pv["similarity"]), es(pv["final"])),
            "Un panel en el punto terrestre no recibe lo mismo que un panel en la Luna: allí solo llega la luz que alcanza el suelo, mientras que el día lunar dura 29,5 días terrestres, aproximadamente la mitad a oscuras. La temperatura media de la superficie, %s K frente a %s K, y la oscilación diaria, %s K frente a %s K, no forman parte de la similitud. Simulación 3D basada en datos de las tablas. No son imágenes reales." % (es(tk["earth"]), es(tk["moon"]), es(sw["earth"]), es(sw["moon"]))]
    # extra cues where the real terrain hides the Sun (labels 'partly' / 'blocked'), from the timeline
    extra = {S["partly"]: ("The Sun starts to go behind the real terrain; the light on the array fades.",
                           "El Sol empieza a ocultarse tras el relieve real; la luz sobre los paneles se apaga."),
             S["blocked"]: ("The Sun is behind the real terrain while still above the flat horizon: the array is in shadow and the power is zero.",
                            "El Sol está tras el relieve real aunque sigue sobre el horizonte plano: los paneles quedan en sombra y la potencia es cero."),
             S["night"]: ("The Sun is below the horizon: lunar night.", "El Sol está bajo el horizonte: noche lunar.")}
    cues = sc["captions"]["cue_times"]
    if a.timeline:
        tl = json.load(open(a.timeline)); prev = None
        for i, x in enumerate(tl[:nf]):
            if x["status"] != prev and i > 0:
                t = fr(i)
                if not any(abs(t - c) < 1e-6 for c in cues):
                    if x["status"] not in extra:
                        raise SystemExit("label change at %.3f s to '%s' is not a cue; adjust the template" % (t, x["status"]))
                    k = next(j for j, c in enumerate(cues) if c > t)
                    cues.insert(k, t); en.insert(k, extra[x["status"]][0]); esl.insert(k, extra[x["status"]][1])
            prev = x["status"]
    sc["captions"]["en"]["text"], sc["captions"]["es"]["text"] = en, esl
    assert len(en) == len(esl) == len(sc["captions"]["cue_times"])
    if a.out != os.path.join(HERE, "scenarios", "solar.json"):
        sc["output_dir"] = os.path.relpath(os.path.join(HERE, "..", "public", "media", "solar"), os.path.dirname(os.path.abspath(a.out)))
    json.dump(sc, open(a.out, "w"), ensure_ascii=False, indent=2)
    print("wrote %s: Earth E%d (%s) - Moon M%d (%s), selected by %s; cues %s" % (a.out, eid, ll(elat, elon), mid, ll(mlat, mlon), sel, sc["captions"]["cue_times"]))


if __name__ == "__main__":
    main()
