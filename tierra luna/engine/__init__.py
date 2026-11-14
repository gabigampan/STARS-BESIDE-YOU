"""Stars Beside You - Earth-Moon analog engine.

Wires the team's mission_scoring.py/json (gates and soft criteria) to a physical
Earth-Moon similarity, lunar twin pairing, confidence labels, computed place
names and a static JSON bundle for the browser app.

Run ``python -m engine build`` from the "tierra luna" directory.
"""
import json as _json
import os as _os

__all__ = ["__version__"]

# Single source of the version: engine_config.json "engine_version".
with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "engine_config.json"), encoding="utf-8") as _fh:
    __version__ = str(_json.load(_fh)["engine_version"]["value"])
