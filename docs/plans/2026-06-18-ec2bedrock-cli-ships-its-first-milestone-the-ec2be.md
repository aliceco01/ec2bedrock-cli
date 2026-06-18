# Build Plan — ec2bedrock-cli ships its first milestone: the ec2bedrock CLI can define inference profiles and answer 'is self-managed EC2 cheaper than a token provider for this ADLC workload?' — estimate scheduled EC2 cost, compare against token-provider pricing, and explain break-even utilization — entirely offline, dry-run by default, with JSON output for a future ADLC router, and zero AWS mutation.

slug: `ec2bedrock-cli-ships-its-first-milestone-the-ec2be` · status: `exported` · from frame: `ec2bedrock-cli-ships-its-first-milestone-the-ec2be`

> ec2bedrock-cli ships its first milestone: the ec2bedrock CLI can define inference profiles and answer 'is self-managed EC2 cheaper than a token provider for this ADLC workload?' — estimate scheduled EC2 cost, compare against token-provider pricing, and explain break-even utilization — entirely offline, dry-run by default, with JSON output for a future ADLC router, and zero AWS mutation.

## Tasks

### t1 — ec2-cli coupling adapter + dependency pin + offline/no-boto3 guard

- covers: c4, h12, h1, c20, h13
- acceptance:
  - pyproject adds ec2-cli as the only new runtime dependency, pinned to a version whose ec2.aws.pricing API is verified at import
  - ec2bedrock/cost/_ec2cli.py re-exports estimate_cost + Estimate; a test asserts estimate_cost accepts kwargs ondemand_rate/spot_rate/running_hours/ebs_monthly and that importing it does NOT pull boto3 into sys.modules
  - a static test asserts no module under ec2bedrock/cost imports boto3 at top level and no milestone-1 path opens a socket

### t2 — Profile schema + bundled default profiles

- covers: c3, c1
- acceptance:
  - ec2bedrock/cost/profiles.py defines a Profile dataclass (instance_type, gpu, runtime, quantization, hourly_usd, storage_gb, performance, lifecycle, budgets) and a DEFAULT_PROFILES registry with qwen27b-awq-l40s as a Python literal (g6e.xlarge/l40s-48gb/vllm/awq/1.861/200)
  - Profile round-trips to a plain dict for --json; unknown config fields raise a clear CliError, not a traceback

### t3 — config.toml loader over bundled defaults (stdlib tomllib)

- depends on: t2
- covers: h12, c3
- acceptance:
  - ec2bedrock/cost/config.py loads ~/.ec2bedrock/config.toml via stdlib tomllib, returning resolved profiles + token-provider pricing + budgets; missing file falls back to bundled defaults with no error
  - a user profile of the same name in config.toml overrides the bundled default; a test proves override + extend semantics

### t4 — Bundled rate data (EBS GB-month + default provider prices)

- covers: c5
- acceptance:
  - ec2bedrock/cost/rates.py exposes an EBS USD/GB-month rate (cited from ec2-cli rates concept) and default token-provider prices (input 0.58, output 3.01 USD/1M), each overridable; lookups return None/default and never raise

### t5 — EC2 scheduled-cost estimate

- depends on: t1, t2, t4
- covers: c3, h3
- acceptance:
  - ec2bedrock/cost/estimate.py estimate(profile, hours, days) returns an estimate where compute = hourly_usd*hours*days and ebs derives from storage_gb*ebs_rate, computed via ec2.aws.pricing.estimate_cost with the rate injected from the profile
  - estimate degrades to an UNKNOWN total (no crash) when a rate is missing, mirroring ec2-cli Estimate semantics; numbers reproduce with zero AWS credentials present

### t6 — Break-even math (output-only + input+output-aware)

