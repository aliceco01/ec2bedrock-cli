"""Markdown catalog for ``ec2bedrock-cli explain <path>``.

Each entry is verbatim markdown. Keys are command-path tuples. The empty tuple
and ``("ec2bedrock-cli",)`` both resolve to the root entry.

Keep bodies self-contained: an agent reading one entry should get enough
context without chaining reads.
"""

from __future__ import annotations

_ROOT = """\
# ec2bedrock-cli

A clonable template for AgentCulture mesh agents. It carries an agent-first CLI
(cited from the teken `python-cli` reference), a mesh identity (`culture.yaml` +
`CLAUDE.md`), the canonical guildmaster skill kit under `.claude/skills/`, and a
buildable/deployable package baseline. Clone it, rename the package, edit
`culture.yaml`, and you have a new agent.

## Verbs

- `ec2bedrock-cli whoami` — identity probe from `culture.yaml`.
- `ec2bedrock-cli learn` — structured self-teaching prompt.
- `ec2bedrock-cli explain <path>` — markdown docs for any noun/verb.
- `ec2bedrock-cli overview` — descriptive snapshot of the agent.
- `ec2bedrock-cli doctor` — check the agent-identity invariants.
- `ec2bedrock-cli cli overview` — describe the CLI surface.

## Exit-code policy

- `0` success
- `1` user-input error
- `2` environment / setup error
- `3+` reserved

## See also

- `ec2bedrock-cli explain whoami`
- `ec2bedrock-cli explain doctor`
"""

_WHOAMI = """\
# ec2bedrock-cli whoami

Reports the agent's identity from `culture.yaml`: nick (`suffix`), backend,
served model, and the package version. Read-only.

## Usage

    ec2bedrock-cli whoami
    ec2bedrock-cli whoami --json
"""

_LEARN = """\
# ec2bedrock-cli learn

Prints a structured self-teaching prompt covering purpose, command map,
exit-code policy, `--json` support, and the `explain` pointer.

## Usage

    ec2bedrock-cli learn
    ec2bedrock-cli learn --json
"""

_EXPLAIN = """\
# ec2bedrock-cli explain <path>

Prints markdown documentation for any noun/verb path. Unlike `--help` (terse,
positional), `explain` is global and addressable by path.

## Usage

    ec2bedrock-cli explain ec2bedrock-cli
    ec2bedrock-cli explain whoami
    ec2bedrock-cli explain --json <path>
"""

_OVERVIEW = """\
# ec2bedrock-cli overview

Read-only descriptive snapshot of the agent: identity (from `culture.yaml`), the
verb surface, and the sibling-pattern artifacts the template carries. Accepts an
ignored `target` so a stray path never hard-fails.

## Usage

    ec2bedrock-cli overview
    ec2bedrock-cli overview --json
"""

_DOCTOR = """\
# ec2bedrock-cli doctor

Checks the agent-identity invariants `steward doctor` verifies:
prompt-file-present and backend-consistency (`claude` → `CLAUDE.md`), plus a
skills-present check. Exits 1 when unhealthy.

## Usage

    ec2bedrock-cli doctor
    ec2bedrock-cli doctor --json
"""

_CLI = """\
# ec2bedrock-cli cli

Noun group for CLI-surface introspection. `cli overview` describes the CLI
itself (distinct from the global `overview`, which describes the agent).

## Usage

    ec2bedrock-cli cli overview
    ec2bedrock-cli cli overview --json
"""


ENTRIES: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("ec2bedrock-cli",): _ROOT,
    ("whoami",): _WHOAMI,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("overview",): _OVERVIEW,
    ("doctor",): _DOCTOR,
    ("cli",): _CLI,
    ("cli", "overview"): _CLI,
}
