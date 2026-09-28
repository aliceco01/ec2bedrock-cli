# g6e benchmark: self-hosted Qwen3 32B vs Bedrock

`ec2bedrock compare` assumes one g6e.xlarge serves 80-180 output tokens per
second. This kit measures it: throughput and latency with vLLM on one
g6e.xlarge (1x L40S, 48 GB), how long the instance takes to become ready, and
what that makes the cost per 1M tokens against Bedrock's price for the same
model.

## What it measures

- **Throughput and latency** at 1, 4, 8, 16 and 32 concurrent requests, each
  with 4,096 input and 512 output tokens (an agent reading code and writing a
  patch), using `vllm bench serve`.
- **Cold start**: from the launch request to a model that answers, split into
  boot, image pull, weight download and model load.
- **Warm start**: stop and start the instance, then time how long the model
  takes to answer again, loading from EBS. GPU instances can't hibernate, so
  this is the fastest way back.
- **Cost**: EC2 dollars per 1M output tokens with the instance 100% busy,
  against Bedrock's price for the same tokens, and the break-even utilization
  (how busy the instance must be, on average, for EC2 to cost the same).

The model is `Qwen/Qwen3-32B-AWQ` (4-bit), because Bedrock sells Qwen3 32B at
$0.15 per 1M input and $0.60 per 1M output tokens. It runs in
`vllm/vllm-openai:v0.30.0` on the Deep Learning Base OSS Nvidia Driver GPU AMI
(Ubuntu 22.04). All of these are set in `env.sh` and can be overridden.

## Before you start

- Your own AWS account as a named profile: `export AWS_PROFILE=<profile>`.
  The scripts refuse to run without it, so default credentials are never used
  by accident.
- The "Running On-Demand G and VT instances" quota (code `L-DB2E81BA`) at 4
  vCPUs or more in us-east-1. New accounts start at 0, and approval can take
  days.
- A budget alarm. A full run is about 1.5 instance hours, about $3 at
  $1.861/h.

## Steps

| Step | Script | Bills? | Time |
|---|---|---|---|
| 1 | `preflight.sh`: account, quota, AMI, dry-run launch | no | 1 min |
| 2 | `up.sh`: key pair, SSH-only security group, launch | from here on | 2 min |
| 3 | `run.sh`: wait for the model, run the sweep, copy results | yes | 15-20 min, then about 40 |
| 4 | `restart-test.sh`: stop, start, time until ready | yes | about 10 min |
| 5 | `down.sh`: delete everything, check nothing is left | stops billing | 2 min |
| 6 | `python3 summarize.py results/<run id>` | no | seconds |

Run step 5 even if a step fails. If `restart-test.sh` fails on
`InsufficientInstanceCapacity`, the instance stays stopped: compute billing has
stopped, but the volume still bills until `down.sh`.

The instance accepts SSH only from the IP that ran `up.sh`, requires IMDSv2,
and the vLLM API listens on localhost only. Everything the kit creates carries
the tag `Project=ec2bedrock-bench`.

## Results

`run.sh` writes `results/<run id>/`: one `vllm bench serve` JSON per
concurrency level, `timeline.log` (bootstrap events on the instance),
`local-timeline.log` (launch events), `server.log` (vLLM's KV cache and
concurrency lines) and `config.env`. `restart-test.sh` adds
`restart-timeline.log`. `summarize.py` prints the report and saves it as
`report.md`; `--provider-input` and `--provider-output` compare against other
prices.

Commit the results directory with the report: the measured throughput is what
replaces `performance.expected_aggregate_tps` in the default profile.

## How the scripts share state

Each script keeps what the next one needs in `bench/.state/` (not committed),
one value per file:

| Key | Written by | Read by |
|---|---|---|
| `ami`, `root_device` | `preflight.sh` | `up.sh`, `run.sh` |
| `sg`, `instance`, `launch_requested`, `running_at` | `up.sh` | `run.sh`, `down.sh` |
| `host` (public DNS name) | `up.sh`, `restart-test.sh` (it changes on every start) | `run.sh`, `restart-test.sh` |
| `run_id` | `run.sh` | `restart-test.sh` |

Timeline files hold one `<epoch seconds> <event>` line per event.
`restart-timeline.log` uses the events `stop_requested`, `stopped`,
`start_requested`, `running` and `server_ready`, which is what `summarize.py`
reads.
