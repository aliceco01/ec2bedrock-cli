"""Tests for ec2bedrock.cost.rates — bundled rate data."""

from __future__ import annotations

import pytest

from ec2bedrock.cost.rates import (
    DEFAULT_PROVIDER_INPUT_USD_PER_1M,
    DEFAULT_PROVIDER_OUTPUT_USD_PER_1M,
    EBS_USD_PER_GB_MONTH,
    WORKDAYS_PER_MONTH,
    ebs_monthly_usd,
    ebs_window_usd,
    provider_prices,
)


class TestConstants:
    def test_ebs_rate(self) -> None:
        assert EBS_USD_PER_GB_MONTH == 0.08

    def test_default_provider_prices(self) -> None:
        assert DEFAULT_PROVIDER_INPUT_USD_PER_1M == 0.58
        assert DEFAULT_PROVIDER_OUTPUT_USD_PER_1M == 3.01


class TestEbsMonthlyUsd:
    def test_default_rate(self) -> None:
        assert ebs_monthly_usd(200) == 200 * 0.08

    def test_custom_rate(self) -> None:
        assert ebs_monthly_usd(200, 0.05) == 10.0

    def test_none_storage(self) -> None:
        assert ebs_monthly_usd(None) == 0.0


class TestEbsWindowUsd:
    def test_one_month_of_workdays_is_one_month(self) -> None:
        assert ebs_window_usd(200, WORKDAYS_PER_MONTH) == pytest.approx(ebs_monthly_usd(200))

    def test_scales_with_days(self) -> None:
        assert ebs_window_usd(200, 1) == pytest.approx(16.0 / 22)
        assert ebs_window_usd(200, 66) == pytest.approx(48.0)

    def test_custom_rate_and_none_storage(self) -> None:
        assert ebs_window_usd(200, 22, 0.05) == pytest.approx(10.0)
        assert ebs_window_usd(None, 22) == 0.0


class TestProviderPrices:
    def test_defaults(self) -> None:
        assert provider_prices() == (0.58, 3.01)

    def test_custom(self) -> None:
        assert provider_prices(1.0, 2.0) == (1.0, 2.0)
