"""Display rounding of the per-pair sentences, shared by the engine, the tools and the browser.

Wording and display rounding, 2026-11-15 (docs/DATA_CONTRACT.md, contract revision 6):
a number printed in a per-pair sentence is the value the browser displays, and a number
derived from printed numbers (the share of sunlight lost in the atmosphere, ``{loss_pct}``
of ``texts.solar_limitation``) is computed from those printed numbers, in integers, so
the engine (Python) and the browser (JavaScript) cannot disagree on a half.

The displayed value of a stored float32 ``raw`` with ``d`` decimals:

1. ``x`` = the shortest decimal that rounds back to the same float32 (the browser's
   ``f32Decimal(raw)``; here ``np.format_float_positional(np.float32(raw), unique=True)``);
2. ``v = (x - subtract) * multiply`` in double precision (both languages do the same
   double arithmetic; with no subtract or multiply ``v = x``);
3. ``v`` written to ``d`` decimals rounding half up (half away from zero), on the
   shortest decimal of the double ``v`` (``Intl.NumberFormat`` in the browser, which
   rounds that decimal ``halfExpand``; ``Decimal(repr(v))`` with ``ROUND_HALF_UP`` here).

The share lost (``share_lost_percent``): ``A`` and ``G`` are the sunlight above the
atmosphere and at the ground as displayed with 1 decimal, as integers of tenths
(6.2 -> 62); the percentage is ``floor((200 * (A - G) + A) / (2 * A))``, i.e.
100 x (A - G) / A rounded half up, in integer arithmetic:

    Python:      (200 * (A - G) + A) // (2 * A)
    JavaScript:  Math.floor((200 * (A - G) + A) / (2 * A))

(exact in JavaScript too: numerator and denominator are small integers, and a quotient
of two integers with denominator 2A < 2^20 is never within rounding error of the next
integer unless it is that integer.) Number 1 Solar panels pair: 6.2 of 9.6 ->
A = 96, G = 62 -> floor(6896 / 192) = 35.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Any

import numpy as np

SHARE_LOST_RULE = "share_lost_of_displayed_tenths"
SHARE_LOST_PYTHON = "(200 * (A - G) + A) // (2 * A)"
SHARE_LOST_JAVASCRIPT = "Math.floor((200 * (A - G) + A) / (2 * A))"
TENTHS_JAVASCRIPT = ("const s = f32Decimal(raw).toFixed(12), i = s.indexOf('.'); "
                     "const T = Number(s.slice(0, i)) * 10 + Number(s[i + 1]) + (Number(s[i + 2]) >= 5 ? 1 : 0); "
                     "// raw >= 0; T/10 is exactly what Intl.NumberFormat shows with 1 decimal")


def f32_shortest(raw: float) -> str:
    """The shortest decimal string that rounds back to the float32 of ``raw`` (the
    browser's ``f32Decimal``)."""
    x = np.float32(raw)
    if not np.isfinite(x):
        raise ValueError(f"no displayed value for a missing value ({raw!r})")
    return np.format_float_positional(x, unique=True, trim="-")


def displayed(raw: float, decimals: int, subtract: float = 0.0, multiply: float = 1.0) -> Decimal:
    """The value the browser displays for a stored float32 ``raw`` (module docstring)."""
    v = (float(f32_shortest(raw)) - float(subtract)) * float(multiply)
    return Decimal(repr(v)).quantize(Decimal(1).scaleb(-int(decimals)), rounding=ROUND_HALF_UP)


def displayed_text(raw: float, decimals: int, subtract: float = 0.0, multiply: float = 1.0) -> str:
    """``displayed`` as the text printed in a sentence (no thousands separator)."""
    return format(displayed(raw, decimals, subtract, multiply), "f")


def tenths(raw: float) -> int:
    """The stored float32 ``raw`` as displayed with 1 decimal, as an integer of tenths (6.2 -> 62)."""
    return int(displayed(raw, 1).scaleb(1))


def share_lost_percent(above_raw: float, ground_raw: float) -> int:
    """Percentage of the sunlight above the atmosphere that does not reach the ground,
    from the two values as displayed (1 decimal each), rounded half up, in integers."""
    a, g = tenths(above_raw), tenths(ground_raw)
    if a <= 0:
        raise ValueError(f"sunlight above the atmosphere displays as {a / 10} : no share lost")
    return (200 * (a - g) + a) // (2 * a)


def to_fixed(x: float, decimals: int) -> str:
    """JavaScript ``Number.prototype.toFixed(decimals)`` of the double ``x``, exactly
    (ECMA-262: the integer n nearest to x * 10^d on the EXACT binary value of x; of two
    equally near, the larger n; a negative x is formatted as -(-x), so a half goes away
    from zero). Python's ``f"{x:.{d}f}"`` differs on exact binary halves only (it rounds
    them to even: 154.5 -> '154' where toFixed gives '155')."""
    x = float(x)
    if not np.isfinite(x):
        raise ValueError(f"no displayed value for a missing value ({x!r})")
    if x == 0.0:
        x = 0.0  # (-0).toFixed(d) is "0..." (toFixed tests x < 0, false for -0)
    q = Decimal(x).quantize(Decimal(1).scaleb(-int(decimals)), rounding=ROUND_HALF_UP)
    return format(q, "f")


def to_fixed_of_stored(raw: float, decimals: int, subtract: float = 0.0, multiply: float = 1.0) -> str:
    """The lunar_base_pair_sentence rule of docs/DATA_CONTRACT.md (earth_lunar_base_pairs.bin,
    'Per-pair sentence'): the stored float32 read as a double (what a Float32Array gives the
    browser), minus ``subtract``, times ``multiply``, in double precision, shown with
    ``toFixed(decimals)``. Used by the engine for explain.json so that its copy of the
    sentence is character for character what that rule prints (statistical audit
    2026-11-15, correction 3); templates with a ``display_rule`` (solar_limitation) use
    ``displayed`` instead."""
    v = (float(np.float32(raw)) - float(subtract)) * float(multiply)
    return to_fixed(v, decimals)


def fill_placeholder(spec: Dict[str, Any], values: Dict[str, float], display_rule: bool = True) -> str:
    """Text of one per-pair placeholder ({file, column, decimals[, subtract][, multiply]} or
    the share-lost rule {file, columns: {above, ground}, rule}) from the pair's stored
    values {column: value}. ``display_rule`` False: a template without a display_rule
    (lunar_base_pair_sentence), filled with ``to_fixed_of_stored``."""
    if spec.get("rule") == SHARE_LOST_RULE:
        cols = spec["columns"]
        return str(share_lost_percent(values[cols["above"]], values[cols["ground"]]))
    args = (values[spec["column"]], int(spec["decimals"]), float(spec.get("subtract", 0.0)), float(spec.get("multiply", 1.0)))
    return displayed_text(*args) if display_rule else to_fixed_of_stored(*args)
