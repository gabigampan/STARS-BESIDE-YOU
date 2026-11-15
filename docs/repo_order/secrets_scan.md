# Secrets and personal-data scan: Stars Beside You (before going public)

**Verdict: no real secret found in tree or history.**

## Scope

- Repository `/home/user/stars-beside-you`, HEAD `5a9d749` (final-integration), with uncommitted edits to README.md and docs/AI_USE.md.
- **History:** every object reachable from `git rev-list --all`. That is 188 commits across HEAD, main and 10 origin/* branches, and 2,514 unique objects. Text blobs were scanned once each. 172 binary blobs were skipped for the text patterns. Commit messages were scanned too.
- **Working tree:** the 667 files tracked at HEAD.
- **Zip:** `STARS-BESIDE-YOU-main (2).zip` has 60 entries. Its 50 files were extracted to `scratchpad/order/zipx` and scanned. Nothing was executed.
- **Local files outside git:**
  - `app/.env.local`
  - the Vercel token file under `/root/.config`
  - the local build in `app/dist`

  The values in these files were compared byte-for-byte against every git object, the zip and dist. Only hit counts were printed.
- **Patterns:**
  - JWT, `vcp_` and `vercel_` tokens, Cesium ion assignments
  - GitHub tokens: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_`
  - AWS: `AKIA`, `ASIA`, `aws_secret_access_key`, `X-Amz-*`
  - Google: `AIza`, `ya29.`, `GOCSPX-`, service_account
  - `api_key=` (including DEMO_KEY)
  - Earthdata and Earth Engine credentials
  - ElevenLabs: `xi-api-key`, `sk_`
  - `sk-` keys
  - PEM private keys
  - bearer and authorization headers
  - generic `api_key`, `secret`, `password`, `passwd` or `token` assignments that have a value
  - `.netrc` and `.npmrc` content
  - presigned URLs (`sig=`, `X-Goog-Signature`, `token=`)
  - personal data: e-mail addresses, Spanish phone numbers, DNI and NIE numbers, postal addresses
- **Self-test:** a scratch file with one dummy value of each kind triggered every detector.

## Counts per kind (history ∪ tree ∪ zip)

| Kind | Hits |
|---|---|
| JWT / Vercel / Cesium ion value / GitHub / AWS / presigned / Google / NASA api_key / DEMO_KEY / Earthdata / ElevenLabs / sk- / private key / bearer / netrc-npmrc | **0** |
| Generic secret-looking assignment | 5 (2 places, both harmless) |
| Keyword mentions with no value (docs, variable names) | 181 in history, 56 at HEAD, 4 in the zip |
| Key or .env files ever added | 1 (`app/.env.example`, an empty template) |
| E-mail, phone, national id or postal address in file content | **0** |
| E-mail addresses in commit messages | 140 (all `nor…@anthropic.com` Co-Authored-By trailers) |
| Distinct author/committer e-mails | 5 |

## Findings

| ID | Where | Commit | Kind / prefix | Decision |
|---|---|---|---|---|
| G1 | `tierra luna/audit/out/p5_shown_numbers_summary.json` lines 699, 707, 1203, 1211 | 98f95f5 | A JSON field named `"token"`, values `−28.…` and `−204…` | HARMLESS: numbers quoted by the audit, not credentials |
| G2 | `tierra luna/real_data/earth_sources.py:58` | 65d5677 | `CCI_TOKEN_URL = "http…"` | HARMLESS: the public Planetary Computer SAS endpoint URL. The token is fetched at runtime and never stored. No `sig=` appears anywhere in history. |
| E1 | `app/.env.example:3` | 2f3c4b8 | `VITE…` with empty values | HARMLESS: template only |
| K1 | READMEs, docs/, `scripts/deploy_vercel.sh`, `app/src/scene/ionUpgrade.ts`, `app/vite.config.ts`, `app/tests/smoke.mjs`, `tierra luna/config.py` | many | Variable names: `VITE_CESIUM_ION_TOKEN`, `VERCEL_TOKEN`, `Ion.defaultAccessToken = import.meta.env…`; Earthdata login URLs | HARMLESS: no values |
| K2 | `docs/audit_evidence/A1_inventory_tests.md:44,47` | in 185 snapshots | The regex names `AIza…` and `gith…` | HARMLESS: an earlier audit listing the patterns it searched for |
| C1 | `app/dist/assets/index-gOLdQ4gU.js` (untracked and git-ignored) | none | JWT `eyJh…` (sha256 8d3d978b) | HARMLESS: the same string is in `app/node_modules/cesium/Build/Cesium/index.js`. It is CesiumJS's own public default ion token. It is in 0 git objects, and no JWT exists anywhere in tree or history. |
| L1 | `app/.env.local` (git-ignored, never committed) | none | A real Cesium ion token, `eyJh…` | TO CHECK: found in 0 git objects, 0 zip files, 0 dist files. During the reorganisation, never `git add -f` it, and keep the `.env.*` ignore rule covering `app/`. |
| L2 | Vercel env file under `/root/.config`, outside the repo | none | `VERCEL_TOKEN=<masked>` | TO CHECK: found in 0 git objects. `deploy_vercel.sh` names only the file path. |
| P1 | Commit metadata | all | 5 distinct e-mails | TO CHECK: see the next section |
| P2 | Commit messages | 140 commits | 7 distinct `claude.ai/code/session_…` links | TO CHECK: the links require login, so they are not secrets. The team decides whether to keep them. |
| X1 | 69 tracked files (docs/audit_evidence, tierra luna/audit/out, ASSUMPTIONS.md, …) | many | Sandbox paths such as `/tmp/claude-0/…`, `/home/user`, `/root/.config` | HARMLESS: cosmetic. No personal user names. |

## Author e-mails the public history will expose

There are 5 distinct addresses:

- **2 real mailboxes:** `fac…@gmail.com` (3 times) and `fco…@gmail.com` (2 times). These are the only real personal data that going public will expose.
- **1 GitHub noreply:** `154…@users.noreply.github.com` (once).
- **2 automation addresses:**
  - `nor…@github.com` (6 times; the GitHub web-flow committer)
  - `nor…@anthropic.com` (366 author/committer uses, plus 140 trailers)

## Tracked files over 5 MB

These are not secrets, but they matter for a public repository.

| Bytes | Path |
|---|---|
| 14,031,467 | `STARS-BESIDE-YOU-main (2).zip` |
| 12,182,950 | `tierra luna/output_real/moon_real_1deg.csv` |
| 11,824,940 | `app/public/media/lunar-base/lunar-base.webm` |
| 11,168,347 | `app/public/media/lunar-base/lunar-base.mp4` |
| 8,723,185 | `tierra luna/output_real/earth_real_1deg.csv` |
| 7,115,011 | `app/public/media/solar/solar.mp4` |
| 6,199,981 | `app/public/media/solar/solar.webm` |
| 6,127,481 | `tierra luna/output_py/earth_moon_harmonized_clean.csv` |
| 5,990,400 | `tierra luna/data/cache/ldem_64.img.8894cdd5.rows_8466_8596.bin` |

History also keeps 7 older versions of the videos and of `moon_real_1deg.csv`, 7.9 to 11.8 MB each. The pack is 28 MiB.

## Tracked archives, caches and `__pycache__`

- **Archive:** `STARS-BESIDE-YOU-main (2).zip` is an old snapshot of the original main. It holds its own `__pycache__` and `data/cache` and contains no secrets. It goes to archive/ or is deleted from the tree.
- **`__pycache__`:** 8 files under `tierra luna/__pycache__/*.cpython-312.pyc`, plus `tierra luna/tests/__pycache__/test_pipeline.cpython-312-pytest-9.2.0.pyc`. They are already in .gitignore but still tracked, so they need `git rm --cached`. None of them contain personal home paths.
- **Cache:** `tierra luna/data/cache/` holds 13 files, 12.8 MB in total: PDS `.lbl` and `.img` files, row-slice `.bin` files, `earth_global_real.npz` and `moon_global_pds.npz`.
- **Other binaries:**
  - `tierra luna/research/out/r1_dem_{earth,moon}.npz`
  - `tierra luna/output_py/*.tif` (2 files)
- **App data:** `app/public/data/v2/*.bin` (30 files, 13 MB) is the app's data bundle by design. Keep it.

## Re-run

```
cd /home/user/stars-beside-you
S=/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/order
python3 -I $S/scan.py history . > $S/hist.json     # all objects of all refs; prints only kind/line/first 4 chars
python3 -I $S/scan.py tree . > $S/tree.json
python3 -I $S/scan.py dir $S/zipx > $S/zip.json
git log --all --diff-filter=A --name-only --format= | sort -u | grep -iE '(^|/)(\.env[^/]*|[^/]*\.pem|[^/]*\.key|id_rsa[^/]*|credentials[^/]*|token[^/]*|\.npmrc|\.netrc)$'
git rev-list --all | xargs git grep -I -l -E 'eyJ[A-Za-z0-9_-]{8,}\.eyJ|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pous]_[A-Za-z0-9]{30,}|github_pat_|vcp_|-----BEGIN [A-Z ]*PRIVATE KEY|api_key=' | cut -d: -f2- | sort | uniq -c
#   expected: only docs/audit_evidence/A1_inventory_tests.md (pattern names)
python3 -I $S/valcheck.py . app/.env.local <vercel env file>   # local secret values vs all git objects/zip/dist: counts only
git log --all --format='%ae%n%ce' | sort | uniq -c
```

**Verdict: no real secret found in tree or history.**
