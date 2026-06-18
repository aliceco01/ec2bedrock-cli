"""Cost domain for ec2bedrock — the milestone-1 *prove-the-economics* layer.

This package answers issue #1's first-milestone question — *is self-managed EC2
cheaper than a token provider for this ADLC workload?* — entirely offline, with
no EC2 lifecycle, no model serving, and no live AWS. It couples to **ec2-cli**
for the per-machine cost arithmetic via the boto3-free :mod:`ec2.aws.pricing`
module; see :mod:`ec2bedrock.cost._ec2cli` for the adapter seam.

The stable public surface other modules build on:

- :class:`CostBreakdown` — ec2bedrock's own compute/EBS/total result type,
  independent of which ec2-cli ``Estimate`` shape is installed.
- :func:`per_machine_cost` — compute a breakdown from an injected hourly rate,
  running hours, and monthly EBS cost (the offline arithmetic).
"""

from __future__ import annotations

from ec2bedrock.cost._ec2cli import CostBreakdown, per_machine_cost

__all__ = ["CostBreakdown", "per_machine_cost"]
