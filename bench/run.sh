#!/usr/bin/env bash
# Wait for the server on the running benchmark instance, run the throughput
# sweep there, and copy the results into bench/results/<run id>/.
set -euo pipefail
source "$(dirname "$0")/env.sh"

if [[ -z "$(state host)" ]]; then
  log "error: no running instance is recorded in bench/.state"
  exit 1
fi

log "waiting for the server (first boot pulls the image and about 19 GB of weights)"
until ssh_bench 'grep -qE "server_(ready|failed)" /var/log/bench-timeline.log' 2>/dev/null; do
  sleep 20
done
if ! ssh_bench 'grep -q server_ready /var/log/bench-timeline.log'; then
  log "error: the server did not come up. Look at: sudo docker logs vllm"
  exit 1
fi

run_id=${BENCH_RUN_ID:-$(date -u +%Y%m%dT%H%MZ)}
out="$BENCH_DIR/results/$run_id"
mkdir -p "$out"
save run_id "$run_id"

input_len=${BENCH_INPUT_LEN:-4096}
output_len=${BENCH_OUTPUT_LEN:-512}
levels=${BENCH_CONCURRENCY:-1 4 8 16 32}
log "sweep: ${input_len} in / ${output_len} out tokens, concurrency $levels"
ssh_bench "sudo bash -s -- '$BENCH_MODEL' '$input_len' '$output_len' '$levels'" \
  <"$BENCH_DIR/remote-sweep.sh"

scp -i "$BENCH_KEY_FILE" "ubuntu@$(state host):/opt/bench/results/*.json" "$out/"
ssh_bench 'cat /var/log/bench-timeline.log' >"$out/timeline.log"
ssh_bench 'sudo docker logs vllm 2>&1 | grep -iE "kv cache|concurrency" | head -20' \
  >"$out/server.log" || true
printf '%s launch_requested\n%s running\n' "$(state launch_requested)" "$(state running_at)" \
  >"$out/local-timeline.log"
cat >"$out/config.env" <<EOF
instance_type=$BENCH_INSTANCE_TYPE
region=$BENCH_REGION
model=$BENCH_MODEL
vllm_image=$BENCH_VLLM_IMAGE
max_model_len=$BENCH_MAX_MODEL_LEN
volume_gb=$BENCH_VOLUME_GB
volume_throughput_mbps=$BENCH_VOLUME_THROUGHPUT
hourly_usd=$BENCH_HOURLY_USD
ami=$(state ami)
EOF
log "results in $out"
log "report: python3 bench/summarize.py $out"
