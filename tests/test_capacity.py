"""Tests for ec2bedrock.cost.capacity and the capacity-aware compare / decide.

Before this, compare priced one instance for any volume: 1B output tokens in the
default window came out as a $343.54 EC2 win, although one g6e.xlarge at the
profile's 80-180 tok/s serves at most ~114M output tokens in 176 hours.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from ec2bedrock.cost.capacity import assess, throughput_range
from ec2bedrock.cost.compare import compare
from ec2bedrock.cost.decide import decide
from ec2bedrock.cost.profiles import DEFAULT_PROFILES

PROFILE = DEFAULT_PROFILES["qwen27b-awq-l40s"]
WINDOW_S = 8 * 22 * 3600  # the default 176-hour window, in seconds


def _with_tps(value: object):
    return replace(PROFILE, performance={"expected_aggregate_tps": value})


class TestThroughputRange:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("80-180", (80.0, 180.0)),
            (" 80 - 180 ", (80.0, 180.0)),
            ("150", (150.0, 150.0)),
            (150, (150.0, 150.0)),
            (150.5, (150.5, 150.5)),
        ],
    )
    def test_parses(self, value, expected) -> None:
        assert throughput_range(_with_tps(value)) == expected

    @pytest.mark.parametrize(
        "value",
        ["fast", "-80", "180-80", "0", "80-180-300", "nan", "inf", True, None, [80, 180]],
    )
    def test_unusable_figure_is_none(self, value) -> None:
        assert throughput_range(_with_tps(value)) is None

    def test_missing_performance_is_none(self) -> None:
        assert throughput_range(replace(PROFILE, performance=None)) is None


class TestAssess:
    def test_empty_window_is_none(self) -> None:
        assert assess(PROFILE, 1_000, 0, None) is None

    def test_exactly_at_capacity_needs_one_instance(self) -> None:
        cap = assess(PROFILE, 180 * WINDOW_S, 176, None)
        assert cap.instances == 1
        assert assess(PROFILE, 180 * WINDOW_S + 1, 176, None).instances == 2


class TestCapacityAwareCompare:
    def test_readme_example_fits_one_instance(self) -> None:
        c = compare(
            PROFILE,
            300_000_000,
            60_000_000,
            hours=8,
            days=22,
            input_usd_per_1m=0.58,
            output_usd_per_1m=3.01,
        )
        assert c.capacity.required_output_tps == pytest.approx(60_000_000 / WINDOW_S)  # ~94.7
        assert c.capacity.instances == 1
        # Issue #1's break-even utilization: EC2 must run almost flat out to beat
        # output-only pricing, about half as hard once 5:1 input is priced in.
        assert c.capacity.output_only_utilization == pytest.approx(171.742 / 180, abs=1e-3)
        assert c.capacity.io_aware_utilization == pytest.approx(87.469 / 180, abs=1e-3)
        assert c.ec2_usd == pytest.approx(343.536)
        assert c.recommendation == "mixed"  # unchanged
        assert any("above the profile's low estimate" in n for n in c.notes)

    def test_over_capacity_prices_enough_instances(self) -> None:
        c = compare(PROFILE, 0, 1_000_000_000, hours=8, days=22)
        assert c.capacity.required_output_tps == pytest.approx(1e9 / WINDOW_S)  # ~1578
        assert c.capacity.instances == 9
        assert c.ec2_usd == pytest.approx(9 * 343.536)
        assert any(n.startswith("needs 9 instances") for n in c.notes)
        # Was "ec2" ($343.54 vs $3,010). Nine instances ($3,091.82) are within 5%.
        assert c.recommendation == "mixed"

    def test_bedrock_prices_cannot_break_even(self) -> None:
        # Bedrock lists Qwen3 32B at about $0.15 in / $0.60 out per 1M tokens.
        c = compare(
            PROFILE,
            300_000_000,
            60_000_000,
            hours=8,
            days=22,
            input_usd_per_1m=0.15,
            output_usd_per_1m=0.60,
        )
        assert c.capacity.output_only_utilization == pytest.approx(861.574 / 180, abs=1e-3)
        assert c.capacity.io_aware_utilization == pytest.approx(382.922 / 180, abs=1e-3)
        assert c.recommendation == "token-provider"
        assert "break-even needs more throughput than one instance delivers" in " ".join(c.notes)

    def test_no_throughput_figure_skips_the_check(self) -> None:
        c = compare(replace(PROFILE, performance=None), 0, 1_000_000_000, hours=8, days=22)
        assert c.capacity is None
        assert c.ec2_usd == pytest.approx(343.536)
        assert c.to_dict()["capacity"] is None

    def test_unknown_ec2_cost_stays_unknown(self) -> None:
        c = compare(replace(PROFILE, hourly_usd=None), 0, 1_000_000_000, hours=8, days=22)
        assert c.capacity.instances == 9
        assert c.ec2_usd is None
        assert c.recommendation == "token-provider"

    def test_to_dict_is_strict_json(self) -> None:
        c = compare(
            PROFILE, 1_000, 1_000, hours=8, days=22, input_usd_per_1m=0.0, output_usd_per_1m=0.0
        )
        data = json.loads(json.dumps(c.to_dict(), allow_nan=False))
        assert set(data["capacity"]) == {
            "expected_output_tps",
            "required_output_tps",
            "instances",
            "break_even_utilization",
        }
        assert data["capacity"]["break_even_utilization"] == {
            "output_only": None,
            "io_aware": None,
        }


def test_decide_reason_names_the_instance_count() -> None:
    d = decide("batch", 10_000_000_000, 2_000_000_000)
    assert d.target == "ec2"
    assert d.reason == "cost-driven (batch): EC2 $6,183.65 for 18 instances vs provider $11,820.00"
