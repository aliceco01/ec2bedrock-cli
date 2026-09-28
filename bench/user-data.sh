#!/bin/bash
# First-boot bootstrap for the benchmark instance (cloud-init runs it once, as
# root). up.sh fills in the __PLACEHOLDERS__. Each phase appends
# "<epoch seconds> <event>" to /var/log/bench-timeline.log so the cold start
# can be timed. The server container restarts on every boot, so a stop/start
# later measures a warm start from the image and weights already on EBS.
set -euxo pipefail
MODEL="__MODEL__"
IMAGE="__VLLM_IMAGE__"
MAX_MODEL_LEN="__MAX_MODEL_LEN__"
TIMELINE=/var/log/bench-timeline.log
mark() { echo "$(date +%s) $1" >>"$TIMELINE"; }

mark userdata_start
if ! command -v docker >/dev/null; then
  apt-get update -y
  apt-get install -y docker.io
fi
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
mark docker_ready

docker pull "$IMAGE"
mark image_pulled

# Weights and vLLM's compile cache live on the EBS root volume, not on the
# instance-store NVMe, so they survive a stop/start.
mkdir -p /opt/hf /opt/vllm-cache /opt/bench/results
docker run --rm -v /opt/hf:/root/.cache/huggingface --entrypoint python3 "$IMAGE" \
  -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL')"
mark model_downloaded

# The API listens on localhost only; the benchmark runs next to it.
docker run -d --name vllm --restart unless-stopped \
  --runtime nvidia --gpus all --ipc=host -p 127.0.0.1:8000:8000 \
  -v /opt/hf:/root/.cache/huggingface -v /opt/vllm-cache:/root/.cache/vllm \
  -v /opt/bench:/opt/bench \
  "$IMAGE" --model "$MODEL" --max-model-len "$MAX_MODEL_LEN"
mark server_started

if timeout 2400 bash -c 'until curl -sf http://127.0.0.1:8000/health >/dev/null; do sleep 2; done'; then
  mark server_ready
else
  mark server_failed
fi
