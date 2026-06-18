"""Hardening driven by the colleague review of the milestone-1 diff.

Three correctness/robustness fixes a diverse second pass surfaced:
  1. a legitimate 0.0 hourly rate is a *known* rate, not "missing";
  2. break-even must not divide by a zero provider price;
  3. the `decide` CLI must honour --provider-*-price like `compare` does.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace

from ec2bedrock.cli._commands import decide as dec_cmd
from ec2bedrock.cost.breakeven import io_aware_breakeven_tps, output_only_breakeven_tps
from ec2bedrock.cost.compare import compare
from ec2bedrock.cost.profiles import DEFAULT_PROFILES


def test_zero_provider_price_yields_none_not_infinity():
    # A free/zero output price means "no finite break-even". Represent it as None
    # (JSON null), never float('inf') which would serialise to invalid JSON.
    assert output_only_breakeven_tps(1.861, 0.0) is None
    assert io_aware_breakeven_tps(1.861, 0.0, 0.0, 6.0) is None


def test_zero_provider_price_compare_emits_strict_valid_json():
    # Live testing caught Infinity leaking into --json output. Guard it: the
    # comparison dict must be serialisable with allow_nan=False (strict JSON).
    c = compare(
        DEFAULT_PROFILES["qwen27b-awq-l40s"],
        input_tokens=1000,
        output_tokens=1000,
        hours=8,
        days=22,
        output_usd_per_1m=0.0,
    )
    encoded = json.dumps(c.to_dict(), allow_nan=False)  # raises if any inf/nan
    assert json.loads(encoded)["break_even"]["output_only_tps"] is None


def test_zero_hourly_rate_is_a_known_rate_not_missing():
    # hourly_usd == 0.0 is a *known* (free) rate: break-even is still computed
    # (the bug forced it to None), and the EC2 cost is known (0 compute + the
    # fixed EBS floor), not UNKNOWN.
    free = replace(DEFAULT_PROFILES["qwen27b-awq-l40s"], hourly_usd=0.0)
    c = compare(free, input_tokens=1_000_000, output_tokens=1_000_000, hours=8, days=22)
    assert c.break_even is not None  # the falsy-check bug forced this to None
    assert c.ec2_usd is not None  # 0 compute + $16 EBS floor, still known

    # At high volume, free compute + a cheap EBS floor crushes the provider.
    big = compare(free, input_tokens=1_000_000_000, output_tokens=1_000_000_000, hours=8, days=22)
    assert big.recommendation == "ec2"


def test_decide_cli_honours_provider_prices(capsys):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    dec_cmd.register(sub)
    # Near-free provider prices must flow through and flip a sustained batch
    # workload toward the provider (exit 20). With the defaults it would be ec2.
    args = parser.parse_args(
        [
            "decide",
            "--workload",
            "batch",
            "--input-tokens",
            "100000000",
            "--output-tokens",
            "100000000",
            "--provider-input-price",
            "0.001",
            "--provider-output-price",
            "0.001",
            "--json",
        ]
    )
    assert hasattr(args, "provider_input_price")
    rc = args.func(args)
    capsys.readouterr()
    assert rc == 20  # token-provider — proves the prices were honoured
