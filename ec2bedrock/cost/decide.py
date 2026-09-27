"""Router verdict — milestone-1 task t8.

Pure domain logic: given a workload label and token volumes, return a
router-consumable :class:`Decision` (``ec2``, ``token-provider``, or
``mixed``) with a human reason and a deterministic exit code.

No boto3, no ``ec2bedrock.cli`` imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from ec2bedrock.cost.compare import compare
from ec2bedrock.cost.profiles import DEFAULT_PROFILES, Profile

# Workload classes from issue #1 routing rules.
TOKEN_PROVIDER_WORKLOADS = frozenset({"sporadic", "interactive", "off-hours"})
SUSTAINED_WORKLOADS = frozenset({"batch", "meeting-mode", "ci"})
# Issue #1 also lists ``sensitive`` as a workload class hint; it routes exactly
# like the ``sensitive=True`` flag, never through the cost comparison.
SENSITIVE_WORKLOAD = "sensitive"
# Every documented class; the CLI accepts only these.
WORKLOAD_CLASSES = TOKEN_PROVIDER_WORKLOADS | SUSTAINED_WORKLOADS | {SENSITIVE_WORKLOAD}


@dataclass(frozen=True)
class Decision:
    """Router verdict with a human-readable reason and exit code."""

    target: str
    reason: str
    exit: int

    def to_dict(self) -> dict:
        """Structured payload with stable keys."""
        return {"decision": self.target, "reason": self.reason, "exit": self.exit}


def decide(
    workload: str,
    input_tokens: int,
    output_tokens: int,
    *,
    sensitive: bool = False,
    profile: Profile | None = None,
    hours: float = 8.0,
    days: float = 22.0,
    input_usd_per_1m: float | None = None,
    output_usd_per_1m: float | None = None,
) -> Decision:
    """Return a router verdict for *workload* given token volumes.

    Routing rules (issue #1):
    1. Sensitive workloads (``sensitive=True`` or the ``sensitive`` class) stay
       on self-managed EC2.
    2. Token-provider workloads (sporadic, interactive, off-hours) route
       to a token provider.
    3. Sustained or unknown workloads are cost-driven (EC2 vs provider).
    """
    prof = profile if profile is not None else DEFAULT_PROFILES["qwen27b-awq-l40s"]

    if sensitive or workload == SENSITIVE_WORKLOAD:
        return Decision("ec2", "sensitive workload kept on self-managed EC2", 0)

    if workload in TOKEN_PROVIDER_WORKLOADS:
        return Decision("token-provider", f"{workload} traffic favours a token provider", 20)

    # Sustained or unknown workload -> cost-driven.
    cmp = compare(
        prof,
        input_tokens,
        output_tokens,
        hours=hours,
        days=days,
        input_usd_per_1m=input_usd_per_1m,
        output_usd_per_1m=output_usd_per_1m,
    )
    fleet = ""
    if cmp.capacity is not None and cmp.capacity.instances > 1:
        fleet = f" for {cmp.capacity.instances} instances"
    reason = (
        f"cost-driven ({workload}): EC2 {_usd(cmp.ec2_usd)}{fleet} "
        f"vs provider {_usd(cmp.provider_usd)}"
    )
    return Decision(cmp.recommendation, reason, cmp.exit_code)


def _usd(amount: float | None) -> str:
    """Dollars and cents for the human reason; ``unknown`` when not computable."""
    return "unknown" if amount is None else f"${amount:,.2f}"
