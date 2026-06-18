"""t13 — milestone-1 acceptance matrix (issue #1).

Each of issue #1's six first-milestone acceptance criteria maps to at least one
assertion here, driven through the real surface and proven to run offline (no
network, no boto3). This is the milestone gate: if these pass with zero AWS, the
*prove-the-economics* milestone is met.

Issue #1 acceptance criteria:
  1. Can define a profile
  2. Can estimate scheduled EC2 cost
  3. Can compare against token-provider cost
  4. Can explain break-even utilization
  5. Can output JSON for future ADLC router integration
  6. Can run in dry-run mode without AWS mutation
"""

from __future__ import annotations

import json
import socket
import sys

import pytest

from ec2bedrock.cli import main
from ec2bedrock.cost.breakeven import break_even
from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.estimate import estimate

_PROFILE = "qwen27b-awq-l40s"


def test_criterion_1_can_define_a_profile(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        "\n".join(
            [
                "[profiles.custom-l40s]",
                'instance_type = "g6e.xlarge"',
                'gpu = "l40s-48gb"',
                'runtime = "vllm"',
                'quantization = "awq"',
                "hourly_usd = 1.5",
                "storage_gb = 100",
            ]
        )
    )
    cfg = load_config(cfg_file)
    assert "custom-l40s" in cfg.profiles
    # a defined profile is immediately usable for an estimate
    est = estimate(get_profile(cfg, "custom-l40s"), 8, 22)
    assert est.total_usd is not None


def test_criterion_2_can_estimate_scheduled_ec2_cost(capsys):
    rc = main(["estimate", "--profile", _PROFILE, "--hours", "8", "--days", "22", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["total_usd"] == 343.536  # issue #1's $343.54/month


def test_criterion_3_can_compare_against_token_provider(capsys):
    rc = main(
        [
            "compare",
            "--profile",
            _PROFILE,
            "--input-tokens",
            "300000000",
            "--output-tokens",
            "60000000",
            "--provider-input-price",
            "0.58",
            "--provider-output-price",
            "3.01",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert data["recommendation"] in {"ec2", "token-provider", "mixed"}
    assert data["provider_usd"] == pytest.approx(354.6)
    assert rc == data["exit_code"]  # process exit encodes the recommendation


def test_criterion_4_can_explain_break_even_utilization():
    be = break_even(1.861, 0.58, 3.01, 6.0)
    # output-only ~172 tok/s; including input, EC2 wins earlier (lower threshold)
    assert be.output_only_tps == pytest.approx(172, abs=2)
    assert be.io_aware_tps < be.output_only_tps


def test_criterion_5_json_for_router_integration(capsys):
    rc = main(
        [
            "decide",
            "--workload",
            "meeting-mode",
            "--input-tokens",
            "3000000",
            "--output-tokens",
            "500000",
            "--sensitive",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    # router-consumable: stable keys + explicit decision + exit code
    assert set(data) >= {"decision", "reason", "exit"}
    assert data["decision"] == "ec2"
    assert rc == data["exit"] == 0


def test_criterion_6_dry_run_no_aws_mutation(monkeypatch, capsys):
    # No boto3 anywhere in the milestone-1 paths...
    assert "boto3" not in sys.modules
    # ...and a banned socket proves the commands never reach AWS.
    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("network attempted")),
    )
    rc = main(["estimate", "--profile", _PROFILE, "--hours", "8", "--days", "22"])
    assert rc == 0
    assert "boto3" not in sys.modules
