"""argparse ``type=`` validators for the cost verbs (estimate / compare / decide).

A validator raises :class:`argparse.ArgumentTypeError`; argparse turns that into
``parser.error()``, which ``_CliArgumentParser`` routes through the structured
error path (exit 1 with a ``hint:`` line). Bad numbers are rejected at the edge
and never reach the cost arithmetic, so a router cannot receive a negative cost
or a verdict computed from a typo.
"""

from __future__ import annotations

import argparse
import math
from typing import Callable


def _parse(value: str, cast: Callable[[str], float], kind: str) -> float:
    try:
        n = cast(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not {kind}: {value!r}") from None
    if not math.isfinite(n):
        raise argparse.ArgumentTypeError(f"not a finite number: {value!r}")
    return n


def token_count(value: str) -> int:
    """A token total: a whole number, 0 or more."""
    n = int(_parse(value, int, "a whole number"))
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return n


def hours_per_day(value: str) -> float:
    """Instance hours per day: more than 0 and at most 24."""
    n = _parse(value, float, "a number")
    if not 0 < n <= 24:
        raise argparse.ArgumentTypeError(f"must be more than 0 and at most 24, got {value}")
    return n


def day_count(value: str) -> float:
    """Days the instance runs in the window: more than 0."""
    n = _parse(value, float, "a number")
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be more than 0, got {value}")
    return n


def usd_price(value: str) -> float:
    """A USD price, 0 or more (0 is a valid free price)."""
    n = _parse(value, float, "a number")
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return n
