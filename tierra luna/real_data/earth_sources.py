"""Keyless, open Earth data sources used by build_earth.py, plus a polite downloader.

Every file is fetched from an anonymous public URL (no account, login or key).
Each host gets at least the delay its robots.txt asks for (Crawl-delay) and never
more than one request per second. Each download is recorded in
real_data/manifest_earth.csv with URL, size and sha256 so the build can be repeated.

Planetary Computer blobs (ESA CCI land cover) need a short-lived *anonymous* SAS
token from https://planetarycomputer.microsoft.com/api/sas/v1/token/... (no account);
the token is appended at download time and never written to the manifest.
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
import subprocess
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest_earth.csv"
DEFAULT_RAW = Path(os.environ.get(
    "EARTH_RAW_DIR",
    "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/earth_raw",
))
# Generic client name only: no personal or project detail in requests.
USER_AGENT = "Mozilla/5.0 (compatible; open-data-script)"

# Minimum seconds between requests per host (robots.txt Crawl-delay where given).
HOST_DELAY = {
    "www.ngdc.noaa.gov": 60.0,      # robots.txt Crawl-delay: 60
    "zenodo.org": 10.0,             # robots.txt Crawl-delay: 10
    "store.pangaea.de": 2.0,
    "geodata.ucdavis.edu": 1.0,
    "landcoverdata.blob.core.windows.net": 1.0,
    "planetarycomputer.microsoft.com": 1.0,
}
_last_hit: dict[str, float] = {}

ETOPO_URL = ("https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/"
             "60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc")
WORLDCLIM_URL = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_{var}.zip"
WORLDCLIM_VARS = ["tmin", "wind", "prec", "srad"]
# OpenLandMap long-term MODIS MOD11A2 LST climatology 2000-2017 (Hengl 2018, Zenodo 1420115)
LST_URL = ("https://zenodo.org/api/records/1420115/files/"
           "clm_lst_mod11a2.{period}.{stat}_m_1km_s0..0cm_2000..2017_v1.0.tif/content")
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
PERMAFROST_NH_URL = ("https://store.pangaea.de/Publications/ObuJ-etal_2018/"
                     "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip")
PERMAFROST_ANT_URL = ("https://store.pangaea.de/Publications/ObuJ-etal_2019/"
                      "UiO_PEX_PERPROB_5.0_20181205_2000_2017_ANT.zip")
CCI_TILE_URL = ("https://landcoverdata.blob.core.windows.net/esa-cci-lc/cog/v2.1.1/{tile}/2020/"
                "C3S-LC-L4-LCCS-Map-300m-P1Y-2020-v2.1.1-{tile}-lccs_class.tif")
CCI_TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landcoverdata/esa-cci-lc"
CCI_TILES = [f"{la}{lo}" for la in ("N45", "N00", "S45", "S90")
             for lo in ("W180", "W135", "W090", "W045", "E000", "E045", "E090", "E135")]

_sas_token: tuple[float, str] | None = None


def _wait(host: str) -> None:
    delay = HOST_DELAY.get(host, 1.0)
    last = _last_hit.get(host)
    if last is not None:
        dt = time.monotonic() - last
        if dt < delay:
            time.sleep(delay - dt)
    _last_hit[host] = time.monotonic()


def _curl(url: str, out: Path) -> None:
    host = urllib.parse.urlparse(url).hostname or ""
    _wait(host)
    tmp = out.with_suffix(out.suffix + ".part")
    cmd = ["curl", "-sS", "-L", "--fail", "--retry", "3", "--retry-delay", "15",
           "-A", USER_AGENT, "-o", str(tmp), url]
    subprocess.run(cmd, check=True)
    tmp.rename(out)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_rows() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, newline="") as f:
        return {r["local_name"]: r for r in csv.DictReader(f)}


def _manifest_write(rows: dict[str, dict]) -> None:
    cols = ["local_name", "url", "size_bytes", "sha256", "retrieved_utc", "kept_on_disk", "note"]
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in cols})


def record(local: Path, url: str, kept: bool, note: str = "") -> None:
    digest = _sha256(local)
    with _lock():
        rows = _manifest_rows()
        rows[local.name] = {
            "local_name": local.name, "url": url, "size_bytes": local.stat().st_size,
            "sha256": digest,
            "retrieved_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kept_on_disk": "yes" if kept else "no (deleted after aggregation)", "note": note,
        }
        _manifest_write(rows)


def mark_deleted(local_name: str) -> None:
    with _lock():
        rows = _manifest_rows()
        if local_name in rows:
            rows[local_name]["kept_on_disk"] = "no (deleted after aggregation)"
            _manifest_write(rows)


class _lock:
    """Exclusive file lock so parallel downloaders can share the manifest."""

    def __enter__(self):
        import fcntl
        DEFAULT_RAW.mkdir(parents=True, exist_ok=True)
        self._f = open(DEFAULT_RAW / ".manifest_earth.lock", "w")
        fcntl.flock(self._f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        import fcntl
        fcntl.flock(self._f, fcntl.LOCK_UN)
        self._f.close()


def verify(local: Path) -> bool:
    """True if the local file matches the sha256 recorded in the manifest."""
    row = _manifest_rows().get(local.name)
    return bool(row) and local.exists() and _sha256(local) == row["sha256"]


def fetch(url: str, out: Path, note: str = "", keep: bool = True) -> Path:
    """Download url to out once (skipped when the file is present), then record it."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.name in _manifest_rows():
        return out
    if not out.exists():
        print(f"  downloading {url}", flush=True)
        _curl(url, out)
    record(out, url, kept=keep, note=note)
    return out


def _cci_token() -> str:
    global _sas_token
    if _sas_token and time.time() < _sas_token[0]:
        return _sas_token[1]
    _wait("planetarycomputer.microsoft.com")
    res = subprocess.run(["curl", "-sS", "--fail", "-A", USER_AGENT, CCI_TOKEN_URL],
                         check=True, capture_output=True, text=True)
    tok = json.loads(res.stdout)["token"]
    _sas_token = (time.time() + 1800, tok)
    return tok


def fetch_cci_tile(tile: str, out: Path) -> Path:
    url = CCI_TILE_URL.format(tile=tile)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.name in _manifest_rows():
        return out
    if not out.exists():
        print(f"  downloading {url}", flush=True)
        _curl(url + "?" + _cci_token(), out)
    record(out, url, kept=True, note="anonymous Planetary Computer SAS token appended at download time")
    return out
