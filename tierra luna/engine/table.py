"""Reading the harmonized cell table into one frame per body, sorted by cell id."""
from __future__ import annotations

from typing import Dict

import pandas as pd

from engine.config import BODIES, GRID_COLS


def split_bodies(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Split a harmonized table by body, add ``id = row * 180 + col`` and sort by id.

    Values are not changed. Category columns stay strings; empty strings and NaN
    stay missing.
    """
    out: Dict[str, pd.DataFrame] = {}
    body_col = df["body"].astype(str).str.upper()
    for body in BODIES:
        part = df[body_col == body].copy()
        part["id"] = (part["row"].astype(int) * GRID_COLS + part["col"].astype(int)).astype(int)
        part = part.sort_values("id", kind="mergesort").reset_index(drop=True)
        out[body] = part
    return out


def load_cells(csv_path: str) -> Dict[str, pd.DataFrame]:
    """Load the harmonized CSV and split it by body (see :func:`split_bodies`)."""
    df = pd.read_csv(csv_path, keep_default_na=True)
    return split_bodies(df)
