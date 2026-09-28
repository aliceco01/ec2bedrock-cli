#!/usr/bin/env bash
# Tear everything down: terminate the instance (its volume goes with it),
# delete the security group and key pair, then check that nothing tagged for
# the benchmark is left billing.
set -euo pipefail
source "$(dirname "$0")/env.sh"

instance=$(state instance)
if [[ -n "$instance" ]]; then
  aws ec2 terminate-instances --instance-ids "$instance" >/dev/null
  log "terminating $instance"
  aws ec2 wait instance-terminated --instance-ids "$instance"
fi

sg=$(state sg)
if [[ -n "$sg" ]]; then
  aws ec2 delete-security-group --group-id "$sg"
  log "deleted security group $sg"
fi

aws ec2 delete-key-pair --key-name "$BENCH_NAME" >/dev/null
rm -f "$BENCH_KEY_FILE"
forget instance host sg running_at launch_requested

instances=$(aws ec2 describe-instances --output text \
  --filters "Name=tag:Project,Values=$BENCH_NAME" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'length(Reservations[].Instances[])')
volumes=$(aws ec2 describe-volumes --output text \
  --filters "Name=tag:Project,Values=$BENCH_NAME" "Name=status,Values=creating,available,in-use" \
  --query 'length(Volumes)')
log "left behind: $instances instances, $volumes volumes (both should be 0)"
