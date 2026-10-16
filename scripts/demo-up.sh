#!/usr/bin/env bash
# Bring up every port-forward the demo needs and print where everything is.
# Leave it running in its own terminal tab; Ctrl-C stops all the forwards.
set -uo pipefail

kubectl config use-context kind-mltracker >/dev/null

# Stale forwards from an earlier session hold the ports and fail silently.
pkill -f "kubectl port-forward" 2>/dev/null
sleep 1

forward() {  # namespace service local:remote
  kubectl port-forward -n "$1" "svc/$2" "$3" >/dev/null 2>&1 &
}
forward argocd     argocd-server          8081:80
forward monitoring prometheus-prometheus  9090:9090
forward monitoring monitoring-grafana     3001:80
sleep 3

argocd_password=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)

check() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$1"; }

cat <<EOF

  App (through the Ingress)  http://localhost:8080                     $(check http://localhost:8080)
  Argo CD                    http://127.0.0.1:8081                     $(check http://127.0.0.1:8081)
                             user: admin   password: ${argocd_password}
  Prometheus targets         http://127.0.0.1:9090/targets             $(check http://127.0.0.1:9090/-/ready)
  Grafana                    http://127.0.0.1:3001                     $(check http://127.0.0.1:3001/api/health)
                             user: admin   password: admin
                             dashboard: Dashboards -> ML Experiment Tracker - Application

  Every code above should be 200. Leave this tab open; Ctrl-C stops the forwards.

EOF
wait
