"""Bundled rate data for ec2bedrock cost calculations.

Pure stdlib — no boto3, no imports from ec2bedrock.cli.
"""

from __future__ import annotations

EBS_USD_PER_GB_MONTH: float = 0.08
"""Bundled default EBS gp3 USD/GB-month rate."""

WORKDAYS_PER_MONTH: float = 22.0
"""Working days in a month: the default ``--days 22`` window is one month."""

DEFAULT_PROVIDER_INPUT_USD_PER_1M: float = 0.58
"""Default token-provider input price (USD per 1M tokens)."""

DEFAULT_PROVIDER_OUTPUT_USD_PER_1M: float = 3.01
"""Default token-provider output price (USD per 1M tokens)."""


def ebs_monthly_usd(storage_gb: float, rate_per_gb_month: float | None = None) -> float:
    """Return monthly EBS cost in USD for *storage_gb* at the given rate.

    Uses :data:`EBS_USD_PER_GB_MONTH` when *rate_per_gb_month* is ``None``.
    Treats ``None`` storage as 0.0. Never raises.
    """
    if storage_gb is None:
        storage_gb = 0.0
    rate = rate_per_gb_month if rate_per_gb_month is not None else EBS_USD_PER_GB_MONTH
    return storage_gb * rate


def ebs_window_usd(
    storage_gb: float,
    days: float,
    rate_per_gb_month: float | None = None,
) -> float:
    """Return the EBS cost in USD for a window of *days* working days.

    EBS bills per GB-month whether or not the instance runs, so the monthly
    charge is spread over :data:`WORKDAYS_PER_MONTH` working days: 22 days
    carry one month of storage, 1 day carries 1/22 of it, 44 days carry two
    months. Never raises.
    """
    return ebs_monthly_usd(storage_gb, rate_per_gb_month) * days / WORKDAYS_PER_MONTH


def provider_prices(
    input_usd_per_1m: float | None = None,
    output_usd_per_1m: float | None = None,
) -> tuple[float, float]:
    """Return (input, output) token-provider prices in USD per 1M tokens.

    Falls back to :data:`DEFAULT_PROVIDER_INPUT_USD_PER_1M` and
    :data:`DEFAULT_PROVIDER_OUTPUT_USD_PER_1M` when the arguments are ``None``.
    Never raises.
    """
    inp = input_usd_per_1m if input_usd_per_1m is not None else DEFAULT_PROVIDER_INPUT_USD_PER_1M
    out = output_usd_per_1m if output_usd_per_1m is not None else DEFAULT_PROVIDER_OUTPUT_USD_PER_1M
    return (inp, out)
