# Presentation video — recording script

Target length **12–15 minutes**. Everything below has been run and works; the
commands are copy-pasteable in the order given.

Record with QuickTime (**File → New Screen Recording**, tick the microphone) or
OBS. Export as MP4 and save it to this folder as `demo/presentation.mp4`.

---

## Before you hit record

Get the whole environment up first. This takes a few minutes and you do not
want it happening on camera.

```bash
cd ~/ml-experiment-tracker

# 1. cluster + ingress + Argo CD (skip any that are already running)
kind create cluster --config k8s/kind-cluster.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/kind/deploy.yaml
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.1/manifests/install.yaml
kubectl wait --for=condition=available --timeout=420s deployment --all -n argocd

# 2. let Argo CD deploy the app
kubectl apply -f argocd/application.yaml

# 3. monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
kubectl apply -f monitoring/grafana-dashboard-configmap.yaml -n monitoring
```

Then open these tabs in this order, so you can move left to right on camera:

| Tab | URL |
|---|---|
| 1 | `demo/slides.pdf` (open in Preview, View → Slideshow, ⌘⇧F) |
| 2 | `https://github.com/anisha-singhal/ml-experiment-tracker` |
| 3 | `https://github.com/anisha-singhal/ml-experiment-tracker/actions` |
| 4 | `http://localhost:8080` — the app through the Ingress |
| 5 | `http://127.0.0.1:8081` — Argo CD |
| 6 | `http://127.0.0.1:9090/targets` — Prometheus |
| 7 | `http://127.0.0.1:3001` — Grafana |
| 8 | AWS Console — VPC and EKS pages |

Port-forwards, each in its own terminal tab:

```bash
kubectl port-forward -n argocd svc/argocd-server 8081:80
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
```

Argo CD login is `admin` plus:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

Grafana is `admin` / `prom-operator`.

**Log in to all of them before recording.** Nobody wants to watch you type a
password, and the Argo CD one is 16 random characters.

---

## Part 1 — Slides (3 minutes)

Share the deck and talk over slides 1–3.

> "This is ML Experiment Tracker, my DevOps capstone. It's a web application for
> tracking machine learning training runs — what was trained, on what data, with
> what hyperparameters, and how well it scored.
>
> I picked this domain because it's a problem I actually have. Once you've run
> more than a handful of experiments you lose track of which configuration
> produced the good number.
>
> One design decision I want to call out early, on slide 2: accuracy is
> nullable, not zero. A queued run hasn't been scored yet, and that's a
> different thing from having scored 0.0. That distinction runs through the
> database schema, the API responses and the UI."

Slide 3, the stack — read it, don't dwell.

Slide 4, the architecture, is the one to slow down on:

> "The flow is: I push to GitHub, GitHub Actions runs tests and builds images,
> Trivy scans them before anything is published, images go to GHCR tagged with
> the commit SHA. Terraform provisions the VPC and EKS cluster. Argo CD watches
> this repository and deploys the chart into Kubernetes. Prometheus scrapes the
> backend and Grafana renders it."

---

## Part 2 — Codebase (2 minutes)

Tab 2, the repository root. Scroll the folder list slowly.

> "Backend is FastAPI with SQLAlchemy 2 and Alembic migrations. Frontend is
> React built with Vite. The Helm chart is in helm/mltracker, Terraform in
> terraform/, the Argo CD Application in argocd/."

Open `backend/app/main.py`:

> "Nine endpoints. Two things worth pointing out. First, `/health` deliberately
> does not touch the database, but `/ready` does — a liveness probe that fails
> on a brief database problem would restart pods that are perfectly fine, so
> liveness checks the process and readiness checks the dependency.
>
> Second, the `/api/experiments/stats` route is declared **before**
> `/api/experiments/{experiment_id}`. FastAPI matches routes in definition
> order, so the other way round, `stats` gets captured as an experiment ID and
> you get a validation error instead of your statistics."

Open `backend/tests/conftest.py`:

> "Tests run against SQLite with a StaticPool, injected by overriding the
> `get_db` dependency. Seventeen tests, and they never touch the real database."

---

## Part 3 — CI/CD, live (3 minutes)

This is the part the rubric asks you to actually trigger. Make a real change.

