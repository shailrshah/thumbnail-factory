#!/usr/bin/env bash
# Runs on the EC2 instance (as root, via SSM Run Command) from the deploy workflow, which first
# writes this script and compose.prod.yml into APP_DIR.
# Required env: ECR_REGISTRY, IMAGE_TAG, AWS_REGION.
set -euo pipefail

: "${ECR_REGISTRY:?}" "${IMAGE_TAG:?}" "${AWS_REGION:?}"
APP_DIR=/opt/thumbnail-factory
cd "$APP_DIR"

echo "Deploying $IMAGE_TAG"

# Uses the instance role; the token is valid for 12 hours, so log in on every deploy.
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Persisted so a reboot, or a manual `docker compose` on the box, keeps running the same tag.
printf 'ECR_REGISTRY=%s\nIMAGE_TAG=%s\n' "$ECR_REGISTRY" "$IMAGE_TAG" > .env

docker compose -f compose.prod.yml pull --quiet
docker compose -f compose.prod.yml up -d --wait --wait-timeout 180 --remove-orphans
docker compose -f compose.prod.yml ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}'

curl -fsS http://localhost/api/health
echo

docker image prune -f
