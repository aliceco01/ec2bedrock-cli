# ec2bedrock-cli

Agent and CLI to manage EC2 instances running self-hosted LLM inference: warm up an instance and serve an LLM, then hibernate it on idle to power ongoing inference workloads such as ADLC. Built on ec2-cli for the underlying EC2 machine lifecycle.

## What you get

- **An agent-first CLI** cited from [teken](https://github.com/agentculture/teken)
  (`afi-cli`) — the runtime package has no third-party dependencies.
- **A mesh identity** — `culture.yaml` (`suffix` + `backend`) and the matching
  prompt file (`CLAUDE.md` for `backend: claude`).
- **The canonical guildmaster skill kit** (11 skills) under `.claude/skills/`,
  vendored cite-don't-import. See [`docs/skill-sources.md`](docs/skill-sources.md).
- **A build + deploy baseline** — pytest, lint, the agent-first rubric gate, and
  PyPI Trusted Publishing wired into GitHub Actions.

## Quickstart

```bash
uv sync
uv run pytest -n auto                 # run the test suite
uv run ec2bedrock whoami  # identity from culture.yaml (command is `ec2bedrock`; dist is `ec2bedrock-cli`)
uv run ec2bedrock learn   # self-teaching prompt (add --json)
uv run teken cli doctor . --strict    # the agent-first rubric gate CI runs
```

## Milestone 1 — cost estimator (offline)

All commands below are offline / dry-run (no AWS calls). `compare` and `decide`
encode the recommendation in the exit code: `ec2` = **0**, `token-provider` =
**20**, `mixed` = **21**. Note that **0 doubles as "recommend EC2" and generic
success** — a router that needs an unambiguous verdict should parse `--json`
(the `recommendation`/`decision` field) rather than rely on exit code 0 alone;
the non-zero codes (20/21) are unambiguous, and `1`/`2` remain user/environment
errors.

```bash
ec2bedrock profile list
ec2bedrock profile show qwen27b-awq-l40s
ec2bedrock estimate --profile qwen27b-awq-l40s --hours 8 --days 22
ec2bedrock compare --profile qwen27b-awq-l40s --input-tokens 300000000 --output-tokens 60000000 --provider-input-price 0.58 --provider-output-price 3.01
ec2bedrock decide --workload meeting-mode --input-tokens 528000000 --output-tokens 88000000 --json
ec2bedrock decide --workload sensitive --input-tokens 528000000 --output-tokens 88000000 --json
```

Token counts are totals for the whole window (`--hours` x `--days`, default
8 x 22 = 176 hours), not per hour. Issue #1's example of 3M input and 0.5M
output tokens an hour is `--input-tokens 528000000 --output-tokens 88000000`;
passed as-is, the per-hour numbers flip the verdict to `token-provider`.
`decide --workload` accepts `batch`, `ci`, `meeting-mode`, `interactive`,
`off-hours`, `sporadic` and `sensitive`; `sensitive` (or `--sensitive`) always
routes to EC2.

`compare` and `decide` also check the output tokens against the profile's
`performance.expected_aggregate_tps`. When the workload needs more than one
instance, the EC2 cost covers all of them, and `capacity.break_even_utilization`
in the JSON shows how busy each instance must be for EC2 to cost the same as the
provider (above 1.0, EC2 can't win on cost at those prices).

## CLI

| Verb | What it does |
|------|--------------|
| `whoami` | Report this agent's nick, version, backend, and model from `culture.yaml`. |
| `learn` | Print a structured self-teaching prompt. |
| `explain <path>` | Markdown docs for any noun/verb path. |
| `overview` | Read-only descriptive snapshot of the agent. |
| `doctor` | Check the agent-identity invariants (prompt-file-present, backend-consistency). |
| `cli overview` | Describe the CLI surface itself. |

Every command supports `--json`. Results go to stdout, errors/diagnostics to
stderr (never mixed). Exit codes: `0` success, `1` user error, `2` environment
error, `3+` reserved.

## Make it your own

1. Rename the package `ec2bedrock/` and the `ec2bedrock-cli`
   CLI/dist name throughout `pyproject.toml`, the package, `tests/`,
   `sonar-project.properties`, and this `README.md`. The name is hard-coded in
   ~100 places, so list every occurrence first — see the `git grep` discovery
   command in [`CLAUDE.md`](CLAUDE.md), the authoritative rename procedure.
2. Edit `culture.yaml` with your `suffix` and `backend`.
3. Rewrite `CLAUDE.md` for your agent and run `/init`.
4. Re-vendor only the skills you need from guildmaster (see
   [`docs/skill-sources.md`](docs/skill-sources.md)).

See [`CLAUDE.md`](CLAUDE.md) for the full conventions (version-bump-every-PR,
the `cicd` PR lane, deploy setup).

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
