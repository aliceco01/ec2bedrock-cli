#!/usr/bin/env bash
# Free checks before spending anything: account, region, GPU quota, AMI and a
# dry-run launch. Creates nothing.
set -euo pipefail
source "$(dirname "$0")/env.sh"

log "account: $(aws sts get-caller-identity --query Arn --output text)"

zones=$(aws ec2 describe-instance-type-offerings --location-type availability-zone \
  --filters "Name=instance-type,Values=$BENCH_INSTANCE_TYPE" \
  --query 'InstanceTypeOfferings[].Location' --output text)
if [[ -z "$zones" ]]; then
  log "error: $BENCH_INSTANCE_TYPE is not offered in $BENCH_REGION"
  exit 1
fi
log "$BENCH_INSTANCE_TYPE is offered in: $zones"

vcpus=$(aws ec2 describe-instance-types --instance-types "$BENCH_INSTANCE_TYPE" \
  --query 'InstanceTypes[0].VCpuInfo.DefaultVCpus' --output text)
quota=$(aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA \
  --query 'Quota.Value' --output text)
log "on-demand G and VT vCPU quota: $quota (need $vcpus)"
if ((${quota%.*} < vcpus)); then
  log "error: quota too low. Request more, then wait for approval:"
  log "  aws service-quotas request-service-quota-increase --service-code ec2" \
    "--quota-code L-DB2E81BA --desired-value 8 --region $BENCH_REGION"
  exit 1
fi

ami=$(aws ssm get-parameter \
  --name /aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-22.04/latest/ami-id \
  --query Parameter.Value --output text)
# Text output is tab-separated, and the AMI name contains spaces.
IFS=$'\t' read -r ami_name root_device < <(aws ec2 describe-images --image-ids "$ami" \
  --query 'Images[0].[Name, RootDeviceName]' --output text)
root_gb=$(aws ec2 describe-images --image-ids "$ami" --output text \
  --query "Images[0].BlockDeviceMappings[?DeviceName=='$root_device'].Ebs.VolumeSize | [0]")
log "AMI: $ami ($ami_name), root $root_device ${root_gb} GB"
if ((root_gb > BENCH_VOLUME_GB)); then
  log "error: the AMI's root snapshot (${root_gb} GB) is larger than BENCH_VOLUME_GB"
  exit 1
fi
save ami "$ami"
save root_device "$root_device"

out=$(aws ec2 run-instances --dry-run --image-id "$ami" \
  --instance-type "$BENCH_INSTANCE_TYPE" 2>&1 || true)
if ! grep -q DryRunOperation <<<"$out"; then
  log "error: dry-run launch refused: $out"
  exit 1
fi
log "dry-run launch: permitted"
log "preflight OK. A full run is about 1.5 GPU hours at \$$BENCH_HOURLY_USD/h."
