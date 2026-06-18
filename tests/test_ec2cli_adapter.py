"""t1 — ec2-cli coupling adapter: pinned API, offline/no-boto3, shape-normalised.

These tests are the milestone-1 contract for the ec2-cli seam:

- the ec2-cli ``estimate_cost`` API we depend on is pinned (fails loudly if a
  future ec2-cli changes the keyword signature);
- importing the cost domain pulls **no** boto3 and opens **no** socket;
- the adapter normalises *either* ec2-cli ``Estimate`` shape (0.5.x ``.figure``
  vs 0.6.x ``.compute``/``.ebs``) into ec2bedrock's :class:`CostBreakdown`.
"""

from __future__ import annotations

import inspect
import pathlib
import socket
import sys

import pytest

from ec2bedrock.cost import CostBreakdown, per_machine_cost
from ec2bedrock.cost._ec2cli import normalize_estimate

_COST_PKG = pathlib.Path(__file__).resolve().parent.parent / "ec2bedrock" / "cost"


def test_ec2cli_estimate_cost_signature_is_pinned():
    """The ec2-cli pricing API M1 imports must keep its injected-rate kwargs."""
    from ec2.aws.pricing import estimate_cost

    params = set(inspect.signature(estimate_cost).parameters)
    assert {"ondemand_rate", "spot_rate", "running_hours", "ebs_monthly"} <= params


def test_importing_cost_domain_does_not_pull_boto3():
    """Milestone-1 paths must stay boto3-free (boto3 is ec2-cli's [aws] extra)."""
    # ec2bedrock.cost is already imported at module load above.
    assert "boto3" not in sys.modules
    assert "botocore" not in sys.modules


def test_no_top_level_boto3_import_in_cost_package():
    """Static guard: no module under ec2bedrock/cost imports boto3 at top level."""
    banned = ("import boto3", "from boto3", "import botocore", "from botocore")
    offenders = []
    for path in _COST_PKG.glob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(banned):
                offenders.append(f"{path.name}: {stripped}")
    assert offenders == [], f"boto3 imported at top level in cost pkg: {offenders}"


def test_per_machine_cost_basic_arithmetic():
    """compute = hourly_usd × running_hours; total = compute + EBS; known, not UNKNOWN."""
    bd = per_machine_cost(hourly_usd=1.861, running_hours=176.0, ebs_monthly=10.0)
    assert bd.compute == pytest.approx(1.861 * 176.0)
    assert bd.ebs == pytest.approx(10.0)
    assert bd.total == pytest.approx(1.861 * 176.0 + 10.0)
    assert bd.unknown is False


def test_per_machine_cost_is_offline(monkeypatch):
    """The cost arithmetic must not open a socket — prove it by banning connect()."""

    def _no_network(*_a, **_k):  # pragma: no cover - only the raise matters
        raise AssertionError("milestone-1 cost path attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    bd = per_machine_cost(hourly_usd=1.861, running_hours=8.0, ebs_monthly=0.0)
    assert bd.total == pytest.approx(1.861 * 8.0)


def test_unknown_rate_degrades_not_raises():
    """A missing hourly rate degrades to an UNKNOWN total, never a crash."""
    bd = per_machine_cost(hourly_usd=None, running_hours=176.0, ebs_monthly=10.0)
    assert bd.compute is None
    assert bd.unknown is True
    assert bd.total is None


class _FigureEstimate:
    """Stand-in for ec2-cli 0.5.x Estimate (single combined ``.figure``)."""

    def __init__(self, figure, notes=()):
        self.figure = figure
        self.notes = list(notes)


class _SplitEstimate:
    """Stand-in for ec2-cli 0.6.x Estimate (explicit ``.compute`` / ``.ebs``)."""

    def __init__(self, compute, ebs, notes=()):
        self.compute = compute
        self.ebs = ebs
        self.notes = list(notes)


def test_normalize_recovers_split_from_05_figure_shape():
    """0.5.x .figure (compute+EBS combined) is split back using injected EBS."""
    bd = normalize_estimate(_FigureEstimate(330.0), ebs_monthly=10.0)
    assert isinstance(bd, CostBreakdown)
    assert bd.ebs == pytest.approx(10.0)
    assert bd.compute == pytest.approx(320.0)
    assert bd.total == pytest.approx(330.0)


def test_normalize_uses_native_fields_from_06_split_shape():
    """0.6.x .compute/.ebs are used directly (forward compatibility)."""
    bd = normalize_estimate(_SplitEstimate(320.0, 10.0), ebs_monthly=10.0)
    assert bd.compute == pytest.approx(320.0)
    assert bd.ebs == pytest.approx(10.0)
    assert bd.unknown is False
