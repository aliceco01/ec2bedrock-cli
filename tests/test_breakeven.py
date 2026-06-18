"""Tests for ec2bedrock.cost.breakeven — break-even math."""

from __future__ import annotations

import pytest

from ec2bedrock.cost.breakeven import (
    break_even,
    io_aware_breakeven_tps,
    output_only_breakeven_tps,
)


class TestOutputOnlyBreakevenTps:
    def test_issue_1_reference(self) -> None:
        assert output_only_breakeven_tps(1.861, 3.0) == pytest.approx(172.3, abs=1.0)

    def test_slightly_higher_output_price(self) -> None:
        assert output_only_breakeven_tps(1.861, 3.01) == pytest.approx(171.7, abs=1.0)


class TestIoAwareBreakevenTps:
    def test_io_aware_reference(self) -> None:
        assert io_aware_breakeven_tps(1.861, 0.58, 3.01, 6.0) == pytest.approx(79.6, abs=1.0)

    def test_io_aware_lower_than_output_only(self) -> None:
        io = io_aware_breakeven_tps(1.861, 0.58, 3.01, 6.0)
        oo = output_only_breakeven_tps(1.861, 3.01)
        assert io < oo


class TestBreakEven:
    def test_to_dict_keys(self) -> None:
        result = break_even(1.861, 0.58, 3.01, 6.0)
        d = result.to_dict()
        assert "output_only_tps" in d
        assert "io_aware_tps" in d
        assert "input_output_ratio" in d
