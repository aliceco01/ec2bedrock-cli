"""``ec2bedrock compare`` — compare EC2 vs token-provider cost for a workload."""

from __future__ import annotations

import argparse

from ec2bedrock.cli._errors import EXIT_USER_ERROR, CliError
from ec2bedrock.cli._output import emit_result
from ec2bedrock.cost.compare import compare
from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.profiles import ProfileError


def cmd_compare(args: argparse.Namespace) -> int:
    cfg = load_config()
    try:
        prof = get_profile(cfg, args.profile)
    except ProfileError as e:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=str(e),
            remediation="run 'ec2bedrock profile list' to see available profiles",
        ) from e
    in_price = (
        args.provider_input_price
        if args.provider_input_price is not None
        else cfg.provider_input_usd_per_1m
    )
    out_price = (
        args.provider_output_price
        if args.provider_output_price is not None
        else cfg.provider_output_usd_per_1m
    )
    cmp = compare(
        prof,
        args.input_tokens,
        args.output_tokens,
        hours=args.hours,
        days=args.days,
        input_usd_per_1m=in_price,
        output_usd_per_1m=out_price,
    )
    if bool(getattr(args, "json", False)):
        emit_result(cmp.to_dict(), json_mode=True)
    else:
        emit_result(
            "\n".join(f"{k}: {v}" for k, v in cmp.to_dict().items()),
            json_mode=False,
        )
    return cmp.exit_code


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("compare", help="Compare EC2 vs token-provider cost for a workload.")
    p.add_argument("--profile", required=True)
    p.add_argument("--input-tokens", type=int, required=True)
    p.add_argument("--output-tokens", type=int, required=True)
    p.add_argument("--hours", type=float, default=8.0)
    p.add_argument("--days", type=float, default=22.0)
    p.add_argument("--provider-input-price", type=float, default=None)
    p.add_argument("--provider-output-price", type=float, default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_compare)
