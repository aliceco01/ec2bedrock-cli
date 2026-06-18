"""Break-even analysis for EC2 vs token-provider costs.

Pure stdlib — no boto3, no ec2bedrock.cli imports.
"""

from __future__ import annotations

from dataclasses import dataclass


def output_only_breakeven_tps(
    hourly_usd: float,
    output_usd_per_1m: float,
) -> float | None:
    """Tokens/sec of output at which token-provider output cost equals the EC2 hourly rate.

    Returns ``None`` ("no finite break-even") when the output price is non-positive
    — the provider is never beaten on output. ``None`` serialises to JSON ``null``;
    a non-finite ``float('inf')`` would emit invalid JSON for a strict router.
    """
    if output_usd_per_1m <= 0:
        return None
    return hourly_usd / output_usd_per_1m * 1_000_000 / 3600


def io_aware_breakeven_tps(
    hourly_usd: float,
    input_usd_per_1m: float,
    output_usd_per_1m: float,
    input_output_ratio: float,
) -> float | None:
    """Break-even TPS when the provider also charges for input tokens.

    *input_output_ratio* is the number of input tokens per output token. Returns
    ``None`` (JSON ``null``) when the effective provider price is non-positive.
    """
    effective = input_output_ratio * input_usd_per_1m + output_usd_per_1m
    if effective <= 0:
        return None
    return hourly_usd / effective * 1_000_000 / 3600


@dataclass(frozen=True)
class BreakEven:
    """Break-even point for EC2 vs token-provider costs.

    A ``None`` TPS means "no finite break-even" (the provider is never beaten on
    that axis) — kept JSON-safe (``null``), never a non-finite float.
    """

    output_only_tps: float | None
    io_aware_tps: float | None
    input_output_ratio: float

    def to_dict(self) -> dict:
        """Return all fields as a plain dict."""
        return {
            "output_only_tps": self.output_only_tps,
            "io_aware_tps": self.io_aware_tps,
            "input_output_ratio": self.input_output_ratio,
        }


def break_even(
    hourly_usd: float,
    input_usd_per_1m: float,
    output_usd_per_1m: float,
    input_output_ratio: float,
) -> BreakEven:
    """Compute break-even points for EC2 vs token-provider costs."""
    return BreakEven(
        output_only_tps=output_only_breakeven_tps(hourly_usd, output_usd_per_1m),
        io_aware_tps=io_aware_breakeven_tps(
            hourly_usd, input_usd_per_1m, output_usd_per_1m, input_output_ratio
        ),
        input_output_ratio=input_output_ratio,
    )
