"""Tests for the ``ec2bedrock profile`` CLI command (list/show)."""

from __future__ import annotations

import argparse
import json

import pytest

from ec2bedrock.cli._commands import profile as profile_cmd
from ec2bedrock.cli._errors import CliError


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    profile_cmd.register(sub)
    return parser.parse_args(argv)


# --- profile list ----------------------------------------------------------


def test_profile_list_text(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(["profile", "list"])
    rc = args.func(args)
    captured = capsys.readouterr()
    assert "qwen27b-awq-l40s" in captured.out
    assert rc == 0


def test_profile_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(["profile", "list", "--json"])
    rc = args.func(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "qwen27b-awq-l40s" in data["profiles"]
    assert rc == 0


# --- profile show ----------------------------------------------------------


def test_profile_show_json(capsys: pytest.CaptureFixture[str]) -> None:
    args = _parse(["profile", "show", "qwen27b-awq-l40s", "--json"])
    rc = args.func(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["instance_type"] == "g6e.xlarge"
    assert data["hourly_usd"] == 1.861
    assert rc == 0


def test_profile_show_bogus() -> None:
    args = _parse(["profile", "show", "bogus"])
    with pytest.raises(CliError):
        args.func(args)
