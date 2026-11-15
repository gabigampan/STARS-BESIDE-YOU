"""Run every validation metric of docs/VALIDATION.md and write validation/out/.

    cd "tierra luna" && python validation/run_all.py

Deterministic: no random numbers, no clock in the outputs; every table is sorted.
About 12 minutes on 4 shared CPUs (metrics 4 and 8 rerun one mission of the engine 56 times in memory).
Reads only; writes only validation/out/.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import write_json  # noqa: E402
import m1_coverage, m2_validity, m3_external, m4_sensitivity, m5_reproduction, m6_coordinates, m7_global, m8_improvements  # noqa: E402,E401


def main() -> int:
    summary = {}
    for name, mod in (("m1_coverage", m1_coverage), ("m2_validity", m2_validity), ("m3_external", m3_external),
                      ("m4_sensitivity", m4_sensitivity), ("m5_reproduction", m5_reproduction),
                      ("m6_coordinates", m6_coordinates), ("m7_global", m7_global), ("m8_improvements", m8_improvements)):
        t = time.time()
        summary[name] = mod.run()
        print(f"{name}: done in {time.time() - t:.0f} s", flush=True)
    write_json(summary, "summary.json")
    print("wrote validation/out/summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
