# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-09-27

### Added

- `compare` (and so `decide`) checks throughput against the profile's `performance.expected_aggregate_tps`. A new `capacity` block in the output shows the output tokens/sec the workload needs over the window, how many instances that takes, and the break-even utilization issue #1 asks for: how busy each instance must be for EC2 to cost the same as the provider. The default profile must run at 95% of its 180 tok/s to beat output-only pricing, 49% with 5:1 input.

### Changed

- When the workload needs more than one instance, `ec2_usd` is the cost of all of them, and `decide` names the instance count in its reason. Before, `compare` priced one instance for any volume, so 1B output tokens in the default window came out as a $343.54 EC2 win, although one instance serves about 114M at most. It now takes 9 instances ($3,091.82), which is `mixed` against $3,010 of provider tokens.

## [0.6.2] - 2026-09-27

### Fixed

- `estimate` (and the EC2 side of `compare` and `decide`) spreads the monthly EBS charge over the window at 22 working days a month. Before, every estimate carried exactly one month of storage, so `--days 1` showed $16 of storage on $14.89 of compute and `--days 60` still showed $16. The default 8 x 22 result is unchanged ($343.54).

## [0.6.1] - 2026-09-27

### Fixed

- `compare` and `decide` token flags now say they are totals for the whole `--hours` x `--days` window, not per hour. Issue #1's per-hour example (3M input + 0.5M output tokens an hour, where EC2 wins) returned `token-provider` when passed as-is. Every `estimate`, `compare` and `decide` flag now has help text, and the README `decide` example uses window totals.
- `estimate`, `compare` and `decide` reject negative or non-finite numbers and `--hours` above 24 as a user error (exit 1 with a hint). Before, `--hours -8` printed a total of -$311.54 with exit 0.
- `decide --workload sensitive` routes to EC2, like `--sensitive`. Before, it fell through to the cost comparison and could send sensitive traffic to the token provider. Unknown workload classes are now a user error instead of silently being decided on cost.
- `decide` reasons print money as dollars and cents (`$3.24`, not `$3.2449999999999997`) and say `unknown` when the EC2 cost can't be computed (was `$None`).

## [0.6.0] - 2026-06-24

### Added

