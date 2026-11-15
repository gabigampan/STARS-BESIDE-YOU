"""w0: reproduce the shipped results with the in-memory configuration before any option.

    python "tierra luna/audit/w0_reproduce.py"

Checks paired counts 10,192 / 6,360 / 450 and the top 5 of each mission against
docs/AUDIO_TOP5.json (Earth id, twin id, similarity, suitability, final) and against the bundle
ranks. Writes audit/out/w0_reproduce.json.
"""
import numpy as np
from w_common import MISSIONS, audio_top5, base_run, compare_tracks, dump, jload, ROOT, summary
import os

EXPECT = {"rover": 10192, "solar": 6360, "lunar_base": 450}


def main():
    a = jload(os.path.join(ROOT, "docs", "AUDIO_TOP5.json"))
    out, ok_all = {}, True
    for mi in MISSIONS:
        r = base_run(mi)
        s = summary(r)
        rec = a["missions"][mi]["pairs"]
        score_ok = all(abs(t["similarity"] - p["similarity"]) < 0.006 and abs(t["suitability"] - p["suitability"]) < 0.006
                       and abs(t["final"] - p["final"]) < 0.006 for t, p in zip(s["top"], rec))
        tracks, broken = compare_tracks(mi, s["top"], r)
        ok = s["paired"] == EXPECT[mi] and not broken and score_ok
        ok_all &= ok
        out[mi] = dict(s, expected_paired=EXPECT[mi], tracks=tracks, scores_match_audio=score_ok, reproduced=ok)
        print(mi, "passing", s["passing"], "paired", s["paired"], "twins", s["distinct_twins"], "zone", s["zone_cells"],
              "top5 ok", not broken, "scores ok", score_ok)
        for t in s["top"]:
            print("  ", t["rank"], t["earth_id"], t["earth_place"]["place"], t["moon_id"], t["moon_feature"]["feature"],
                  t["similarity"], t["suitability"], t["final"])
    out["reproduced_all"] = bool(ok_all)
    dump(out, "w0_reproduce.json")
    print("REPRODUCED" if ok_all else "NOT REPRODUCED")


if __name__ == "__main__":
    main()
