# Shared settings for the g6e benchmark scripts. Source it, don't run it.
# Override any value by exporting it before running a script.
# shellcheck shell=bash

: "${BENCH_REGION:=us-east-1}"                   # g6e.xlarge is $1.861/h on demand here
: "${BENCH_INSTANCE_TYPE:=g6e.xlarge}"           # 1x L40S 48 GB, 4 vCPU, 32 GiB RAM
: "${BENCH_MODEL:=Qwen/Qwen3-32B-AWQ}"           # Bedrock sells the same model as Qwen3 32B
: "${BENCH_VLLM_IMAGE:=vllm/vllm-openai:v0.30.0}"
: "${BENCH_MAX_MODEL_LEN:=16384}"
: "${BENCH_VOLUME_GB:=200}"                      # the profile's storage_gb
: "${BENCH_VOLUME_THROUGHPUT:=125}"              # gp3 baseline MB/s; bounds model load time
: "${BENCH_HOURLY_USD:=1.861}"                   # on-demand price, for the report
: "${BENCH_NAME:=ec2bedrock-bench}"              # tag value, key pair and security group name
: "${BENCH_KEY_FILE:=$HOME/.ssh/${BENCH_NAME}.pem}"

BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_STATE="$BENCH_DIR/.state"
mkdir -p "$BENCH_STATE"

# Never fall back to whichever credentials are the default on this machine:
# every run has to name the AWS profile (account) that pays for it.
if [[ -z "${AWS_PROFILE:-}" ]]; then
  echo "error: set AWS_PROFILE to the profile of the account that should pay for this run" >&2
  exit 1
fi
export AWS_REGION="$BENCH_REGION" AWS_DEFAULT_REGION="$BENCH_REGION"

log() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
now() { date +%s; }
state() { cat "$BENCH_STATE/$1" 2>/dev/null || true; }
save() { printf '%s\n' "$2" >"$BENCH_STATE/$1"; }
forget() { for key in "$@"; do rm -f "$BENCH_STATE/$key"; done; }
confirm() {
  [[ "${BENCH_YES:-}" == 1 ]] && return 0
  local answer
  read -r -p "$1 [y/N] " answer
  [[ "$answer" == [yY] ]]
}
ssh_bench() {
  ssh -i "$BENCH_KEY_FILE" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
    "ubuntu@$(state host)" "$@"
}
