#!/usr/bin/env bash
# Generate traffic against the app so Prometheus and Grafana have something to
# show. Mixes successful reads, writes and deliberate 404s/422s, because a
# dashboard that only ever shows 200s proves nothing about error-rate panels.
#
# Usage: ./scripts/load-test.sh [base-url] [seconds]
set -uo pipefail

BASE="${1:-http://localhost:8080}"
DURATION="${2:-60}"
END=$(( $(date +%s) + DURATION ))

echo "driving load at $BASE for ${DURATION}s"
req=0
while [ "$(date +%s)" -lt "$END" ]; do
  curl -s -o /dev/null "$BASE/api/experiments"                 # 200
  curl -s -o /dev/null "$BASE/api/experiments/stats"           # 200
  curl -s -o /dev/null "$BASE/health"                          # 200
  curl -s -o /dev/null "$BASE/api/experiments/999999"          # 404, on purpose
  curl -s -o /dev/null -X POST "$BASE/api/experiments" \
       -H 'Content-Type: application/json' \
       -d '{"name":"bad"}'                                     # 422, on purpose
  req=$((req + 5))
done
echo "sent ~$req requests"
