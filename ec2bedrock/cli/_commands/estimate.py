"""``ec2bedrock estimate`` — estimate scheduled EC2 cost for a profile."""

from __future__ import annotations

import argparse

from ec2bedrock.cli._errors import EXIT_USER_ERROR, CliError
from ec2bedrock.cli._output import emit_result
from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.estimate import estimate
from ec2bedrock.cost.profiles import ProfileError


def _resolve(name: str):
    try:
        return get_profile(load_config(), name)
    except ProfileError as e:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=str(e),
            remediation="run 'ec2bedrock profile list' to see available profiles",
        ) from e


def cmd_estimate(args: argparse.Namespace) -> int:
    est = estimate(_resolve(args.profile), args.hours, args.days)
    if bool(getattr(args, "json", False)):
        emit_result(est.to_dict(), json_mode=True)
    else:
        emit_result(
            "\n".join(f"{k}: {v}" for k, v in est.to_dict().items()),
            json_mode=False,
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("estimate", help="Estimate scheduled EC2 cost for a profile.")
    p.add_argument("--profile", required=True)
    p.add_argument("--hours", type=float, default=8.0)
    p.add_argument("--days", type=float, default=22.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_estimate)
