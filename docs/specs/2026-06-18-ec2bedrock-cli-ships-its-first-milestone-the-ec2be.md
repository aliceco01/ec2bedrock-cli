# ec2bedrock-cli ships its first milestone: the ec2bedrock CLI can define inference profiles and answer 'is self-managed EC2 cheaper than a token provider for this ADLC workload?' — estimate scheduled EC2 cost, compare against token-provider pricing, and explain break-even utilization — entirely offline, dry-run by default, with JSON output for a future ADLC router, and zero AWS mutation.

> ec2bedrock-cli ships its first milestone: the ec2bedrock CLI can define inference profiles and answer 'is self-managed EC2 cheaper than a token provider for this ADLC workload?' — estimate scheduled EC2 cost, compare against token-provider pricing, and explain break-even utilization — entirely offline, dry-run by default, with JSON output for a future ADLC router, and zero AWS mutation.

## Audience

- ADLC/Culture engineers and the future model router deciding whether to wake EC2 GPU capacity or call a token provider, plus AWS clients evaluating self-hosted inference economics.

## Before → After

- Before: Today ec2bedrock-cli is the culture-agent-template introspection scaffold (whoami/learn/explain/overview/doctor, empty runtime deps); issue #1's plan exists only as prose, no cost or profile logic.
- After: An engineer runs 'ec2bedrock profile show qwen27b-awq-l40s', 'ec2bedrock estimate --profile … --hours 8 --days 22', and 'ec2bedrock compare --profile … --input-tokens … --output-tokens …' and gets a costed EC2-vs-token-provider recommendation with break-even utilization — no AWS account, nothing launched.

## Why it matters

- ADLC only pays off when sustained office-hours agent work beats token-provider economics; you must prove the economics on paper before spending on GPUs or building lifecycle/serving machinery.

## Requirements

- Every command supports --json with a documented stable schema; estimate and compare also encode the recommendation in the process exit code so a router can branch on it.
  - honesty: estimate --json and compare --json validate against a documented schema in tests; compare's exit code maps deterministically to {EC2 / token-provider / mixed} and is documented.
- The break-even output answers issue #1's question: output-only break-even tokens/sec AND an input+output-aware break-even, so context-heavy ADLC workloads are modelled, not just output.
  - honesty: break-even is reported two ways — output-only tokens/sec, and an input+output-aware figure given an assumed input:output ratio — matching issue #1's worked numbers (≈172 tok/s output-only; EC2 wins earlier once input is included).

## Honesty conditions

- estimate, compare, and break-even all run with no network and no boto3 installed; --json emits a documented stable schema; no command mutates AWS.
- the JSON output is router-consumable: stable keys + an explicit decision field + an exit code that encodes the recommendation, not just human-readable text.
- all three commands produce correct, reproducible numbers from profile+args alone with zero AWS credentials present.
- the new cost/profile code is additive — the existing introspection scaffold (whoami/learn/explain/overview/doctor) and its tests pass unchanged; the ONLY new runtime dep is ec2-cli (itself boto3-free on a base install); config parsing is stdlib tomllib.
- compare output states a clear recommendation (EC2 / token-provider / mixed) AND the break-even utilization, so economics are legible, not just two totals.
- each of the six acceptance criteria maps to at least one passing test; the suite runs fully offline in CI.
- no milestone-1 code path imports boto3 or opens a socket; a test asserts estimate/compare/decide do not import boto3 and that pricing is read only from the profile + ec2-cli's boto3-free pricing module (no live AWS / Pricing API).

## Success signals

- Issue #1's six first-milestone acceptance criteria pass: define a profile, estimate scheduled EC2 cost, compare against token-provider cost, explain break-even utilization, emit router JSON, and run dry-run with no AWS mutation — verified by tests with zero network/boto3.

## Scope / boundaries

- Milestone 1 does NOT launch/stop/hibernate EC2 (Stage 2), does NOT serve a model/run vLLM (Stage 3), does NOT do schedules/fallback/Blackwell (Stages 5/6/8), and does NOT touch a live AWS account or the Pricing API — pricing is computed offline from the profile's hourly_usd plus ec2-cli's boto3-free estimate_cost arithmetic, never a live rate lookup.

## Assumptions

- RISK: the injected-rate estimate_cost signature M1 targets is finalized on ec2-cli's unmerged spec/issue-4-per-machine-cost (->0.6.0); released 0.5.0 has an estimate_cost of possibly-different signature and no rates table. M1's first build task MUST pin ec2-cli to a PyPI version whose pricing API it verifies against, or sequence behind ec2-cli 0.6.0.

## Decisions

- A bundled default profile 'qwen27b-awq-l40s' (g6e.xlarge, L40S, vLLM, AWQ, $1.861/hr, 200GB) ships in-package so estimate/compare work with zero user config; user config layers on top.
- COUPLING: M1 takes a runtime dependency on ec2-cli and imports ec2.aws.pricing (estimate_cost, Estimate) for per-machine cost arithmetic + UNKNOWN-degradation. GPU hourly rate comes from profile.hourly_usd (ec2-cli's static table has no GPU/g6e rows); EBS from profile.storage_gb x a bundled EBS rate. boto3 stays OUT of M1 — it is ec2-cli's optional [aws] extra and M1 imports only the boto3-free pricing module.
- VERBS: ship 'profile list', 'profile show', 'estimate', 'compare', AND 'decide --json' (workload-class + sensitive -> recommendation + exit code) — pulling Stage-7's router verb forward per the user's choice.
- CONFIG: M1 loads ~/.ec2bedrock/config.toml via stdlib tomllib (py3.12); ec2-cli is the ONLY new runtime dependency. The bundled default 'qwen27b-awq-l40s' profile is a Python literal so the tool works with zero config; a user config.toml layers over / overrides it.

## Open / follow-up

- coordinate ec2-cli to merge issue #4 (pricing.estimate_cost final signature + rates) to main and release the version ec2bedrock-cli M1 pins
