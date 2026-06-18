"""Tests for the estimate / compare / decide CLI commands."""

from __future__ import annotations

import argparse
import json

import pytest

from ec2bedrock.cli._commands import compare as cmp_cmd
from ec2bedrock.cli._commands import decide as dec_cmd
from ec2bedrock.cli._commands import estimate as est_cmd
from ec2bedrock.cli._errors import CliError


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    est_cmd.register(sub)
    cmp_cmd.register(sub)
    dec_cmd.register(sub)
    return parser.parse_args(argv)


# --- estimate ----------------------------------------------------------------


def test_estimate_json(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(
        [
            "estimate",
            "--profile",
            "qwen27b-awq-l40s",
            "--hours",
            "8",
            "--days",
            "22",
            "--json",
        ]
    )
    rc = args.func(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_usd"] == pytest.approx(343.536)
    assert rc == 0


# --- compare -----------------------------------------------------------------


def test_compare_mixed_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(
        [
            "compare",
            "--profile",
            "qwen27b-awq-l40s",
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
    rc = args.func(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["recommendation"] == "mixed"
    assert rc == 21


# --- decide ------------------------------------------------------------------


def test_decide_sensitive_ec2(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(
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
    rc = args.func(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["decision"] == "ec2"
    assert rc == 0


# --- error handling -----------------------------------------------------------


def test_unknown_profile_raises_cli_error() -> None:
    args = _parse(["estimate", "--profile", "bogus"])
    with pytest.raises(CliError):
        args.func(args)