```bash
cd ~/ml-experiment-tracker
# edit the dashboard heading in frontend/src/App.jsx, or just:
echo "" >> README.md
git add -A
git commit -m "Demo: trigger the pipeline for the capstone walkthrough"
git push origin main
```

Switch to tab 3 (Actions) and refresh.

> "That push just started the pipeline. You can see five jobs. Tests and the
> frontend build run in parallel, and both have to pass before any image gets
> built — that's a fan-in dependency, not a sequential chain.
>
> The important bit is the order inside the build job. The image is built into
> the local Docker daemon with `load: true`, Trivy scans it there, and only if
> the scan passes does it get pushed. A vulnerable image never reaches the
> registry at all. Scanning after pushing would be theatre.
>
> And the tags are commit SHAs, never `latest`. Every running pod traces back
> to the exact commit that produced it."

While it runs, open the GHCR packages page and show the SHA-tagged images.

If the pipeline is slow, say so and cut to a completed earlier run rather than
filling silence.

---

## Part 4 — Security (1.5 minutes)

Stay in the Actions run, open the Trivy step. Then slide 6.

> "The first time this gate ran, it failed both images — and that's the gate
> working, not a problem with it.
>
> The backend had three fixable HIGH CVEs, all in Starlette 0.41.3, which isn't
> even a direct dependency — FastAPI pins it. Take CVE-2026-48818: Starlette's
> StaticFiles didn't reject Windows UNC paths, so a crafted request path could
> make the server open a share on an attacker's host. Server-side request
> forgery, and on Windows a leak of NTLM credentials. Nothing in my code imports
> StaticFiles, but the vulnerable code shipped inside the image, and 'we don't
> call that function' isn't a security control. Upgrading FastAPI pulled
> Starlette 1.7.0 and all seventeen tests still passed.
>
> The frontend had forty-one findings, two of them critical, and none of them my
> code — all from the nginx Alpine base image. A pinned base tag gets rebuilt far
> less often than Alpine ships fixes, so the image was carrying months of patches
> that already existed. Moving to 1.29-alpine and running apk upgrade at build
> time took it to zero.
>
> One honest caveat: the backend still reports forty-four HIGH with no fix
> available. I exclude those with --ignore-unfixed on purpose. Failing every
> build on a CVE nobody has patched yet blocks delivery for a reason this
> repository can't do anything about. They're tracked in docs/trivy-output.txt,
> not hidden."

---

## Part 5 — Terraform and AWS (2 minutes)

```bash
cd terraform
terraform init
terraform plan
```

> "The Terraform provisions a VPC with two public and two private subnets across
> two availability zones, an internet gateway, a NAT gateway, and an EKS cluster
> with a managed node group. The subnet CIDRs are computed with cidrsubnet
> rather than hardcoded.
>
> EKS sits behind `count` on a module, so the entire cluster is one variable away
> from not existing — which is how I developed this without paying for a control
> plane I wasn't using."

Switch to tab 8, the AWS Console. Show the **VPC** page, then **EKS → Clusters**.

> "Here's the VPC in ap-south-1, and here's the EKS cluster with its node group,
> both created by that code — not clicked together in the console."

Then, on camera:

```bash
terraform destroy
```

> "And destroying it, because an EKS control plane bills ten cents an hour
> whether or not anything is running on it."

**If AWS isn't finished provisioning when you record:** say exactly that. Show
`terraform plan` succeeding and say the VPC and IAM resources were validated
against LocalStack while EKS was pending. Do not claim a console screenshot you
don't have — the grader can check, and an honest limitation costs less than a
false claim.

---

## Part 6 — Argo CD and GitOps (2 minutes)

Tab 5. The application tree, Synced and Healthy.

> "Nothing here was deployed by me running `helm upgrade`. Argo CD reads the
> Application in argocd/application.yaml, fetches the chart from this
> repository, renders it, and makes the cluster match.
>
> The sync revision at the top is the Git commit it rendered — so what's running
> traces to a commit, not to whatever was in my terminal.
>
> The image tags live in values-gitops.yaml, pinned to a full commit SHA rather
> than a moving tag. Changing the deployed version means editing that file and
> pushing. The deployment is a commit."

Now prove self-heal on camera — this is the best 30 seconds in the video:

