# Troubleshooting lab

Two deliberately broken deployments, each a fault that really happens in this
project's delivery path. Both run in their own namespace, `ml-tracker-lab`, so
they never touch the real release and Argo CD never sees them.

Real output from running both against the kind cluster is in
[`docs/troubleshooting-output.txt`](../docs/troubleshooting-output.txt).

```bash
kubectl apply -f troubleshooting/namespace.yaml
```

## 1. Broken image: `ImagePullBackOff`

```bash
kubectl apply -f troubleshooting/broken-image.yaml
```

**Symptom.** The Pod never starts.

```
$ kubectl get pods -n ml-tracker-lab -l app=lab-backend
NAME                           READY   STATUS             RESTARTS   AGE
lab-backend-67567bdff6-dg46p   0/1     ImagePullBackOff   0          25s
```

**Investigate.** The status only says the pull is failing. The events say why.

```bash
kubectl describe pod -n ml-tracker-lab -l app=lab-backend   # read Events at the bottom
kubectl get events -n ml-tracker-lab --sort-by=.lastTimestamp
```

```
Failed to pull image "ghcr.io/anisha-singhal/ml-experiment-tracker-backend:28917b4":
  ... failed to resolve reference ...: not found
```

**Cause.** `not found` means the registry was reached and has no such tag. That
is different from `unauthorized` (a private package or missing pull secret) and
from a DNS or timeout error (the node cannot reach the registry). CI tags every
image with the **full** 40-character commit SHA; `28917b4` is the short form,
which was never published.

**Fix.** Point the Deployment at a tag that exists:

```bash
kubectl set image -n ml-tracker-lab deployment/lab-backend \
  backend=ghcr.io/anisha-singhal/ml-experiment-tracker-backend:28917b4c0a38cd63cb06c9e99f0285de82c102b9
kubectl rollout status -n ml-tracker-lab deployment/lab-backend
```

**Prevention.** [`scripts/deploy-sha.sh`](../scripts/deploy-sha.sh) runs
`docker manifest inspect` on both images before it changes
`values-gitops.yaml`, so this fault cannot reach the real deployment through
the normal path.

## 2. Broken Service: no endpoints

```bash
kubectl apply -f troubleshooting/broken-service.yaml
```

**Symptom.** Everything looks healthy, and nothing works. The Pods are
`Running` and `1/1` Ready, the Service has a ClusterIP, but every request to it
is refused.

```
$ kubectl get endpoints -n ml-tracker-lab lab-web
NAME      ENDPOINTS   AGE
lab-web   <none>      8s

$ curl http://lab-web/healthz      # from a pod inside the namespace
curl: (7) Failed to connect to lab-web port 80 after 2 ms: Could not connect to server
```

**Investigate.** `<none>` endpoints with Ready Pods means the Service is not
selecting them. Compare its selector with the Pods' labels:

```bash
kubectl get svc -n ml-tracker-lab lab-web -o jsonpath='{.spec.selector}'
kubectl get pods -n ml-tracker-lab --show-labels
```

```
{"app":"lab-frontend"}
lab-web-8679b485f8-9cvb8   1/1   Running   ...   app=lab-web,pod-template-hash=8679b485f8
```

**Cause.** A Service finds its Pods by label, not by name. It asks for
`app=lab-frontend`; the Pods carry `app=lab-web`. No matching labels, no
endpoints, no traffic.

**Fix.**

```bash
kubectl patch svc -n ml-tracker-lab lab-web -p '{"spec":{"selector":{"app":"lab-web"}}}'
kubectl get endpoints -n ml-tracker-lab lab-web    # 10.244.1.13:8080,10.244.2.14:8080
```

The same request now returns `200`.

**Prevention.** The chart builds both the Deployment's Pod labels and the
Service selector from one helper, `mltracker.selectorLabels` in
[`_helpers.tpl`](../helm/mltracker/templates/_helpers.tpl), so the two cannot
drift apart.

## Clean up

```bash
kubectl delete namespace ml-tracker-lab
```
