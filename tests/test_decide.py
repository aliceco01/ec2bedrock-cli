"""Tests for ec2bedrock.cost.decide — router verdict (milestone-1 task t8).

The decide function encodes issue #1's routing rules:
1. Sensitive workloads stay on EC2.
2. Token-provider workloads (sporadic, interactive, off-hours) route to a provider.
3. Sustained/unknown workloads are cost-driven (EC2 vs provider).
"""

from __future__ import annotations

from ec2bedrock.cost.decide import decide


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
