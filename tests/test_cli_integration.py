"""t11 — end-to-end CLI integration for the milestone-1 cost verbs.

Drives the real :func:`ec2bedrock.cli.main` (the wired parser) offline and
asserts routing, JSON output, and the decision-encoding exit codes. Also guards
that wiring the cost verbs left the existing introspection scaffold unchanged.
"""

from __future__ import annotations

import json

from ec2bedrock.cli import main


def test_profile_show_routes_and_succeeds(capsys):
    rc = main(["profile", "show", "qwen27b-awq-l40s"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "g6e.xlarge" in out


def test_estimate_json_end_to_end(capsys):
    rc = main(
        ["estimate", "--profile", "qwen27b-awq-l40s", "--hours", "8", "--days", "22", "--json"]
    )
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["total_usd"] == 343.536


def test_compare_exit_code_encodes_recommendation(capsys):
    rc = main(
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
    data = json.loads(capsys.readouterr().out)
    assert data["recommendation"] == "mixed"
    assert rc == 21  # the router-facing exit code for "mixed"


def test_decide_sensitive_routes_to_ec2(capsys):
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
    assert data["decision"] == "ec2"
    assert rc == 0


def test_unknown_profile_is_user_error(capsys):
    # A bad profile maps ProfileError -> CliError(EXIT_USER_ERROR=1), no traceback.
    rc = main(["estimate", "--profile", "does-not-exist"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "hint:" in err


def test_existing_scaffold_verbs_unchanged(capsys):
    rc = main(["whoami", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["nick"]
