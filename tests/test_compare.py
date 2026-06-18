"""Tests for ec2bedrock.cost.compare — EC2 vs token-provider comparison.

The economics: EC2 is a fixed scheduled monthly cost, the provider is
pay-per-token. So EC2 wins at HIGH sustained volume and the provider wins at
LOW/sporadic volume — and near parity is "mixed" (roughly break-even).
"""

from __future__ import annotations

import pytest

from ec2bedrock.cost.compare import compare
from ec2bedrock.cost.profiles import DEFAULT_PROFILES


class TestCompare:
    profile = DEFAULT_PROFILES["qwen27b-awq-l40s"]

    def test_issue_1_worked_example_is_mixed(self) -> None:
        # Issue #1: EC2 ~$343.54/mo vs provider ~$354.60/mo -> roughly break-even.
        result = compare(
            self.profile,
            input_tokens=300_000_000,
            output_tokens=60_000_000,
            hours=8,
            days=22,
            input_usd_per_1m=0.58,
            output_usd_per_1m=3.01,
        )
        expected_provider = 300_000_000 * 0.58 / 1e6 + 60_000_000 * 3.01 / 1e6
        assert result.provider_usd == pytest.approx(expected_provider)  # ~354.6
        assert result.ec2_usd == pytest.approx(343.536)
        assert result.recommendation == "mixed"
        assert result.exit_code == 21

    def test_low_volume_favours_token_provider(self) -> None:
        # Tiny token volume: provider ~$3.59 << fixed EC2 ~$343.5/mo.
        result = compare(
            self.profile,
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            hours=8,
            days=22,
        )
        assert result.recommendation == "token-provider"
        assert result.exit_code == 20

    def test_high_volume_favours_ec2(self) -> None:
        # Huge sustained volume: provider ~$11,820 >> fixed EC2 ~$343.5/mo.
        result = compare(
            self.profile,
            input_tokens=10_000_000_000,
            output_tokens=2_000_000_000,
            hours=8,
            days=22,
        )
        assert result.recommendation == "ec2"
        assert result.exit_code == 0

    def test_unknown_ec2_cost_falls_back_to_provider(self) -> None:
        # A profile with no hourly rate -> EC2 cost UNKNOWN -> cannot justify EC2.
        from dataclasses import replace

        no_rate = replace(self.profile, hourly_usd=None)
        result = compare(no_rate, input_tokens=10**12, output_tokens=10**11, hours=8, days=22)
        assert result.ec2_usd is None
        assert result.recommendation == "token-provider"
        assert result.exit_code == 20

    def test_to_dict_has_router_keys(self) -> None:
        result = compare(
            self.profile,
            input_tokens=300_000_000,
            output_tokens=60_000_000,
            hours=8,
            days=22,
        )
        d = result.to_dict()
        for key in (
            "ec2_usd",
            "provider_usd",
            "recommendation",
            "exit_code",
            "break_even",
            "input_tokens",
            "output_tokens",
            "notes",
        ):
            assert key in d
