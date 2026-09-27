"""``ec2bedrock decide`` — router verdict: EC2 vs token-provider for a workload."""

from __future__ import annotations

import argparse

from ec2bedrock.cli._args import day_count, hours_per_day, token_count, usd_price
from ec2bedrock.cli._errors import EXIT_USER_ERROR, CliError
from ec2bedrock.cli._output import emit_result
from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.decide import WORKLOAD_CLASSES, decide
from ec2bedrock.cost.profiles import ProfileError
from ec2bedrock.cost.rates import (
    DEFAULT_PROVIDER_INPUT_USD_PER_1M,
    DEFAULT_PROVIDER_OUTPUT_USD_PER_1M,
)


def cmd_decide(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.profile:
        try:
            prof = get_profile(cfg, args.profile)
        except ProfileError as e:
            raise CliError(
                code=EXIT_USER_ERROR,
                message=str(e),
                remediation="run 'ec2bedrock profile list' to see available profiles",
            ) from e
    else:
        prof = None
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
    dec = decide(
        args.workload,
        args.input_tokens,
        args.output_tokens,
        sensitive=args.sensitive,
        profile=prof,
        hours=args.hours,
        days=args.days,
        input_usd_per_1m=in_price,
        output_usd_per_1m=out_price,
    )
    if bool(getattr(args, "json", False)):
        emit_result(dec.to_dict(), json_mode=True)
    else:
        emit_result(
            "\n".join(f"{k}: {v}" for k, v in dec.to_dict().items()),
            json_mode=False,
        )
    return dec.exit


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("decide", help="Router verdict: EC2 vs token-provider for a workload.")
    p.add_argument(
        "--workload",
        required=True,
        choices=sorted(WORKLOAD_CLASSES),
        help=(
            "Workload class. sensitive always routes to EC2; sporadic, interactive and "
            "off-hours route to a token provider; batch, ci and meeting-mode are decided "
            "on cost."
        ),
    )
    p.add_argument(
        "--input-tokens",
        type=token_count,
        required=True,
        help="Total input tokens over the whole window (--hours x --days), not per hour.",
    )
    p.add_argument(
        "--output-tokens",
        type=token_count,
        required=True,
        help="Total output tokens over the whole window (--hours x --days), not per hour.",
    )
    p.add_argument(
        "--sensitive",
        action="store_true",
        help="Keep the workload on self-managed EC2 regardless of cost.",
    )
    p.add_argument(
        "--profile",
        default=None,
        help="Profile name; see 'ec2bedrock profile list' (default: qwen27b-awq-l40s).",
    )
    p.add_argument(
        "--hours",
        type=hours_per_day,
        default=8.0,
        help="Instance hours per day, more than 0 and at most 24 (default: %(default)s).",
    )
    p.add_argument(
        "--days",
        type=day_count,
        default=22.0,
        help=(
            "Days the instance runs in the window "
            "(default: %(default)s, about a month of workdays)."
        ),
    )
    p.add_argument(
        "--provider-input-price",
        type=usd_price,
        default=None,
        help=(
            "Token-provider USD per 1M input tokens "
            f"(default: config.toml, else {DEFAULT_PROVIDER_INPUT_USD_PER_1M})."
        ),
    )
    p.add_argument(
        "--provider-output-price",
        type=usd_price,
        default=None,
        help=(
            "Token-provider USD per 1M output tokens "
            f"(default: config.toml, else {DEFAULT_PROVIDER_OUTPUT_USD_PER_1M})."
        ),
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_decide)
