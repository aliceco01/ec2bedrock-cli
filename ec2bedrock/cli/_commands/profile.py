"""``ec2bedrock profile`` — inspect inference profiles (list/show).

List available profile names or show the fields of a single profile.
"""

from __future__ import annotations

import argparse

from ec2bedrock.cli._errors import EXIT_USER_ERROR, CliError
from ec2bedrock.cli._output import emit_result
from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.profiles import ProfileError


def cmd_profile_list(args: argparse.Namespace) -> int:
    cfg = load_config()
    names = sorted(cfg.profiles)
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result({"profiles": names}, json_mode=True)
    else:
        emit_result("\n".join(names), json_mode=False)
    return 0


def cmd_profile_show(args: argparse.Namespace) -> int:
    cfg = load_config()
    try:
        prof = get_profile(cfg, args.name)
    except ProfileError as e:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=str(e),
            remediation="run 'ec2bedrock profile list' to see available profiles",
        ) from e

    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(prof.to_dict(), json_mode=True)
    else:
        emit_result(
            "\n".join(f"{k}: {v}" for k, v in prof.to_dict().items()),
            json_mode=False,
        )
    return 0


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_profile_list(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("profile", help="Inspect inference profiles (list/show).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="profile_command", parser_class=type(p))
    lp = noun_sub.add_parser("list", help="List available profile names.")
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_profile_list)
    sp = noun_sub.add_parser("show", help="Show one profile's fields.")
    sp.add_argument("name", help="Profile name, e.g. qwen27b-awq-l40s")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_profile_show)
