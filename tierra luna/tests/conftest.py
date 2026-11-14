"""Shared test setup.

analog_finder.get_rover_preset_bundle() rewrites the tracked file
data/presets/presets.json (new frozen_at) every time the old pipeline runs, and
the existing tests run it. This session-scoped fixture snapshots that file and
restores it byte for byte after the test session, so running the tests leaves
the working tree unchanged. It does not alter what any test checks.
"""
import os

import pytest

PRESETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "presets", "presets.json")


@pytest.fixture(scope="session", autouse=True)
def _restore_tracked_presets():
    original = open(PRESETS, "rb").read() if os.path.exists(PRESETS) else None
    yield
    if original is not None:
        with open(PRESETS, "wb") as fh:
            fh.write(original)
