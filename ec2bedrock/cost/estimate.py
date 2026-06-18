"""EC2 scheduled-cost estimate — milestone-1 task t5.

Pure stdlib — no boto3, no ec2bedrock.cli imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from ec2bedrock.cost import per_machine_cost
from ec2bedrock.cost.profiles import Profile
from ec2bedrock.cost.rates import ebs_monthly_usd


@dataclass(frozen=True)
class Ec2Estimate:
    """Scheduled-cost estimate for an EC2 instance."""

    hours_per_day: float
    days: float
    running_hours: float
    compute_usd: float | None
    ebs_usd: float | None
    total_usd: float | None
    unknown: bool
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Return all fields as a plain dict (notes as a list) for --json."""
        return {
            "hours_per_day": self.hours_per_day,
            "days": self.days,
            "running_hours": self.running_hours,
            "compute_usd": self.compute_usd,
            "ebs_usd": self.ebs_usd,
            "total_usd": self.total_usd,
            "unknown": self.unknown,
            "notes": list(self.notes),
        }


def estimate(profile: Profile, hours: float, days: float) -> Ec2Estimate:
    """Compute a scheduled-cost estimate for *profile* over *hours* × *days*."""
    running_hours = hours * days
    ebs = ebs_monthly_usd(profile.storage_gb)
    bd = per_machine_cost(
        hourly_usd=profile.hourly_usd,
        running_hours=running_hours,
        ebs_monthly=ebs,
    )
    return Ec2Estimate(
        hours_per_day=hours,
        days=days,
        running_hours=running_hours,
        compute_usd=bd.compute,
        ebs_usd=bd.ebs,
        total_usd=bd.total,
        unknown=bd.unknown,
        notes=tuple(bd.notes),
    )
