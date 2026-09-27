"""Markdown catalog for ``ec2bedrock explain <path>``.

Each entry is verbatim markdown. Keys are command-path tuples. The empty tuple
and ``("ec2bedrock",)`` both resolve to the root entry.

Keep bodies self-contained: an agent reading one entry should get enough
context without chaining reads.
"""

from __future__ import annotations

_ROOT = """\
# ec2bedrock

A clonable template for AgentCulture mesh agents. It carries an agent-first CLI
(cited from the teken `python-cli` reference), a mesh identity (`culture.yaml` +
`CLAUDE.md`), the canonical guildmaster skill kit under `.claude/skills/`, and a
buildable/deployable package baseline. Clone it, rename the package, edit
`culture.yaml`, and you have a new agent.

## Verbs

- `ec2bedrock whoami` — identity probe from `culture.yaml`.
- `ec2bedrock learn` — structured self-teaching prompt.
- `ec2bedrock explain <path>` — markdown docs for any noun/verb.
- `ec2bedrock overview` — descriptive snapshot of the agent.
- `ec2bedrock doctor` — check the agent-identity invariants.
- `ec2bedrock cli overview` — describe the CLI surface.
- `ec2bedrock profile list` — list bundled + config.toml profiles.
- `ec2bedrock profile show <name>` — show a single profile.
- `ec2bedrock estimate` — offline scheduled EC2 cost estimate.
- `ec2bedrock compare` — EC2 vs token-provider cost comparison.
- `ec2bedrock decide` — workload router verdict.

## Exit-code policy

- `0` success
- `1` user-input error
- `2` environment / setup error
- `3+` reserved

## See also

- `ec2bedrock explain whoami`
- `ec2bedrock explain doctor`
"""

_WHOAMI = """\
# ec2bedrock whoami

Reports the agent's identity from `culture.yaml`: nick (`suffix`), backend,
served model, and the package version. Read-only.

## Usage

    ec2bedrock whoami
    ec2bedrock whoami --json
"""

_LEARN = """\
# ec2bedrock learn

Prints a structured self-teaching prompt covering purpose, command map,
exit-code policy, `--json` support, and the `explain` pointer.

## Usage

    ec2bedrock learn
    ec2bedrock learn --json
"""

_EXPLAIN = """\
# ec2bedrock explain <path>

Prints markdown documentation for any noun/verb path. Unlike `--help` (terse,
positional), `explain` is global and addressable by path.

## Usage

    ec2bedrock explain ec2bedrock
    ec2bedrock explain whoami
    ec2bedrock explain --json <path>
"""

_OVERVIEW = """\
# ec2bedrock overview

Read-only descriptive snapshot of the agent: identity (from `culture.yaml`), the
verb surface, and the sibling-pattern artifacts the template carries. Accepts an
ignored `target` so a stray path never hard-fails.

## Usage

    ec2bedrock overview
    ec2bedrock overview --json
"""

_DOCTOR = """\
# ec2bedrock doctor

Checks the agent-identity invariants `steward doctor` verifies:
prompt-file-present and backend-consistency (`claude` → `CLAUDE.md`), plus a
skills-present check. Exits 1 when unhealthy.

## Usage

    ec2bedrock doctor
    ec2bedrock doctor --json
"""

_CLI = """\
# ec2bedrock cli

Noun group for CLI-surface introspection. `cli overview` describes the CLI
itself (distinct from the global `overview`, which describes the agent).

## Usage

    ec2bedrock cli overview
    ec2bedrock cli overview --json
"""

_PROFILE = """\
# ec2bedrock profile list / show

List or display bundled and `config.toml` profiles. `profile list` enumerates
all available profiles; `profile show <name>` prints the details for one
profile. Both support `--json`.

## Usage

    ec2bedrock profile list
    ec2bedrock profile list --json
    ec2bedrock profile show <name>
    ec2bedrock profile show <name> --json
"""

_ESTIMATE = """\
# ec2bedrock estimate

Offline scheduled EC2 cost estimate. Computes `compute = hourly_usd * hours *
days` plus EBS costs. EBS bills per month, so the monthly storage charge is
spread over 22 working days: `--days 22` carries one month, `--days 1` carries
1/22 of it. No AWS calls are made. `--hours` is instance hours per day
(more than 0, at most 24); `--days` is the days it runs in the window (default
22, about a month of workdays). Out-of-range values are a user error (exit 1).

## Usage

    ec2bedrock estimate --profile <name> --hours H --days D
    ec2bedrock estimate --profile <name> --hours H --days D --json
"""

_COMPARE = """\
# ec2bedrock compare

Compare EC2 cost against a token-based provider. Prints a recommendation
(`ec2`, `token-provider`, or `mixed`) and the break-even point. The exit code
encodes the recommendation: `0` for `ec2`, `20` for `token-provider`, `21` for
`mixed`.

Token counts are totals for the whole window (`--hours` x `--days`, default
8 x 22 = 176 hours), not per hour. A per-hour figure must be multiplied by the
window's hours first, or the verdict can flip.

## Usage

    ec2bedrock compare --profile <name> --input-tokens N --output-tokens N \\
        --provider-input-price P --provider-output-price P
    ec2bedrock compare --profile <name> --input-tokens N --output-tokens N \\
        --provider-input-price P --provider-output-price P --json
"""

_DECIDE = """\
# ec2bedrock decide

Workload router verdict. Given a workload class and token counts, returns a
recommendation: sensitive workloads (`--workload sensitive` or `--sensitive`)
route to EC2, sporadic/interactive/off-hours workloads route to token-provider,
batch/ci/meeting-mode workloads are cost-driven. Any other class is a user
error (exit 1). The exit code encodes the decision.

Token counts are totals for the whole window (`--hours` x `--days`, default
8 x 22 = 176 hours), not per hour.

## Usage

    ec2bedrock decide --workload W --input-tokens N --output-tokens N
    ec2bedrock decide --workload sensitive --input-tokens N --output-tokens N
    ec2bedrock decide --workload W --input-tokens N --output-tokens N --json
"""


ENTRIES: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("ec2bedrock",): _ROOT,
    # Back-compat alias: the command is `ec2bedrock`, but the PyPI dist and mesh
    # nick are `ec2bedrock-cli`, so a reader may address the root by either name.
    ("ec2bedrock-cli",): _ROOT,
    ("whoami",): _WHOAMI,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("overview",): _OVERVIEW,
    ("doctor",): _DOCTOR,
    ("cli",): _CLI,
    ("cli", "overview"): _CLI,
    ("profile",): _PROFILE,
    ("profile", "list"): _PROFILE,
    ("profile", "show"): _PROFILE,
    ("estimate",): _ESTIMATE,
    ("compare",): _COMPARE,
    ("decide",): _DECIDE,
}
