"""EC2 vs token-provider cost comparison — milestone-1 task t7.

Pure domain logic — no boto3, no ec2bedrock.cli imports. Answers issue #1's
headline question: *is self-managed EC2 cheaper than a token provider for this
workload?* — and encodes the answer in a router-consumable recommendation plus a
deterministic process exit code.
"""

from __future__ import annotations

from dataclasses import dataclass

from ec2bedrock.cost.breakeven import BreakEven, break_even
from ec2bedrock.cost.capacity import Capacity, assess, notes_for
from ec2bedrock.cost.estimate import estimate
from ec2bedrock.cost.profiles import Profile
from ec2bedrock.cost.rates import provider_prices

# The decision -> exit-code contract a router can branch on. ``ec2`` maps to 0
# (success + recommend EC2, matching issue #1's ``decide`` example); the other
# decisions use codes clear of the scaffold's 1 (user error) / 2 (env error).
DECISION_EXIT_CODES: dict[str, int] = {"ec2": 0, "token-provider": 20, "mixed": 21}

# Within this relative band the two options are "roughly break-even" -> mixed.
_MIXED_BAND: float = 0.05


@dataclass(frozen=True)
class Comparison:
    """Result of an EC2 vs token-provider cost comparison."""

    ec2_usd: float | None
    provider_usd: float
    recommendation: str
    break_even: BreakEven | None
    input_tokens: int
    output_tokens: int
    notes: tuple[str, ...] = ()
    capacity: Capacity | None = None

    @property
    def exit_code(self) -> int:
        """The router-facing exit code for :attr:`recommendation`."""
        return DECISION_EXIT_CODES[self.recommendation]

    def to_dict(self) -> dict:
        """Router-consumable structured payload (stable keys)."""
        return {
            "ec2_usd": self.ec2_usd,
            "provider_usd": self.provider_usd,
            "recommendation": self.recommendation,
            "exit_code": self.exit_code,
            "break_even": self.break_even.to_dict() if self.break_even else None,
            "capacity": self.capacity.to_dict() if self.capacity else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "notes": list(self.notes),
        }


def compare(
    profile: Profile,
    input_tokens: int,
    output_tokens: int,
    *,
    hours: float,
    days: float,
    input_usd_per_1m: float | None = None,
    output_usd_per_1m: float | None = None,
) -> Comparison:
    """Compare scheduled EC2 cost against token-provider cost for a workload.

    EC2 is a fixed scheduled cost (``hours`` × ``days`` of the profile's hourly
    rate + EBS); the token provider is pay-per-token. EC2 therefore wins at high
    sustained volume and the provider wins at low/sporadic volume — the whole
    ADLC economics question issue #1 frames.

    The EC2 side is priced for as many instances as the output tokens need at
    the profile's ``expected_aggregate_tps`` (see :mod:`ec2bedrock.cost.capacity`);
    a profile without that figure is priced as one instance.
    """
    in_price, out_price = provider_prices(input_usd_per_1m, output_usd_per_1m)

    provider_usd = input_tokens * in_price / 1_000_000 + output_tokens * out_price / 1_000_000
    per_instance_usd = estimate(profile, hours, days).total_usd
    ratio = (input_tokens / output_tokens) if output_tokens else 0.0
    # No hourly rate -> no break-even to compute (would divide by a missing rate).
    # Use `is not None` so a legitimate 0.0 rate is still a known rate, not "missing".
    be = (
        break_even(profile.hourly_usd, in_price, out_price, ratio)
        if profile.hourly_usd is not None
        else None
    )

    capacity = assess(profile, output_tokens, hours * days, be)
    ec2_usd = per_instance_usd
    notes: list[str] = []
    if capacity is not None:
        if per_instance_usd is not None:
            ec2_usd = per_instance_usd * capacity.instances
        notes.extend(notes_for(capacity))
    if ec2_usd is None:
        recommendation = "token-provider"
        notes.append("EC2 cost UNKNOWN — cannot justify EC2")
    else:
        rel = abs(ec2_usd - provider_usd) / max(ec2_usd, provider_usd, 1e-9)
        if rel <= _MIXED_BAND:
            recommendation = "mixed"
        elif ec2_usd < provider_usd:
            recommendation = "ec2"
        else:
            recommendation = "token-provider"

    return Comparison(
        ec2_usd=ec2_usd,
        provider_usd=provider_usd,
        recommendation=recommendation,
        break_even=be,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        notes=tuple(notes),
        capacity=capacity,
    )
