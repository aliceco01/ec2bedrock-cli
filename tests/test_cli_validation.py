"""Input validation and help text for the estimate / compare / decide verbs.

Bad numbers must be a user error (exit 1, ``error:`` + ``hint:``) before any
cost arithmetic runs; before this, ``--hours -8`` printed a negative total with
exit 0. Token flags must say they are totals for the whole window, because
issue #1's per-hour example gives the opposite verdict when passed as-is.
"""

from __future__ import annotations

import json

import pytest

from ec2bedrock.cli import main

_PROFILE = "qwen27b-awq-l40s"
_COMPARE = ["compare", "--profile", _PROFILE]
_DECIDE = ["decide", "--workload", "batch"]


@pytest.mark.parametrize(
    "argv",
    [
        ["estimate", "--profile", _PROFILE, "--hours", "-8"],
        ["estimate", "--profile", _PROFILE, "--hours", "0"],
        ["estimate", "--profile", _PROFILE, "--hours", "30"],
        ["estimate", "--profile", _PROFILE, "--hours", "nan"],
        ["estimate", "--profile", _PROFILE, "--days", "0"],
        ["estimate", "--profile", _PROFILE, "--days", "inf"],
        [*_COMPARE, "--input-tokens", "-5", "--output-tokens", "100"],
        [*_COMPARE, "--input-tokens", "5", "--output-tokens", "1.5"],
        [*_COMPARE, "--input-tokens", "5", "--output-tokens", "5", "--provider-input-price", "-1"],
        [*_DECIDE, "--input-tokens", "5", "--output-tokens", "5", "--days", "-22"],
        [*_DECIDE, "--input-tokens", "5", "--output-tokens", "-5"],
        ["decide", "--workload", "banana", "--input-tokens", "5", "--output-tokens", "5"],
    ],
)
def test_bad_input_is_a_user_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("error: argument --")
    assert "hint:" in err
    assert "Traceback" not in err


def test_bad_input_error_is_json_in_json_mode(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["estimate", "--profile", _PROFILE, "--hours", "-8", "--json"])
    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == 1
    assert "--hours" in payload["message"]


def test_boundary_values_are_accepted(capsys):
    assert main(["estimate", "--profile", _PROFILE, "--hours", "24", "--days", "30"]) == 0
    rc = main(
        [
            *_COMPARE,
            "--input-tokens",
            "0",
            "--output-tokens",
            "0",
            "--provider-input-price",
            "0",
            "--provider-output-price",
            "0",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert data["provider_usd"] == 0
    assert rc == data["exit_code"] == 20


@pytest.mark.parametrize("verb", ["compare", "decide"])
def test_token_flags_say_they_are_window_totals(verb, capsys):
    with pytest.raises(SystemExit) as exc:
        main([verb, "--help"])
    assert exc.value.code == 0
    text = " ".join(capsys.readouterr().out.split())  # undo argparse line wrapping
    assert "Total input tokens over the whole window (--hours x --days), not per hour." in text
    assert "Total output tokens over the whole window (--hours x --days), not per hour." in text


def test_issue_1_per_hour_example_needs_window_totals(capsys):
    # Issue #1: 3M input + 0.5M output tokens PER HOUR -> EC2 wins ($1.86 vs $3.25
    # an hour). Over the default 8 x 22 = 176 h window that is 528M + 88M.
    rc = main(
        [
            "decide",
            "--workload",
            "meeting-mode",
            "--input-tokens",
            str(3_000_000 * 176),
            "--output-tokens",
            str(500_000 * 176),
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert data["decision"] == "ec2"
    assert rc == data["exit"] == 0


def test_sensitive_workload_class_routes_to_ec2(capsys):
    # Before: `--workload sensitive` fell through to the cost comparison and,
    # at this volume, routed sensitive traffic to the token provider (exit 20).
    rc = main(
        [
            "decide",
            "--workload",
            "sensitive",
            "--input-tokens",
            "3000000",
            "--output-tokens",
            "500000",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert data["decision"] == "ec2"
    assert rc == data["exit"] == 0
