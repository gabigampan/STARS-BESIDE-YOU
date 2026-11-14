"""Stars Beside You - Earth-Moon analog engine.

Wires the team's mission_scoring.py/json (gates and soft criteria) to a physical
Earth-Moon similarity, lunar twin pairing, confidence labels, computed place
names and a static bundle for the browser app. Datasets (input tables, grid,
provenance, column aliases, bundle format) are described in engine/datasets.json.

Run ``python -m engine build`` from the "tierra luna" directory (default dataset
real_1deg -> app/public/data/v2); ``--dataset legacy_2deg`` builds the legacy table
(v1 JSON, not shipped) for comparison.
"""
import json as _json
import os as _os

__all__ = ["__version__"]

# Single source of the version: engine_config.json "engine_version".
with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "engine_config.json"), encoding="utf-8") as _fh:
    __version__ = str(_json.load(_fh)["engine_version"]["value"])