- **Memory-discipline "Conventions and workflow" section in `CLAUDE.md`** — a
  per-task *recall-before / remember-after* convention (scope localized to this
  repo's nick) so the vendored `remember` / `recall` skills are actually used,
  not just present: `/recall` before non-trivial work to build on prior
  decisions instead of re-deriving them, and `/remember` when a non-obvious
  decision, constraint, fix-and-why, or hard-won gotcha surfaces. The section
  documents this repo's memory as **in-repo and public** — records resolve to
  `<repo-root>/.eidetic/memory` (committed, team- and mesh-shared). Inserted
  idempotently (skipped if already present), slotted under an existing
  "Conventions and workflow" heading when one exists, else appended.

### Changed

- **Refreshed the `remember` + `recall` wrappers from eidetic-cli 0.10.0**
  (cite-don't-import) — picks up eidetic's **project-local store default**: the
  files backend now resolves per record by visibility — PUBLIC records inside a
  git repo go to `<repo-root>/.eidetic/memory` (committed, team-shared), PRIVATE
  records (or any record outside a repo) go to `$HOME/.eidetic/memory` (never
  committed), an explicit `EIDETIC_DATA_DIR` still wins, and recall reads both
  stores and merges. Also carries the 0.9.3 hardening (interactive-stdin guard,
  `help` as a search term, SIGPIPE-safe suffix parsing). **Recipe policy
  override (the wrappers here are NOT byte-verbatim):** the injected default
  visibility is flipped from eidetic's `private` to **`public`**, so a plain
  `/remember` lands the note in `./.eidetic/memory` in this repo, kept as part
  of the repo — pass `--visibility private` to route a record to `$HOME`
  instead. `remember` drives `eidetic remember` (idempotent upsert of one JSON
  record or an NDJSON batch on stdin); `recall` drives `eidetic recall` with
  four search modes (exact / approximate / keyword / hybrid). Each `SKILL.md` is
  localized only in the illustrative `--scope <nick>` examples (Provenance keeps
  "First-party to eidetic-cli"). Runtime dep: the `eidetic` CLI on PATH (else a
  local eidetic-cli checkout with `uv`) — **`eidetic >= 0.10.0`** for the
  in-repo routing; on an older CLI the public records still work but are stored
  in `$HOME/.eidetic/memory` instead of in-repo. Propagated by rollout-cli's
  `eidetic-memory` recipe.

## [0.5.0] - 2026-06-23

### Added

- **Vendored the `remember` + `recall` memory skills from eidetic-cli**
  (cite-don't-import) — the write/read halves of eidetic's shared
  `~/.eidetic/memory` surface, so this agent (Claude and its colleague backend)
  can persist facts across sessions and recall them later, sharing one store.
  `remember` drives `eidetic remember` (idempotent upsert of one JSON record or
  an NDJSON batch on stdin, dedup by id + content hash); `recall` drives
  `eidetic recall` with four search modes — exact / approximate / keyword /
  hybrid — each hit carrying text, full provenance metadata, a relevance score,
  and a freshness signal. The `.sh` wrappers are byte-verbatim from eidetic-cli
  (their first-party origin); each `SKILL.md` is localized only in the
  illustrative `--scope <nick>` examples (Provenance keeps "First-party to
  eidetic-cli"). Both default to this agent's PRIVATE scope, reading the suffix
  from `culture.yaml`. Runtime dep: the `eidetic` CLI on PATH (else a local
  eidetic-cli checkout with `uv`). Propagated by rollout-cli's `eidetic-memory`
  recipe.

## [0.4.0] - 2026-06-18

Milestone 1 of [#1](https://github.com/agentculture/ec2bedrock-cli/issues/1):
the *prove-the-economics* layer — answer "is self-managed EC2 cheaper than a
token provider for this ADLC workload?" entirely offline, with no EC2 lifecycle,
no model serving, and no live AWS.

### Added

- **`ec2bedrock/cost/` domain** — an inference `Profile` schema with a bundled
  `qwen27b-awq-l40s` default (g6e.xlarge / L40S / vLLM / AWQ); a `config.toml`
  loader (stdlib `tomllib`) that layers user profiles + provider pricing over the
  defaults; a scheduled-cost `estimate`; break-even math (output-only tokens/sec
  and an input+output-aware figure); an EC2-vs-token-provider `compare` yielding a
  recommendation (`ec2` / `token-provider` / `mixed`); and a `decide` router
  verdict from workload class + sensitivity.
- **CLI verbs** — `profile list` / `profile show`, `estimate`, `compare`, and
  `decide`, all with `--json`. `compare` and `decide` encode the recommendation in
  a deterministic process exit code (`ec2`=0, `token-provider`=20, `mixed`=21) so
  an ADLC router can branch on it.
- **`ec2-cli>=0.5` runtime dependency** — milestone 1 reuses ec2-cli's
  boto3-free `ec2.aws.pricing.estimate_cost` for the per-machine arithmetic
  through an adapter that normalises the `Estimate` shape across ec2-cli 0.5.x /
  0.6.x. boto3 is never imported and no command touches a live AWS account.
- **Docs** — `explain` catalog entries for the new verbs and a milestone-1
  quickstart in the README.

## [0.3.2] - 2026-06-18

### Added

- **`ask-colleague` piloting verbs** (`monitor` / `guide` / `stop`) and the
  `--watch` flag on `explore` / `review` / `write` — propagated by the
  deterministic mass-update. `--watch` arms a flight so it can be watched
  (`monitor`), guided mid-flight (`guide`), or cooperatively stopped (`stop`);
  control applies at the running loop's next turn boundary. The pilot verbs are
  pure `.colleague/flight/` file I/O and are exempt from the git-work-tree guard.

### Fixed

- **Command surface now matches the installed command.** The CLI command is
  `ec2bedrock` (`[project.scripts]`), but the scaffold's help text, `explain`
  catalog, `learn` map, and `README` examples still said `ec2bedrock-cli` (the
  PyPI dist + mesh nick, not an invocable command). Swept the command-surface
  references `ec2bedrock-cli` → `ec2bedrock` and added `("ec2bedrock",)` as the
  primary `explain` catalog key (keeping `("ec2bedrock-cli",)` as a back-compat
  alias). The dist name, mesh nick (`_FALLBACK_NICK`), and `_ISSUES_URL` stay
  `ec2bedrock-cli`. Fixes the `explain_self` agent-first rubric check (the `lint`
  CI gate was 25/26 → now 26/26).
- **License metadata now matches the `LICENSE` file.** The repo ships an Apache
  2.0 `LICENSE`, but `pyproject.toml` declared `license = "MIT"` with an MIT OSI
  classifier and the `README` license line said MIT. Aligned `pyproject.toml`
  (`license = "Apache-2.0"` + Apache OSI classifier) and the `README` line to
  Apache 2.0 — a stale `culture-agent-template` scaffold value, not a relicense.

## [0.3.1] - 2026-06-13

### Changed

- CLAUDE.md: add a convention to reach for the `ask-colleague` skill reflexively
  for explore/review/write/grade — read-only `review`/`explore` are always safe;
  side-effecting `write` needs the user's go-ahead.

## [0.3.0] - 2026-06-13

### Added

- AGENTS.colleague.md resident prompt file (backend colleague <-> AGENTS.colleague.md)

### Changed

- Promote agent identity to a colleague resident: culture.yaml backend
  claude -> colleague with a pinned model. The `doctor` backend-consistency
  map gains `colleague` -> AGENTS.colleague.md.

## [0.2.1] - 2026-06-12

### Changed

- **Re-vendored the `ask-colleague` skill from colleague (now 1.7.0, up from the
  0.39.2 sync)** — the wrapper had drifted multiple releases behind origin. Picks
  up the `clean` verb (reap stale/corrupt `colleague/*` branches + orphaned
  `.colleague/` artifacts a crashed run left behind), the `--json` flag on every
  verb (result JSON on stdout, diagnostics/digest on stderr), the
  `_colleague_via_uv` local-dev resolution that honors `--repo`, and the
  tri-state (0/1/2) exit-code contract. `scripts/ask-colleague.sh` + `prompts/`
  are byte-identical to the origin; `SKILL.md` diverges only in the one
  consumer-identifying Provenance clause (`ec2bedrock-cli vendors from
  guildmaster`). `docs/skill-sources.md` sync row updated to
  `2026-06-12 (colleague 1.7.0, direct)`. Refs: colleague#183, #186.

## [0.2.0] - 2026-06-06

### Added

- **`ask-colleague` skill** (`.claude/skills/ask-colleague/`) — the first-party front door to the `colleague` CLI (the renamed `convertible`). On top of `explore` / `review` / `write` it adds a `feedback` verb (grade a finished work item — the ROI loop), and `write` now **previews by default** in a throwaway worktree (no side effects) unless `--apply` / `--pr` is given. Reach for it reflexively — `review` for a diverse second opinion on a committed diff before opening a PR, `explore` for a fresh read of an unfamiliar area.

### Changed

- **Replaced the `outsource` skill with `ask-colleague`.** `outsource` was renamed to `ask-colleague` upstream ([colleague#148](https://github.com/agentculture/colleague/pull/148)). Because guildmaster has not re-broadcast the rename yet (its kit still ships the old `outsource`), `ask-colleague` is vendored **directly from the sibling `colleague` checkout** rather than from guildmaster — a tracked local divergence recorded in `docs/skill-sources.md`, parallel to the `agex` → `devex` one. Vendored verbatim except one consumer-identifying clause in the Provenance paragraph.
- **Ledger + CLAUDE.md + `.gitignore`:** point `docs/skill-sources.md` and the CLAUDE.md Skills section at `colleague` / `ask-colleague`, swap the *optional* runtime prerequisite `convertible` → `colleague` (env prefix `CONVERTIBLE_*` → `COLLEAGUE_*`, with the legacy names kept as a deprecated fallback), and gitignore the `.colleague/` run-artifact dir the skill writes (plus the stale `.agex/`).

## [0.1.4] - 2026-05-31

### Added

- **Vendor the `outsource` skill** (`.claude/skills/outsource/`) from
  guildmaster's canonical copy (origin
  [`agentculture/convertible`](https://github.com/agentculture/convertible),
  re-broadcast via guildmaster — guildmaster
  [#51](https://github.com/agentculture/guildmaster/pull/51)). Every agent
  cloned from this template now inherits the ability to hand a scoped task to a
  *different* engine/mind: `explore` (read-only investigation), `review` (a
  diverse second opinion on the committed diff), and `write` (delegate a small
  implementation). `explore`/`review` run isolated in a throwaway `git worktree`;
  `write` refuses a dirty tree. Fulfils
  [#8](https://github.com/agentculture/ec2bedrock-cli/issues/8).
- **Ledger + CLAUDE.md:** record `outsource` in `docs/skill-sources.md`
  (origin = convertible, re-broadcast via guildmaster; vendored verbatim — it
  already carries `type: command`) and document its *optional* runtime
  dependency on the `convertible` CLI (the skill exits with an install hint if
  absent, so a clone that never uses it is unaffected).

### Changed

### Fixed

## [0.1.3] - 2026-05-31

### Changed

- Expanded the clone-and-rename instructions in `CLAUDE.md`: added `README.md` to
  the rename targets and a portable `git grep` discovery command so a cloner can
  find every occurrence of the template name (hard-coded in ~100 places across the
  package, including the CLI command files and `_ISSUES_URL` in
  `ec2bedrock/cli/__init__.py`) rather than renaming by hand.
- Synced `README.md`'s "Make it your own" checklist with `CLAUDE.md`: it now lists
  `README.md` itself as a rename target and points to `CLAUDE.md`'s discovery
  command as the authoritative procedure, so the two onboarding checklists no
  longer drift.

## [0.1.2] - 2026-05-30

### Changed

- Renamed the PR-lifecycle CLI references `agex` / `agex-cli` to `devex` (same
  tool, new name) across `CLAUDE.md`, `docs/skill-sources.md`, `.gitignore`, and
  the vendored `cicd`, `assign-to-workforce`, and `communicate` skills — the
  `cicd` scripts now invoke `devex pr`.
- Logged the vendored-skill in-place patch as a local divergence in
  `docs/skill-sources.md`; the matching canonical rename is tracked upstream for
  guildmaster in
  [agentculture/guildmaster#48](https://github.com/agentculture/guildmaster/issues/48)
  so a future re-sync reconciles cleanly.
- Aligned the documented `devex` version floor to `>=0.21` across the vendored
  `cicd` `SKILL.md` and `workflow.sh` install hint (were `>=0.1`), matching
  `docs/skill-sources.md` and the `await`-era feature set; flagged upstream on
  guildmaster#48.

### Fixed

- SonarCloud now reports code coverage — added `relative_files = true` to
  `[tool.coverage.run]` so `coverage.xml` emits repo-relative paths that map to
  `sonar.sources=ec2bedrock` (absolute / `.venv` paths were dropped
  as unmappable). Mirrors the sibling `convertible` setup.

## [0.1.1] - 2026-05-26

### Changed

- **CI gates on the SonarCloud quality gate**
  ([issue #3](https://github.com/agentculture/ec2bedrock-cli/issues/3)) —
  added `sonar.qualitygate.wait=true` to `sonar-project.properties` so a failing
  gate fails the `test` job when `SONAR_TOKEN` is set. Token-less repos and fork
  PRs remain green (the scan step is guarded by `if: env.SONAR_TOKEN != ''`).

## [0.1.0] - 2026-05-26

### Added

- **Onboarded into the AgentCulture mesh** ([issue #1](https://github.com/agentculture/ec2bedrock-cli/issues/1)).
- **Agent-first CLI** cited from teken's (`afi-cli`) `python-cli` reference
  (`teken cli cite`) — verbs `whoami`, `learn`, `explain`, `overview`, `doctor`,
  and the `cli` noun group. Runtime is self-contained (`dependencies = []`);
  `teken>=0.8` is a dev dependency only. Passes the seven-bundle agent-first
  rubric (`teken cli doctor . --strict`). `doctor` checks the agent-identity
  invariants (prompt-file-present, backend-consistency, skills-present).
- **Mesh identity**: `culture.yaml` (`suffix: ec2bedrock-cli`,
  `backend: claude`) and the matching `CLAUDE.md` prompt file.
- **Canonical guildmaster skill kit** (11 skills) vendored under
  `.claude/skills/` (cite-don't-import): `agent-config`, `assign-to-workforce`,
  `cicd`, `communicate`, `doc-test-alignment`, `pypi-maintainer`, `run-tests`,
  `sonarclaude`, `spec-to-plan`, `think`, `version-bump`. Every `SKILL.md`
  carries `type: command` (load-bearing for the culture/claude backend);
  `cicd` / `communicate` consumer-identifying prose adapted, all script bodies
  verbatim. Provenance in `docs/skill-sources.md`. Three skills (`think`,
  `spec-to-plan`, `assign-to-workforce`) originate in `devague`, re-broadcast
  via guildmaster.
- **Build + deploy baseline**: `pyproject.toml` (hatchling), `tests/` (pytest,
  xdist, coverage), `.github/workflows/{tests,publish}.yml` (CI rubric/lint gate,
  PyPI Trusted Publishing), `.flake8`, `.markdownlint-cli2.yaml`,
  `sonar-project.properties`, and `.claude/skills.local.yaml.example`.

### Changed

### Fixed
