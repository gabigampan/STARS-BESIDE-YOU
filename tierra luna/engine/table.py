"""Reading a cell table into one frame per body, sorted by cell id.

The grid comes from the dataset descriptor (engine/datasets.json); see engine/dataset.py
for the full loader (aliases, provenance). These helpers are kept for callers that
read one CSV with both bodies.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

from engine.dataset import Grid
from engine.dataset import split_bodies as _split


def split_bodies(df: pd.DataFrame, grid: Grid) -> Dict[str, pd.DataFrame]:
    """Split a table by body, add ``id = row * grid.cols + col`` and sort by id."""
    return _split(df, grid)


def load_cells(csv_path: str, grid: Grid) -> Dict[str, pd.DataFrame]:
    """Load a CSV holding both bodies and split it by body (see :func:`split_bodies`)."""
    return _split(pd.read_csv(csv_path, keep_default_na=True), grid)
