"""Independent check of the audio integration (15-11-2026, after 14:20 CET).

Usage: python -I "tierra luna/audit/a2_audio_integration_check.py" <team_folder>
Reads only; writes tierra luna/audit/out/a2_audio_integration_check.json.
Checks: (1) the 19 MP3, SHA256SUMS.txt and transcripts.json in app/public/audio are byte-identical to the
team's folder and each MP3 matches its SHA256SUMS line; no other MP3. (2) transcripts.json against
0486ad9: only rover_1 differs, only by the removed Gjoa Haven clause. (3) pending.json is empty;
tracks.json entry n of each mission is <mission>_n and the bundle's nth top5 id. (5) three files
re-measured with ffprobe and ffmpeg volumedetect against the integrator's CSV.
"""
import csv, hashlib, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUD = os.path.join(ROOT, "app", "public", "audio")
TEAM = sys.argv[1]
OUT = os.path.join(ROOT, "tierra luna", "audit", "out", "a2_audio_integration_check.json")
res, fails = {}, []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
    return bool(cond)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# (1)
team_files = sorted(os.listdir(TEAM))
mp3s = sorted(f for f in os.listdir(AUD) if f.endswith(".mp3"))
ok(len(mp3s) == 19, f"{len(mp3s)} MP3 in app/public/audio")
ok(sorted(f for f in team_files if f.endswith(".mp3")) == mp3s, "MP3 set differs from the team's")
sums = {}
for line in open(os.path.join(TEAM, "SHA256SUMS.txt")):
    h, name = line.split()
    sums[name.lstrip("*")] = h
same = {}
for f in mp3s + ["SHA256SUMS.txt", "transcripts.json"]:
    same[f] = open(os.path.join(AUD, f), "rb").read() == open(os.path.join(TEAM, f), "rb").read()
    ok(same[f], f"{f} not byte-identical to the team's")
sum_ok = {f: sha(os.path.join(AUD, f)) == sums.get(f) for f in mp3s}
for f, v in sum_ok.items():
    ok(v, f"{f} does not match SHA256SUMS.txt")
ok(len(sums) == 19, f"{len(sums)} lines in SHA256SUMS.txt")
res["check1"] = {"mp3_count": len(mp3s), "byte_identical": sum(same.values()), "of": len(same),
                 "sha256sums_ok": sum(sum_ok.values()), "sha256sums_lines": len(sums)}

# (2)
old = json.loads(subprocess.check_output(["git", "-C", ROOT, "show", "0486ad9:app/public/audio/transcripts.json"]))
new = json.load(open(os.path.join(AUD, "transcripts.json")))
diff = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
ok(set(old) == set(new), "track keys differ from 0486ad9")
ok(diff == ["rover_1.mp3"], f"tracks differing from 0486ad9: {diff}")
clause = ", about 1,116 kilometers north of Gjoa Haven"
o = old["rover_1.mp3"]
ok(o.replace(clause, "", 1).strip() == new["rover_1.mp3"].strip(), "rover_1 differs by more than the clause")
res["check2"] = {"differing_tracks": diff, "removed_clause": clause,
                 "only_other_difference": "trailing whitespace" if o.replace(clause, "", 1) != new["rover_1.mp3"] else "none"}

# (3)
pend = json.load(open(os.path.join(AUD, "pending.json")))
ok(pend.get("pending_rerecord") == [], "pending.json list not empty")
mj = json.load(open(os.path.join(ROOT, "app/public/data/v2/missions.json")))
ms = mj["missions"] if "missions" in mj else mj
ms = ms if isinstance(ms, list) else list(ms.values())
tracks = json.load(open(os.path.join(AUD, "tracks.json")))["tracks"]
prefix = {"rover": "rover", "solar": "solar", "lunar_base": "base"}
map_ok = 0
for m in ms:
    mid = m.get("id") or m.get("mission")
    ids = m["top5"]["ids"]
    tr = [t for t in tracks if t.get("mission") == mid and t["step"] == "pair"]
    ok(len(tr) == 5, f"{mid}: {len(tr)} pair tracks")
    for n, t in enumerate(tr, 1):
        good = t["file"] == f"{prefix[mid]}_{n}.mp3" and t["rank"] == n and t["earth_cell_id"] == f"E{ids[n-1]}"
        map_ok += ok(good, f"{mid} entry {n}: {t}")
res["check3"] = {"pending_rerecord": pend.get("pending_rerecord"), "pair_tracks_mapped_ok": map_ok, "of": 15,
                 "web_behaviour": "app/src/a11y/audio.ts: a file in pending_rerecord gets state 'pending' (text only, never requested); "
                                  "with the list empty every track is played when the guide is on and its step or pair is on screen"}

# (5)
rows = {r["file"]: r for r in csv.DictReader(open(os.path.join(ROOT, "tierra luna/audit/out/a_audio_files.csv")))}
remeasure = {}
for f in ["rover_4.mp3", "base_3.mp3", "base_1.mp3"]:
    p = os.path.join(AUD, f)
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
    e = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", p, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    mean = float(e.split("mean_volume:")[1].split()[0]); peak = float(e.split("max_volume:")[1].split()[0])
    r = rows[f]
    match = abs(d - float(r["duration_s"])) < 0.01 and mean == float(r["mean_volume_db"]) and peak == float(r["max_volume_db"])
    ok(match, f"{f} re-measure differs from CSV")
    remeasure[f] = {"duration_s": round(d, 3), "mean_db": mean, "peak_db": peak, "matches_csv": match}
dur = [float(r["duration_s"]) for r in rows.values()]
mean = [float(r["mean_volume_db"]) for r in rows.values()]
peak = [float(r["max_volume_db"]) for r in rows.values()]
res["check5"] = {"remeasured": remeasure, "csv_rows": len(rows),
                 "csv_range": {"duration_s": [min(dur), max(dur)], "mean_db": [min(mean), max(mean)], "peak_db": [min(peak), max(peak)],
                               "decode_ok": sum(r["decode_ok"] == "True" for r in rows.values()),
                               "longest_inside_silence_s": max(float(r["longest_inside_silence_s"]) for r in rows.values())}}
ok(min(dur) >= 34.5 - 0.05 and max(dur) <= 51.8 + 0.05, "durations outside 34.5-51.8 s")
ok(max(peak) <= -1.5, "peak above -1.5 dB")
ok(min(mean) >= -23.3 and max(mean) <= -22.7, "mean volume outside -23.3..-22.7 dB")

res["failures"] = fails
res["verdict"] = "GO" if not fails else "NOT YET"
res["not_verified"] = "that the spoken words match transcripts.json word for word (nobody listened or transcribed)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
