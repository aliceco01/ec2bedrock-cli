"""Throughput capacity: can the profile's instance actually serve the workload?

Pure stdlib, no boto3. A profile's ``performance.expected_aggregate_tps`` is the
output-token throughput one instance is expected to sustain across all of its
concurrent requests: a number, or a ``"low-high"`` range string like
``"80-180"``. Capacity is checked on output (decode) tokens only; input tokens
are processed much faster (prefill), and the throughput figure is assumed to
already reflect a typical input mix.

Two answers come out of it, both asked for in issue #1:

* how many instances the workload needs, spread evenly over the window
  (``hours`` x ``days``), at the top of the profile's range; and
* the break-even utilization: how busy one instance must be for its hourly
  cost to equal what the token provider charges for the same tokens. Above
  1.0, EC2 cannot win on cost at those prices, however many instances run.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ec2bedrock.cost.breakeven import BreakEven
from ec2bedrock.cost.profiles import Profile

# Float headroom, so a workload at exactly the top of the range needs one
# instance, not two.
_EPSILON = 1e-9


@dataclass(frozen=True)
class Capacity:
    """How much of the profile's throughput a workload needs."""

    low_tps: float
    high_tps: float
    required_output_tps: float
    instances: int
    output_only_utilization: float | None
    io_aware_utilization: float | None

    def to_dict(self) -> dict:
        """Router-consumable payload (stable keys; ``None`` serialises to null)."""
        return {
            "expected_output_tps": {"low": self.low_tps, "high": self.high_tps},
            "required_output_tps": self.required_output_tps,
            "instances": self.instances,
            "break_even_utilization": {
                "output_only": self.output_only_utilization,
                "io_aware": self.io_aware_utilization,
            },
        }


def throughput_range(profile: Profile) -> tuple[float, float] | None:
    """Parse ``performance.expected_aggregate_tps`` into ``(low, high)`` tok/s.

    Returns ``None`` when the profile carries no usable figure, so callers skip
    the capacity check instead of failing.
    """
    raw = (profile.performance or {}).get("expected_aggregate_tps")
    if isinstance(raw, bool):  # bool is an int subclass, not a throughput
        return None
    if isinstance(raw, (int, float)):
        values = [float(raw)]
    elif isinstance(raw, str):
        try:
            values = [float(part) for part in raw.split("-")]
        except ValueError:
            return None
    else:
        return None
    if len(values) not in (1, 2):
        return None
    low, high = values[0], values[-1]
    if not (math.isfinite(low) and math.isfinite(high)) or low <= 0 or high < low:
        return None
    return low, high


def assess(
    profile: Profile,
    output_tokens: int,
    running_hours: float,
    break_even: BreakEven | None,
) -> Capacity | None:
    """Check *output_tokens* over *running_hours* against the profile's throughput.

    Returns ``None`` when the profile has no throughput figure or the window is
    empty.
    """
    rng = throughput_range(profile)
    if rng is None or running_hours <= 0:
        return None
    low, high = rng
    required = output_tokens / (running_hours * 3600)
    return Capacity(
        low_tps=low,
        high_tps=high,
        required_output_tps=required,
        instances=max(1, math.ceil(required / high - _EPSILON)),
        output_only_utilization=_share(break_even.output_only_tps if break_even else None, high),
        io_aware_utilization=_share(break_even.io_aware_tps if break_even else None, high),
    )


def notes_for(capacity: Capacity) -> list[str]:
    """Human notes for a comparison, in the order a reader needs them."""
    notes: list[str] = []
    if capacity.instances > 1:
        notes.append(
            f"needs {capacity.instances} instances: {capacity.required_output_tps:.0f} "
            f"output tok/s is more than one instance's {capacity.high_tps:g} tok/s"
        )
    elif capacity.required_output_tps > capacity.low_tps:
        notes.append(
            f"{capacity.required_output_tps:.0f} output tok/s is above the profile's low "
            f"estimate of {capacity.low_tps:g} tok/s; one instance may not keep up"
        )
    if capacity.io_aware_utilization is not None and capacity.io_aware_utilization > 1:
        notes.append(
            "break-even needs more throughput than one instance delivers: "
            "EC2 cannot win on cost at these prices"
        )
    return notes


def _share(tps: float | None, capacity_tps: float) -> float | None:
    return None if tps is None else tps / capacity_tps
