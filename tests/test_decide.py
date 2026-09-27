"""Tests for ec2bedrock.cost.decide — router verdict (milestone-1 task t8).

The decide function encodes issue #1's routing rules:
1. Sensitive workloads (the flag or the `sensitive` class) stay on EC2.
2. Token-provider workloads (sporadic, interactive, off-hours) route to a provider.
3. Sustained/unknown workloads are cost-driven (EC2 vs provider).
"""

from __future__ import annotations

from dataclasses import replace

from ec2bedrock.cost.decide import WORKLOAD_CLASSES, decide
from ec2bedrock.cost.profiles import DEFAULT_PROFILES


class TestDecide:
    def test_sensitive_workload_wins(self) -> None:
        # Issue #1 example: sensitive flag overrides everything.
        d = decide("meeting-mode", 3_000_000, 500_000, sensitive=True)
        assert d.target == "ec2"
        assert d.exit == 0
        assert d.to_dict()["decision"] == "ec2"

    def test_sporadic_routes_to_token_provider(self) -> None:
        # Sporadic traffic favours a token provider regardless of volume.
        d = decide("sporadic", 1000, 1000)
        assert d.target == "token-provider"
        assert d.exit == 20

    def test_sustained_batch_high_volume_favours_ec2(self) -> None:
        # Huge sustained volume: EC2 fixed cost << provider pay-per-token.
        d = decide("batch", 10_000_000_000, 2_000_000_000)
        assert d.target == "ec2"
        assert d.exit == 0

    def test_sustained_batch_low_volume_favours_provider(self) -> None:
        # Low volume: provider pay-per-token << fixed EC2 cost.
        d = decide("batch", 1_000_000, 1_000_000)
        assert d.target == "token-provider"
        assert d.exit == 20

    def test_to_dict_has_required_keys(self) -> None:
        d = decide("batch", 1_000_000, 1_000_000)
        keys = set(d.to_dict().keys())
        assert "decision" in keys
        assert "reason" in keys
        assert "exit" in keys

    def test_sensitive_workload_class_routes_to_ec2(self) -> None:
        # Issue #1 lists `sensitive` as a workload class. It must not fall
        # through to the cost comparison, which picks the provider here.
        d = decide("sensitive", 3_000_000, 500_000)
        assert d.target == "ec2"
        assert d.exit == 0

    def test_workload_classes_cover_issue_1_hints(self) -> None:
        assert {"interactive", "meeting-mode", "batch", "sensitive"} <= WORKLOAD_CLASSES

    def test_reason_prints_dollars_and_cents(self) -> None:
        d = decide("batch", 1_000_000, 1_000_000)
        assert d.reason == "cost-driven (batch): EC2 $343.54 vs provider $3.59"

    def test_reason_with_unknown_ec2_cost(self) -> None:
        no_rate = replace(DEFAULT_PROFILES["qwen27b-awq-l40s"], hourly_usd=None)
        d = decide("batch", 1_000_000, 1_000_000, profile=no_rate)
        assert d.reason == "cost-driven (batch): EC2 unknown vs provider $3.59"
        assert d.target == "token-provider"
