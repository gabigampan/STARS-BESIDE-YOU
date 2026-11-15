#!/usr/bin/env python3
"""Secret / personal-data scanner. Never prints secret values: only kind, location and first 4 chars + '…'.
Usage: scan.py history|tree|dir <path>  (run with cwd = repo for history/tree)"""
import json, re, subprocess, sys, os, hashlib

PATTERNS = [
    ("jwt", re.compile(rb"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("vercel_token", re.compile(rb"\b(?:vcp_|vercel_)[A-Za-z0-9_]{16,}")),
    ("vercel_token_assign", re.compile(rb"(?i)VERCEL_(?:TOKEN|OIDC_TOKEN|ACCESS_TOKEN)\s*[=:]\s*['\"]?[^\s'\"$<{]{8,}")),
    ("cesium_ion_assign", re.compile(rb"(?i)(?:ion\.defaultAccessToken|CESIUM_ION_TOKEN|accessToken)\s*[=:]\s*['\"`][^'\"`\s$]{20,}")),
    ("github_token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("aws_access_key", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret_assign", re.compile(rb"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+]{30,}")),
    ("aws_presigned", re.compile(rb"(?i)X-Amz-(?:Signature|Security-Token|Credential)=[A-Za-z0-9%/+_-]{8,}")),
    ("google_api_key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("google_oauth", re.compile(rb"ya29\.[0-9A-Za-z_-]{20,}|GOCSPX-[0-9A-Za-z_-]{10,}|\"type\"\s*:\s*\"service_account\"")),
    ("nasa_api_key", re.compile(rb"(?i)api_key=([A-Za-z0-9_]{6,})")),
    ("earthdata_cred", re.compile(rb"(?i)(?:urs\.earthdata\.nasa\.gov\s+login\s+\S+\s+password\s+\S+|EARTHDATA_(?:USERNAME|PASSWORD|TOKEN)\s*[=:]\s*['\"]?[^\s'\"$<{]{4,}|ee\.ServiceAccountCredentials)")),
    ("elevenlabs_key", re.compile(rb"(?i)xi-api-key['\"]?\s*[:=,]\s*['\"]?[^\s'\"$<{)]{8,}|\bsk_[A-Za-z0-9]{30,}")),
    ("openai_anthropic_key", re.compile(rb"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{30,}")),
    ("private_key", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer_header", re.compile(rb"(?i)\b(?:authorization\s*[:=]\s*['\"]?)?bearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("generic_assign", re.compile(rb"(?i)\b[A-Za-z0-9_]*(?:api[_-]?key|secret|password|passwd|token)[A-Za-z0-9_]*['\"]?\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]")),
    ("netrc_npmrc", re.compile(rb"(?im)^\s*machine\s+\S+\s+login\s+\S+\s+password\s+\S+|_authToken\s*=\s*[^\s$]{8,}")),
    ("presigned_url_other", re.compile(rb"(?i)[?&](?:sig|signature|token|access_token|X-Goog-Signature)=[A-Za-z0-9%._~+/-]{20,}")),
    ("keyword_loose", re.compile(rb"(?i)DEMO_KEY|api[_-]?key|apikey|access[_-]?token|client[_-]?secret|password|passwd|bearer|authorization:|xi-api-key|defaultAccessToken|VITE_CESIUM_ION_TOKEN|VERCEL_TOKEN|GITHUB_TOKEN|EARTHDATA|ee\\.Authenticate|ee\\.Initialize|_authToken|[?&]sig=")),
    ("email", re.compile(rb"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(rb"(?:\+|00)34[\s.-]?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b|(?<![\d.,-])[67]\d{2}[ ]\d{3}[ ]\d{3}(?![\d.,])|(?<![\d.,-])[67]\d{2}[ ]\d{2}[ ]\d{2}[ ]\d{2}(?![\d.,])")),
    ("national_id", re.compile(rb"(?<![A-Za-z0-9])(?:\d{8}-?[A-HJ-NP-TV-Z]|[XYZ]\d{7}-?[A-HJ-NP-TV-Z])(?![A-Za-z0-9])")),
    ("postal_address", re.compile(rb"(?i)\b(?:calle|c/|avda\.?|avenida|plaza|paseo)\s+[A-Za-z\xc0-\xff ]{3,40},?\s*(?:n[o\xba.]\s*)?\d{1,4}\b|\b29\d{3}\s+M[a\xe1]laga\b")),
]
PERSONAL = {"email", "phone", "national_id", "postal_address"}
DATA_EXT = (".csv", ".tsv", ".bin", ".img")

def mask(b):
    s = b.decode("utf-8", "replace")
    return s[:4] + "…"

def scan_bytes(data, path):
    out = []
    if b"\x00" in data[:8192]:
        return out, True
    is_data = path.lower().endswith(DATA_EXT)
    lines = None
    for kind, rx in PATTERNS:
        if kind in ("phone", "national_id") and (is_data or path.lower().endswith(".json")):
            continue  # numeric grids: too noisy, false positives only
        for m in rx.finditer(data):
            val = m.group(1) if m.groups() and m.group(1) else m.group(0)
            ln = data.count(b"\n", 0, m.start()) + 1
            # context class (without value): leading 40 chars before match
            ctx = data[max(0, m.start()-60):m.start()].split(b"\n")[-1].decode("utf-8", "replace")
            out.append({"kind": kind, "line": ln, "prefix": mask(val), "len": len(val),
                        "sha8": hashlib.sha256(val).hexdigest()[:8],
                        "ctx": re.sub(r"[A-Za-z0-9+/=_-]{16,}", "<…>", ctx)[-50:],
                        "full_match_kind_hint": mask(m.group(0)[:20])})
    return out, False

def history(repo):
    objs = subprocess.run(["git", "rev-list", "--all", "--objects"], cwd=repo, capture_output=True).stdout.decode().splitlines()
    blobs = {}
    for l in objs:
        parts = l.split(" ", 1)
        if len(parts) == 2:
            blobs.setdefault(parts[0], parts[1])
    # filter to blobs
    p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    res = []
    nbin = 0
    for sha, path in blobs.items():
        p.stdin.write((sha + "\n").encode()); p.stdin.flush()
        hdr = p.stdout.readline().split()
        typ, size = hdr[1].decode(), int(hdr[2])
        data = p.stdout.read(size); p.stdout.read(1)
        if typ != "blob":
            continue
        f, isbin = scan_bytes(data, path)
        nbin += isbin
        for x in f:
            x.update({"blob": sha[:8], "path": path}); res.append(x)
    p.stdin.close(); p.wait()
    return res, len(blobs), nbin

def walk_dir(root):
    res = []
    for d, _, fs in os.walk(root):
        for fn in fs:
            fp = os.path.join(d, fn)
            with open(fp, "rb") as fh:
                data = fh.read()
            f, _ = scan_bytes(data, fp)
            for x in f:
                x["path"] = os.path.relpath(fp, root); res.append(x)
    return res

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "history":
        res, n, nbin = history(sys.argv[2])
        json.dump({"objects": n, "binary_blobs": nbin, "findings": res}, sys.stdout)
    elif mode == "dir":
        json.dump({"findings": walk_dir(sys.argv[2])}, sys.stdout)
    elif mode == "tree":
        repo = sys.argv[2]
        files = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True).stdout.decode().split("\0")
        res = []
        for f in files:
            fp = os.path.join(repo, f)
            if not f or not os.path.isfile(fp):
                continue
            data = open(fp, "rb").read()
            r, _ = scan_bytes(data, f)
            for x in r:
                x["path"] = f; res.append(x)
        json.dump({"findings": res}, sys.stdout)
