"""Tests for ec2bedrock.cost.estimate — scheduled-cost estimate."""

from __future__ import annotations

import pytest

from ec2bedrock.cost.estimate import estimate
from ec2bedrock.cost.profiles import DEFAULT_PROFILES


class TestEstimate:
    def test_qwen27b_l40s_monthly(self) -> None:
        e = estimate(DEFAULT_PROFILES["qwen27b-awq-l40s"], 8, 22)
        assert e.running_hours == 176
        assert e.compute_usd == pytest.approx(1.861 * 176)
        assert e.ebs_usd == pytest.approx(16.0)
        assert e.total_usd == pytest.approx(343.536)
        assert e.unknown is False

    def test_to_dict_total_usd(self) -> None:
        e = estimate(DEFAULT_PROFILES["qwen27b-awq-l40s"], 8, 22)
        assert e.to_dict()["total_usd"] == pytest.approx(343.536)

    def test_reproducibility(self) -> None:
        e1 = estimate(DEFAULT_PROFILES["qwen27b-awq-l40s"], 8, 22)
        e2 = estimate(DEFAULT_PROFILES["qwen27b-awq-l40s"], 8, 22)
        assert e1.total_usd == e2.total_usd