```bash
kubectl scale deployment mltracker-mltracker-frontend -n ml-tracker --replicas=1
kubectl get deployment mltracker-mltracker-frontend -n ml-tracker -w
```

> "I've just scaled the frontend down to one replica by hand. Nothing in Git
> changed, so as far as Argo CD is concerned the cluster is now wrong..."

Wait for it to flip back to 2 (about 5–15 seconds), then Ctrl-C.

> "...and it's back to two. Drift gets corrected, not just reported. The cluster
> can't quietly diverge from what's in Git.
>
> The backend is deliberately exempt from that, because the HPA owns its replica
> count at runtime. Without an ignoreDifferences rule, Argo CD and the autoscaler
> would fight over the same field forever."

---

## Part 7 — Kubernetes (1.5 minutes)

```bash
kubectl get pods -n ml-tracker
kubectl get svc -n ml-tracker
kubectl get ingress -n ml-tracker
helm list -A
```

> "Two backend pods, two frontend pods, and PostgreSQL as a StatefulSet with a
> persistent volume claim. Services are ClusterIP — nothing is exposed directly.
> The Ingress routes slash to the frontend and slash-api to the backend, which is
> the single entry point."

Switch to tab 4 and use the app: create an experiment, move it to running, then
completed, set an accuracy, watch the stats update, delete one.

> "And that's the application, running in Kubernetes, reached through the
> Ingress."

Mention the migration, which is worth a sentence:

> "Migrations run as an initContainer, not a Helm hook. I tried a pre-install
> hook first and `helm install` timed out every time — a pre-install hook runs
> before *every* resource in the chart, including the PostgreSQL StatefulSet, so
> it had no database to connect to. As an initContainer the ordering is
> guaranteed per pod."

---

## Part 8 — Observability (2 minutes)

Generate traffic first so the panels aren't flat:

```bash
./scripts/load-test.sh
```

Tab 6, Prometheus → Status → Targets.

> "Both backend pods are UP. Prometheus finds them through a ServiceMonitor, so
> the scrape target is declared in the chart rather than configured by hand."

Show `/metrics` briefly:

```bash
kubectl exec -n ml-tracker deploy/mltracker-mltracker-backend -- curl -s localhost:8000/metrics | head -30
```

Tab 7, Grafana.

> "Eight panels: request rate, error rate, p95 latency, backend pods up, request
> rate by endpoint, responses by status class, latency percentiles, and CPU per
> pod.
>
> This dashboard is a ConfigMap in the repository, labelled
> grafana_dashboard, so it's version controlled rather than clicked together in
> the UI and lost on the next reinstall.
>
> One deliberate detail: the load generator sends 404s and 422s on purpose. A
> dashboard that only ever shows 200s proves nothing about its error-rate
> panels."

---

## Part 9 — Close (1 minute)

Slide 11, then slide 12.

> "Five things this actually taught me.
>
> Ordering guarantees are the whole game — the Helm hook failure was me assuming
> 'before install' meant 'after the database'.
>
> A security gate is only honest if it can fail, and mine did, on the first run.
>
> Transitive dependencies are where the CVEs live. Nothing in my code imports
> Starlette or libssl, and both still had to be fixed.
>
> Measure before you fix. I 'fixed' a mobile overflow twice before measuring and
> finding the page was already the right width — my screenshot tool was wrong,
> not my CSS.
>
> And not every 404 is a bug. Three failed requests turned out to be an
> ingress-nginx config reload race; twenty requests later they were all 200.
>
> That's the chain end to end: application, commit, pipeline, image, scan,
> registry, Terraform, Kubernetes, Helm, Argo CD, Ingress, autoscaling,
> monitoring. Thank you."

---

## Afterwards

```bash
# stop the EKS billing if you haven't already
cd terraform && terraform destroy

# local cluster
kind delete cluster --name mltracker
```

Save the recording as `demo/presentation.mp4`, then:

```bash
git add demo/presentation.mp4
git commit -m "Add the capstone presentation video"
git push origin main
```

If the MP4 is over 100 MB, GitHub will reject the push. Either compress it:

```bash
ffmpeg -i presentation.mp4 -vcodec libx264 -crf 30 -preset fast presentation-compressed.mp4
```

or attach it to a GitHub Release instead, which the rubric explicitly allows
("under a `demo/` folder or as a release asset").
