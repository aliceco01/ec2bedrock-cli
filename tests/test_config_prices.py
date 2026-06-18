"""Tests that config provider prices are honoured and CLI flags override them."""

from __future__ import annotations

import argparse
import json

from ec2bedrock.cli._commands import compare as cmp_cmd
from ec2bedrock.cost.config import Config
from ec2bedrock.cost.profiles import DEFAULT_PROFILES


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    cmp_cmd.register(sub)
    return parser.parse_args(argv)


def test_compare_uses_config_provider_prices(monkeypatch, capsys) -> None:
    cheap = Config(
        profiles=dict(DEFAULT_PROFILES),
        provider_input_usd_per_1m=0.001,
        provider_output_usd_per_1m=0.001,
    )
    monkeypatch.setattr(cmp_cmd, "load_config", lambda *a, **k: cheap)
    args = _parse(
        [
            "compare",
            "--profile",
            "qwen27b-awq-l40s",
            "--input-tokens",
            "100000000",
            "--output-tokens",
            "100000000",
            "--json",
        ]
    )
    rc = args.func(args)
    data = json.loads(capsys.readouterr().out)
    # near-free config prices -> provider ~ $0.2 << EC2 $343 -> token-provider, exit 20
    assert data["recommendation"] == "token-provider"
    assert rc == 20


def test_cli_flag_overrides_config_price(monkeypatch, capsys) -> None:
    cheap = Config(
        profiles=dict(DEFAULT_PROFILES),
        provider_input_usd_per_1m=0.001,
        provider_output_usd_per_1m=0.001,
    )
    monkeypatch.setattr(cmp_cmd, "load_config", lambda *a, **k: cheap)
    args = _parse(
        [
            "compare",
            "--profile",
            "qwen27b-awq-l40s",
            "--input-tokens",
            "100000000",
            "--output-tokens",
            "100000000",
            "--provider-output-price",
            "100",
            "--json",
        ]
    )
    rc = args.func(args)
    data = json.loads(capsys.readouterr().out)
    # explicit expensive output price overrides cheap config -> EC2 wins, exit 0
    assert data["recommendation"] == "ec2"
    assert rc == 0
