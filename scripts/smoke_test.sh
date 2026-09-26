#!/usr/bin/env bash
# End-to-end check through the gateway: upload → worker processes → thumbnail served.
# Usage: scripts/smoke_test.sh   (env: BASE_URL, TIMEOUT_SECONDS)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:${GATEWAY_PORT:-8080}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-30}"
FIXTURE="$(dirname "$0")/fixtures/sample.jpg"

json_field() { python3 -c "import sys, json; print(json.load(sys.stdin)$1)"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "Smoke test against $BASE_URL"

health=$(curl -fsS "$BASE_URL/api/health") || fail "health check failed"
echo "  health: $health"

job_id=$(curl -fsS -F "file=@$FIXTURE;type=image/jpeg" "$BASE_URL/api/jobs" | json_field '["id"]') \
  || fail "upload failed"
echo "  uploaded job $job_id"

deadline=$((SECONDS + TIMEOUT_SECONDS))
while :; do
  status=$(curl -fsS "$BASE_URL/api/jobs/$job_id" | json_field '["status"]')
  case "$status" in
    done) break ;;
    failed) fail "job failed: $(curl -fsS "$BASE_URL/api/jobs/$job_id" | json_field '["error"]')" ;;
  esac
  ((SECONDS < deadline)) || fail "job still '$status' after ${TIMEOUT_SECONDS}s"
  sleep 1
done
echo "  job done"

thumb_url=$(curl -fsS "$BASE_URL/api/jobs/$job_id" | json_field '["thumbnails"][0]["url"]')
read -r code type < <(curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' "$BASE_URL$thumb_url")
[[ "$code" == 200 && "$type" == image/webp* ]] || fail "thumbnail $thumb_url returned $code $type"
echo "  thumbnail served: $thumb_url ($type)"

echo "PASS"
