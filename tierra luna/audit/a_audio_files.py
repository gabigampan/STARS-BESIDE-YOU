"""Measure the 19 audio files of the guide (app/public/audio/*.mp3), read only.

For each file: ffprobe (codec, sample rate, channels, bit rate, duration), a full decode
(`ffmpeg -v error -i f -f null -`: any message is a decoding error), ffmpeg volumedetect
(mean and max volume, dB) and silencedetect (noise=-50dB, d=1.0: silences of one second or
more). A silence that starts at 0 or ends at the end of the track is a leading/trailing
silence; any other is "inside the track". It also checks every file against SHA256SUMS.txt.
Nothing is written to the audio folder.

Output: tierra luna/audit/out/a_audio_files.csv (one row per track, in transcripts.json order).

Run: <venv>/python "tierra luna/audit/a_audio_files.py" [--audio DIR] [--out FILE]
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
AUDIO = os.path.join(REPO, "app", "public", "audio")
OUT = os.path.join(HERE, "out", "a_audio_files.csv")
SIL_NOISE, SIL_D = "-50dB", 1.0
EDGE_S = 0.05   # a silence within 50 ms of the start or the end counts as leading/trailing


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    if r.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}: {r.stderr}")
    j = json.loads(r.stdout)
    a = [s for s in j["streams"] if s.get("codec_type") == "audio"]
    if len(a) != 1:
        raise SystemExit(f"{path}: {len(a)} audio streams")
    s, f = a[0], j["format"]
    return {
        "codec": s.get("codec_name"),
        "sample_rate_hz": int(s.get("sample_rate")),
        "channels": int(s.get("channels")),
        "bit_rate_kbps": round(int(s.get("bit_rate") or f.get("bit_rate")) / 1000, 1),
        "duration_s": round(float(f["duration"]), 3),
        "n_streams": len(j["streams"]),
    }


def decode_errors(path):
    r = run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "null", "-"])
    return r.returncode, r.stderr.strip()


def loudness_and_silence(path):
    r = run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", path, "-af",
             f"volumedetect,silencedetect=noise={SIL_NOISE}:d={SIL_D}", "-f", "null", "-"])
    e = r.stderr
    mean = float(re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", e).group(1))
    mx = float(re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", e).group(1))
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", e)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end:\s*(-?[\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", e)]
    return mean, mx, starts, ends


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=AUDIO)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    with open(os.path.join(a.audio, "transcripts.json"), encoding="utf-8") as fh:
        order = list(json.load(fh))
    sums = {}
    with open(os.path.join(a.audio, "SHA256SUMS.txt"), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                h, n = line.split(None, 1)
                sums[n.strip().lstrip("*")] = h
    rows = []
    for name in order:
        p = os.path.join(a.audio, name)
        with open(p, "rb") as fh:
            data = fh.read()
        sha = hashlib.sha256(data).hexdigest()
        pr = probe(p)
        rc, err = decode_errors(p)
        mean, mx, starts, ends = loudness_and_silence(p)
        dur = pr["duration_s"]
        sil = []
        for i, st in enumerate(starts):
            en, d = ends[i] if i < len(ends) else (dur, dur - st)
            sil.append((st, en, d))
        inside = [s for s in sil if s[0] > EDGE_S and s[1] < dur - EDGE_S]
        rows.append({
            "file": name, "bytes": len(data), "sha256_ok": sha == sums.get(name),
            **pr,
            "decode_ok": rc == 0 and err == "", "decode_messages": err.replace("\n", " | "),
            "mean_volume_db": mean, "max_volume_db": mx,
            "silences_ge_1s_total": len(sil),
            "silences_ge_1s_inside": len(inside),
            "longest_inside_silence_s": round(max((s[2] for s in inside), default=0.0), 3),
            "silences_detail": "; ".join(f"{s[0]:.2f}-{s[1]:.2f}s ({s[2]:.2f}s)" for s in sil),
        })
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['file']:16s} {r['duration_s']:7.3f}s {r['codec']} {r['sample_rate_hz']} Hz ch={r['channels']} "
              f"{r['bit_rate_kbps']} kb/s mean={r['mean_volume_db']} max={r['max_volume_db']} "
              f"sil_inside={r['silences_ge_1s_inside']} decode_ok={r['decode_ok']} sha_ok={r['sha256_ok']}")
    num = ["duration_s", "sample_rate_hz", "channels", "bit_rate_kbps", "mean_volume_db", "max_volume_db",
           "silences_ge_1s_total", "silences_ge_1s_inside", "longest_inside_silence_s"]
    for c in num:
        v = [r[c] for r in rows]
        print(f"{c}: min {min(v)} max {max(v)}")
    print("codecs:", sorted({r["codec"] for r in rows}), "| decode_ok:", sum(r["decode_ok"] for r in rows), "of", len(rows),
          "| sha256_ok:", sum(r["sha256_ok"] for r in rows), "of", len(rows))
    print("wrote", a.out)
    bad = [r["file"] for r in rows if not (r["decode_ok"] and r["sha256_ok"])]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
