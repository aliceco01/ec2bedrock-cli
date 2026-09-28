#!/bin/bash
# Runs on the instance (run.sh pipes it over SSH): one `vllm bench serve` pass
# per concurrency level against the local server, from inside the server's own
# container. Results land in /opt/bench/results, mounted from the host.
# Usage: remote-sweep.sh MODEL INPUT_LEN OUTPUT_LEN "CONCURRENCY LEVELS"
set -euo pipefail
MODEL=$1
INPUT_LEN=$2
OUTPUT_LEN=$3
CONCURRENCY=$4
mark() { echo "$(date +%s) $1" >>/var/log/bench-timeline.log; }

bench() { # concurrency, prompts, result file ("" = warm-up, not saved)
  local save=()
  if [[ -n "$3" ]]; then
    save=(--save-result --result-dir /opt/bench/results --result-filename "$3")
  fi
  docker exec vllm vllm bench serve \
    --backend openai --base-url http://127.0.0.1:8000 --model "$MODEL" \
    --dataset-name random --random-input-len "$INPUT_LEN" --random-output-len "$OUTPUT_LEN" \
    --ignore-eos --num-prompts "$2" --max-concurrency "$1" \
    --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,90,99 \
    "${save[@]}"
}

mark sweep_start
bench 4 8 "" # warm-up
for c in $CONCURRENCY; do
  # Enough requests per level to reach a steady state: 8 per slot, at least 20.
  prompts=$((c * 8 > 20 ? c * 8 : 20))
  bench "$c" "$prompts" "in${INPUT_LEN}_out${OUTPUT_LEN}_c${c}.json"
  mark "sweep_c${c}_done"
done
mark sweep_done