- depends on: t4
- covers: c11, h9
- acceptance:
  - ec2bedrock/cost/breakeven.py computes output-only break-even tokens/sec from hourly_usd and provider output price, matching issue #1's ~172 tok/s worked figure
  - computes an input+output-aware break-even given an assumed input:output ratio, demonstrating EC2 wins earlier once input is included (issue #1 worked example)

### t7 — compare: EC2 vs token-provider -> recommendation + exit code

- depends on: t5, t6
- covers: c1, c5, h5, c10, h8
- acceptance:
  - ec2bedrock/cost/compare.py compare(...) returns ec2_usd, provider_usd, a recommendation in {ec2, token-provider, mixed}, and the break-even; provider cost = input*in_price + output*out_price
  - the recommendation maps to a documented, deterministic process exit code; a test asserts the mapping and the unknown-degradation path

### t8 — decide --json: workload-class + sensitive -> verdict + exit code

- depends on: t7
- covers: c2, h2
- acceptance:
  - ec2bedrock/cost/decide.py decide(workload, input_tokens, output_tokens, sensitive) returns {decision, reason, exit}; sensitive=true -> ec2, sporadic/off-hours -> token-provider, else cost-driven via compare
  - output is router-consumable: stable JSON keys + explicit decision field + exit code encoding the recommendation

### t9 — profile CLI command (list/show)

- depends on: t2, t3
- covers: c3
- acceptance:
  - ec2bedrock/cli/_commands/profile.py exposes register(sub) adding 'profile list' and 'profile show <name>' with --json; a test builds a throwaway parser, registers, and asserts list+show output for the bundled default WITHOUT touching cli/__init__.py

### t10 — estimate/compare/decide CLI commands (thin wrappers, file-disjoint per verb)

- depends on: t5, t7, t8
- covers: c10, h8
- acceptance:
  - ec2bedrock/cli/_commands/{estimate,compare,decide}.py each expose register(sub): estimate --profile --hours --days; compare --profile --input-tokens --output-tokens --provider-input-price --provider-output-price; decide --workload --input-tokens --output-tokens --sensitive; all support --json
  - each command's --json validates against the documented schema and the process exit code matches the domain recommendation; tested per-command via a throwaway parser, not the global parser

### t11 — Wire verbs into the CLI + end-to-end integration test

- depends on: t9, t10
- covers: c1, c3
- acceptance:
  - cli/__init__.py registers profile/estimate/compare/decide alongside the existing introspection verbs; the existing scaffold verbs and their tests pass unchanged
  - an integration test drives main(['profile','show','qwen27b-awq-l40s']), main(['estimate',...]), main(['compare',...]), main(['decide',...,'--json']) end-to-end offline and asserts exit codes

### t12 — explain catalog + README quickstart for the new verbs

- depends on: t11
- covers: c1
- acceptance:
  - ec2bedrock/explain/catalog.py gains entries for profile/estimate/compare/decide; README documents the milestone-1 quickstart matching the spec's after-state commands
  - teken rubric still passes (explain ec2bedrock resolves) and markdownlint is clean

### t13 — Acceptance-criteria matrix test (six M1 criteria, offline)

- depends on: t11
- covers: c7, h7, h1, c20
- acceptance:
  - tests/test_acceptance_m1.py asserts each of issue #1's six first-milestone criteria (define profile, estimate, compare, break-even, router JSON, dry-run/no-mutation) maps to >=1 passing assertion
  - the whole suite runs with no network and no boto3 installed; a guard asserts boto3 absence on the milestone-1 paths

### t14 — Version bump 0.3.2 -> 0.4.0 + CHANGELOG

- depends on: t11, t12, t13
- covers: c7
- acceptance:
  - pyproject + ec2bedrock/__init__.py bumped to 0.4.0; CHANGELOG gets a Keep-a-Changelog entry; version-check CI passes (0.4.0 > main 0.3.2)

## Risks

- [unknown_nonblocking] ec2-cli 0.6.0 (issue #4: final injected-rate estimate_cost signature + rates table) is unreleased; PyPI tops at 0.5.0. T1 must pin to a version whose pricing API it verifies against, or sequence M1 behind ec2-cli's 0.6.0 release. (task t1)
