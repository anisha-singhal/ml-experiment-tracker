#!/usr/bin/env python3
"""Build the capstone presentation deck."""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.shapes import MSO_CONNECTOR

OUT = sys.argv[1]

BG      = RGBColor(0x0F, 0x17, 0x2A)
PANEL   = RGBColor(0x1E, 0x29, 0x3B)
ACCENT  = RGBColor(0x38, 0xBD, 0xF8)
ACCENT2 = RGBColor(0x4A, 0xDE, 0x80)
WARN    = RGBColor(0xFB, 0xBF, 0x24)
DANGER  = RGBColor(0xF8, 0x71, 0x71)
TEXT    = RGBColor(0xE2, 0xE8, 0xF0)
MUTED   = RGBColor(0x94, 0xA3, 0xB8)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid(); bg.fill.fore_color.rgb = BG
    bg.line.fill.background(); bg.shadow.inherit = False
    return s


def textbox(s, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def para(tf, text, size=18, color=TEXT, bold=False, first=False,
         space_before=8, space_after=0, font="Helvetica Neue", align=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    for r in p.runs:
        r.font.size = Pt(size); r.font.color.rgb = color
        r.font.bold = bold; r.font.name = font
    return p


def heading(s, title, kicker=None):
    if kicker:
        tf = textbox(s, Inches(0.8), Inches(0.42), Inches(11.7), Inches(0.35))
        para(tf, kicker.upper(), size=12, color=ACCENT, bold=True, first=True, space_before=0)
    tf = textbox(s, Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.8))
    para(tf, title, size=34, color=WHITE, bold=True, first=True, space_before=0)
    ln = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.52), Inches(1.1), Pt(3))
    ln.fill.solid(); ln.fill.fore_color.rgb = ACCENT
    ln.line.fill.background(); ln.shadow.inherit = False


def box(s, x, y, w, h, text, fill=PANEL, border=None, size=14, color=TEXT,
        bold=False, font="Helvetica Neue", radius=True):
    shape = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    if border:
        shape.line.color.rgb = border; shape.line.width = Pt(1.25)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    if radius:
        try:
            shape.adjustments[0] = 0.12
        except (IndexError, KeyError):
            pass
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = PP_ALIGN.CENTER
        p.space_before = Pt(0); p.space_after = Pt(0)
        for r in p.runs:
            r.font.size = Pt(size if i == 0 else size - 2)
            r.font.color.rgb = color if i == 0 else MUTED
            r.font.bold = bold if i == 0 else False
            r.font.name = font
    return shape


def card(s, x, y, w, h, title, body, border=None, fill=PANEL,
         title_size=16, body_size=13, title_color=WHITE, gap=7):
    """One shape holding a bold title and muted body lines in a single text frame."""
    shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    if border:
        shape.line.color.rgb = border; shape.line.width = Pt(1.25)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    try:
        shape.adjustments[0] = 0.08
    except (IndexError, KeyError):
        pass
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.17)
    tf.margin_top = Inches(0.13); tf.margin_bottom = Inches(0.1)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.text = title; p.alignment = PP_ALIGN.LEFT
    p.space_before = Pt(0); p.space_after = Pt(0)
    for r in p.runs:
        r.font.size = Pt(title_size); r.font.bold = True
        r.font.color.rgb = title_color; r.font.name = "Helvetica Neue"
    lines = body if isinstance(body, (list, tuple)) else [body]
    for i, line in enumerate(lines):
        bp = tf.add_paragraph()
        bp.text = line; bp.alignment = PP_ALIGN.LEFT
        bp.space_before = Pt(gap if i == 0 else 5); bp.space_after = Pt(0)
        for r in bp.runs:
            r.font.size = Pt(body_size); r.font.color.rgb = MUTED
            r.font.name = "Helvetica Neue"
    return shape


def codeblock(s, x, y, w, h, lines, size=14, color=ACCENT2, fill=PANEL):
    """Left-aligned monospace block, every line styled identically."""
    shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.fill.background(); shape.shadow.inherit = False
    try:
        shape.adjustments[0] = 0.08
    except (IndexError, KeyError):
        pass
    tf = shape.text_frame
    tf.word_wrap = False
    tf.margin_left = Inches(0.25); tf.margin_right = Inches(0.1)
    tf.margin_top = Inches(0.1); tf.margin_bottom = Inches(0.1)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(lines if isinstance(lines, (list, tuple)) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.alignment = PP_ALIGN.LEFT
        p.space_before = Pt(0 if i == 0 else 4); p.space_after = Pt(0)
        for r in p.runs:
            r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = "Menlo"
    return shape


def arrow(s, x1, y1, x2, y2, color=ACCENT):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color; c.line.width = Pt(1.75)
    return c


def footer(s, n):
    tf = textbox(s, Inches(11.6), Inches(6.85), Inches(1.0), Inches(0.3),
                 align=PP_ALIGN.RIGHT)
    para(tf, str(n), size=11, color=MUTED, first=True, space_before=0)
    tf = textbox(s, Inches(0.8), Inches(6.85), Inches(6.0), Inches(0.3))
    para(tf, "ML Experiment Tracker · Anisha Singhal · 10020",
         size=11, color=MUTED, first=True, space_before=0)


def bullets(s, items, x=Inches(0.8), y=Inches(1.95), w=Inches(11.7), size=17, gap=14):
    tf = textbox(s, x, y, w, Inches(4.5))
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            label, body = item
            p = para(tf, "", size=size, first=(i == 0), space_before=0 if i == 0 else gap)
            r1 = p.add_run(); r1.text = label + "  "
            r1.font.size = Pt(size); r1.font.bold = True
            r1.font.color.rgb = ACCENT; r1.font.name = "Helvetica Neue"
            r2 = p.add_run(); r2.text = body
            r2.font.size = Pt(size); r2.font.color.rgb = TEXT
            r2.font.name = "Helvetica Neue"
        else:
            para(tf, "•  " + item, size=size, first=(i == 0),
                 space_before=0 if i == 0 else gap)
    return tf


# ───────────────────────────── 1. Title ─────────────────────────────
s = slide()
accentbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.22), H)
accentbar.fill.solid(); accentbar.fill.fore_color.rgb = ACCENT
accentbar.line.fill.background(); accentbar.shadow.inherit = False

tf = textbox(s, Inches(1.1), Inches(2.1), Inches(11.0), Inches(0.4))
para(tf, "DEVOPS FINAL CAPSTONE PROJECT · SESSION 21", size=14,
     color=ACCENT, bold=True, first=True, space_before=0)

tf = textbox(s, Inches(1.05), Inches(2.6), Inches(11.2), Inches(1.5))
para(tf, "ML Experiment Tracker", size=60, color=WHITE, bold=True,
     first=True, space_before=0)

tf = textbox(s, Inches(1.1), Inches(3.95), Inches(10.5), Inches(0.9))
para(tf, "From a laptop to a monitored Kubernetes cluster — application, pipeline,\n"
         "security gate, infrastructure as code and live dashboards.",
     size=19, color=MUTED, first=True, space_before=0)

tf = textbox(s, Inches(1.1), Inches(5.35), Inches(10.5), Inches(0.8))
para(tf, "Anisha Singhal", size=22, color=TEXT, bold=True, first=True, space_before=0)
para(tf, "Enrollment 10020  ·  github.com/anisha-singhal/ml-experiment-tracker",
     size=15, color=MUTED, space_before=4)

# ───────────────────────── 2. Project overview ──────────────────────
s = slide(); heading(s, "What the application does", "Project overview")
bullets(s, [
    "Anyone who has run more than a handful of ML experiments has lost track of which "
    "configuration produced the good number.",
    "Each training run is one record: name, model type, dataset, learning rate, epochs, "
    "status and accuracy.",
    "Runs move through queued → running → completed. Filter by status; see totals, "
    "per-status counts, best and average accuracy.",
], y=Inches(1.95), size=17)

tf = textbox(s, Inches(0.8), Inches(3.95), Inches(11.7), Inches(0.4))
para(tf, "ONE DESIGN DECISION WORTH CALLING OUT", size=12, color=ACCENT,
     bold=True, first=True, space_before=0)

card(s, Inches(0.8), Inches(4.35), Inches(11.7), Inches(0.95),
     "Accuracy is nullable, not zero.",
     ["A queued run has no score yet — which is a different thing from having scored 0.0. "
      "That distinction is enforced in the schema, the API and the UI."],
     border=ACCENT, title_size=16, body_size=14)

for i, (num, label) in enumerate([("9", "REST endpoints"), ("17", "passing tests"),
                                  ("2×2", "replicas in K8s"), ("8", "Grafana panels")]):
    x = Inches(0.8 + i * 2.95)
    b = box(s, x, Inches(5.55), Inches(2.7), Inches(0.95), "", fill=PANEL)
    tfb = b.text_frame
    pp = tfb.paragraphs[0]; pp.text = num; pp.alignment = PP_ALIGN.CENTER
    for r in pp.runs:
        r.font.size = Pt(26); r.font.bold = True
        r.font.color.rgb = ACCENT2; r.font.name = "Helvetica Neue"
    p2 = tfb.add_paragraph(); p2.text = label; p2.alignment = PP_ALIGN.CENTER
    for r in p2.runs:
        r.font.size = Pt(12); r.font.color.rgb = MUTED; r.font.name = "Helvetica Neue"
footer(s, 2)

# ─────────────────────────── 3. Tech stack ──────────────────────────
s = slide(); heading(s, "Technology stack", "Tech stack")
rows = [
    ("Frontend", "React 18 · Vite 5 · plain CSS, responsive to 430px"),
    ("Backend", "FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic"),
    ("Database", "PostgreSQL 16 — StatefulSet + PVC in the cluster"),
    ("Tests", "pytest — 17 tests, SQLite-isolated via dependency override"),
    ("Containers", "Docker · multi-stage builds · non-root runtimes"),
    ("CI/CD", "GitHub Actions · GitHub Container Registry, SHA-tagged"),
    ("Security", "Trivy image scanning with a build-failing gate"),
    ("Orchestration", "Kubernetes · Helm 3 · ingress-nginx · HPA"),
    ("GitOps", "Argo CD — declarative sync from this repository"),
    ("Infrastructure", "Terraform — AWS VPC across 2 AZs + EKS node group"),
    ("Observability", "Prometheus · Grafana · prometheus-fastapi-instrumentator"),
]
y0 = 1.92
for i, (layer, used) in enumerate(rows):
    y = Inches(y0 + i * 0.44)
    if i % 2 == 0:
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), y, Inches(11.7), Inches(0.40))
        r.fill.solid(); r.fill.fore_color.rgb = PANEL
        r.line.fill.background(); r.shadow.inherit = False
    tf = textbox(s, Inches(0.95), y + Emu(20000), Inches(2.6), Inches(0.36))
    para(tf, layer, size=14, color=ACCENT, bold=True, first=True, space_before=0)
    tf = textbox(s, Inches(3.5), y + Emu(20000), Inches(8.9), Inches(0.36))
    para(tf, used, size=14, color=TEXT, first=True, space_before=0)
footer(s, 3)

# ────────────────────────── 4. Architecture ─────────────────────────
s = slide(); heading(s, "Architecture", "How it fits together")

box(s, Inches(0.8), Inches(2.1), Inches(1.85), Inches(0.7), "Developer\ngit push",
    border=MUTED, size=13)
box(s, Inches(0.8), Inches(3.25), Inches(1.85), Inches(0.7), "GitHub\nsource of truth",
    border=MUTED, size=13)
arrow(s, Inches(1.72), Inches(2.8), Inches(1.72), Inches(3.25))

card(s, Inches(3.15), Inches(1.95), Inches(2.75), Inches(2.45), "GitHub Actions",
     ["→ pytest — 17 tests", "→ frontend build", "→ docker build (matrix)",
      "→ trivy scan", "→ security gate", "→ push to GHCR", "→ helm lint"],
     border=ACCENT, title_size=15, body_size=12)
arrow(s, Inches(2.65), Inches(3.1), Inches(3.15), Inches(3.1))

box(s, Inches(6.4), Inches(1.95), Inches(2.3), Inches(0.75),
    "GHCR\nimages tagged :sha", border=ACCENT2, size=14, bold=True)
arrow(s, Inches(5.9), Inches(2.32), Inches(6.4), Inches(2.32))

box(s, Inches(6.4), Inches(3.15), Inches(2.3), Inches(0.75),
    "Argo CD\nwatches the repo", border=WARN, size=14, bold=True)
arrow(s, Inches(2.65), Inches(3.6), Inches(6.4), Inches(3.6), color=WARN)

card(s, Inches(9.2), Inches(1.95), Inches(3.3), Inches(2.45), "Kubernetes",
     ["Ingress  /  → frontend", "Ingress  /api → backend", "frontend × 2  (nginx)",
      "backend × 2  (FastAPI)", "PostgreSQL StatefulSet + PVC", "HPA on backend CPU"],
     border=ACCENT, title_size=15, body_size=12)
arrow(s, Inches(8.7), Inches(3.1), Inches(9.2), Inches(3.1))

box(s, Inches(0.8), Inches(4.85), Inches(3.4), Inches(1.0),
    "Terraform\nAWS VPC · 2 AZs · EKS node group", border=ACCENT2, size=14, bold=True)
arrow(s, Inches(4.2), Inches(5.35), Inches(9.2), Inches(4.4), color=ACCENT2)

box(s, Inches(5.1), Inches(4.85), Inches(3.4), Inches(1.0),
    "Prometheus → Grafana\nscrapes /metrics on both pods", border=WARN, size=14, bold=True)
arrow(s, Inches(9.2), Inches(4.4), Inches(8.5), Inches(5.1), color=WARN)
footer(s, 4)

# ───────────────────────────── 5. CI/CD ─────────────────────────────
s = slide(); heading(s, "The pipeline", "CI/CD flow")

stages = [("1  test", "pytest ×17"), ("2  build", "frontend"),
          ("3  image", "docker matrix"), ("4  scan", "trivy"),
          ("5  gate", "HIGH/CRITICAL"), ("6  push", "GHCR :sha")]
for i, (t, sub) in enumerate(stages):
    x = Inches(0.8 + i * 1.98)
    col = DANGER if i == 4 else (ACCENT2 if i == 5 else ACCENT)
    box(s, x, Inches(2.0), Inches(1.78), Inches(0.95), t + "\n" + sub,
        border=col, size=14, bold=True)
    if i < len(stages) - 1:
        arrow(s, x + Inches(1.78), Inches(2.47), x + Inches(1.98), Inches(2.47))

tf = textbox(s, Inches(0.8), Inches(3.3), Inches(11.7), Inches(0.4))
para(tf, "THE TWO DECISIONS THAT MATTER", size=12, color=ACCENT, bold=True,
     first=True, space_before=0)

card(s, Inches(0.8), Inches(3.7), Inches(5.7), Inches(1.55),
     "Scan before push, not after",
     ["The image is built with load: true into the local Docker daemon, scanned, and only "
      "pushed if the gate passes. A vulnerable image never reaches the registry at all."],
     border=DANGER, title_size=16, body_size=13)

card(s, Inches(6.8), Inches(3.7), Inches(5.7), Inches(1.55),
     "Tagged with the commit SHA",
     ["Never :latest. Every running pod can be traced back to the exact commit that "
      "produced it, and a rollback is a tag change rather than a rebuild."],
     border=ACCENT2, title_size=16, body_size=13)

box(s, Inches(0.8), Inches(5.5), Inches(11.7), Inches(0.85),
    "pytest and the frontend build run in parallel and both must pass before any image "
    "is built — a fan-in dependency, not a sequential chain.", size=15, fill=PANEL)
footer(s, 5)

# ──────────────────────────── 6. DevSecOps ──────────────────────────
s = slide(); heading(s, "What the security gate caught", "DevSecOps · Trivy")

codeblock(s, Inches(0.8), Inches(1.95), Inches(11.7), Inches(0.6),
          ["trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1  <image>"],
          size=15)

card(s, Inches(0.8), Inches(2.75), Inches(5.7), Inches(1.75),
     "Backend — 3 fixable HIGH",
     ["All three in starlette 0.41.3, which fastapi pins — not a direct dependency.",
      "CVE-2026-48818: StaticFiles did not reject Windows UNC paths, so a crafted request "
      "could make the server fetch \\\\attacker\\share — SSRF, and an NTLM credential leak "
      "on Windows."],
     border=DANGER, title_size=16, body_size=12)

card(s, Inches(6.8), Inches(2.75), Inches(5.7), Inches(1.75),
     "Frontend — 41 fixable, 2 CRITICAL",
     ["None of it this project's code — all from nginx-unprivileged:1.27-alpine.",
      "A pinned base tag is rebuilt far less often than Alpine ships fixes, so the image "
      "carried months of already-released patches."],
     border=DANGER, title_size=16, body_size=12)

codeblock(s, Inches(0.8), Inches(4.7), Inches(11.7), Inches(0.95),
          ["BEFORE   backend 3 fixable HIGH    ·    frontend 41 fixable (2 CRITICAL, 39 HIGH)",
           "AFTER    backend 0                 ·    frontend 0"],
          size=14)

tf = textbox(s, Inches(0.8), Inches(5.85), Inches(11.7), Inches(1.0))
para(tf, "The honest caveat", size=15, color=ACCENT, bold=True, first=True, space_before=0)
para(tf, "The backend still reports 44 HIGH with no fix available. --ignore-unfixed "
         "excludes those deliberately: failing every build on a CVE nobody has patched "
         "yet blocks delivery for a reason this repository cannot act on. They are "
         "tracked in docs/trivy-output.txt, not hidden.",
     size=12, color=MUTED, space_before=5)
footer(s, 6)

# ────────────────────────── 7. Infrastructure ───────────────────────
s = slide(); heading(s, "Infrastructure as code", "Terraform · AWS")

card(s, Inches(0.8), Inches(1.95), Inches(5.7), Inches(2.6),
     "What the code provisions",
     ["·  VPC with CIDR carved by cidrsubnet()",
      "·  2 public + 2 private subnets across 2 AZs",
      "·  Internet Gateway, NAT gateway, route tables",
      "·  EKS cluster + managed node group",
      "·  IRSA / OIDC provider for pod-level IAM",
      "·  kubernetes.io/role/elb subnet tags, so the load balancer "
      "controller can find them"],
     border=ACCENT, title_size=16, body_size=13)

card(s, Inches(6.8), Inches(1.95), Inches(5.7), Inches(2.6),
     "How it is structured",
     ["·  EKS sits behind count on a module — the whole cluster is one variable "
      "away from absent",
      "·  Provider endpoints come from a dynamic block, so the same code targets "
      "LocalStack or real AWS",
      "·  terraform.tfvars.example is committed; no real credentials anywhere in history",
      "·  destroy is part of the workflow, not an afterthought"],
     border=ACCENT, title_size=16, body_size=13)

card(s, Inches(0.8), Inches(4.75), Inches(11.7), Inches(1.4),
     "Cost discipline",
     ["An EKS control plane bills $0.10/hour whether or not anything runs on it. The cluster "
      "is created for the evaluation and destroyed immediately afterwards, and the Terraform "
      "is written so that enable_eks = false leaves a VPC that costs nothing — which is how "
      "it was developed and tested against LocalStack before a single real resource existed."],
     border=WARN, title_size=16, body_size=13)
footer(s, 7)

# ───────────────────────── 8. Kubernetes + Helm ─────────────────────
s = slide(); heading(s, "Running in the cluster", "Kubernetes · Helm")

box(s, Inches(0.8), Inches(1.95), Inches(2.6), Inches(0.8),
    "Ingress (nginx)\n/ → frontend   /api → backend", border=ACCENT, size=13, bold=True)
box(s, Inches(3.75), Inches(1.95), Inches(2.6), Inches(0.8),
    "frontend × 2\nClusterIP :8080", border=MUTED, size=13, bold=True)
box(s, Inches(6.7), Inches(1.95), Inches(2.6), Inches(0.8),
    "backend × 2\nClusterIP :8000 + HPA", border=MUTED, size=13, bold=True)
box(s, Inches(9.65), Inches(1.95), Inches(2.85), Inches(0.8),
    "PostgreSQL\nStatefulSet + PVC", border=MUTED, size=13, bold=True)
arrow(s, Inches(3.4), Inches(2.35), Inches(3.75), Inches(2.35))
arrow(s, Inches(6.35), Inches(2.35), Inches(6.7), Inches(2.35))
arrow(s, Inches(9.3), Inches(2.35), Inches(9.65), Inches(2.35))

tf = textbox(s, Inches(0.8), Inches(3.05), Inches(11.7), Inches(0.4))
para(tf, "THE CHART DECISION THAT TOOK TWO ATTEMPTS", size=12, color=ACCENT,
     bold=True, first=True, space_before=0)

card(s, Inches(0.8), Inches(3.45), Inches(5.7), Inches(1.85),
     "Attempt 1 — Helm pre-install hook",
     ["The Alembic migration ran as a pre-install hook. helm install timed out every "
      "single time.",
      "A pre-install hook runs before every chart resource — including the PostgreSQL "
      "StatefulSet. It had no database to connect to."],
     border=DANGER, title_size=15, body_size=13)

card(s, Inches(6.8), Inches(3.45), Inches(5.7), Inches(1.85),
     "Attempt 2 — initContainers",
     ["Two initContainers on the backend Deployment: wait-for-postgres, then migrate.",
      "Ordering inside a pod is guaranteed, and the app container cannot start against an "
      "unmigrated schema."],
     border=ACCENT2, title_size=15, body_size=13)

box(s, Inches(0.8), Inches(5.55), Inches(11.7), Inches(0.78),
    "/health deliberately does not touch the database — a liveness probe that fails on a "
    "database blip restarts a perfectly healthy pod. /ready does check it.",
    fill=PANEL, size=14)
footer(s, 8)

# ──────────────────────────── 9. GitOps ─────────────────────────────
s = slide(); heading(s, "GitOps with Argo CD", "Declarative delivery")

box(s, Inches(0.8), Inches(2.0), Inches(2.5), Inches(0.85),
    "Git repository\nhelm/mltracker", border=ACCENT, size=13, bold=True)
box(s, Inches(3.75), Inches(2.0), Inches(2.5), Inches(0.85),
    "Argo CD\nreconciliation loop", border=WARN, size=13, bold=True)
box(s, Inches(6.7), Inches(2.0), Inches(2.5), Inches(0.85),
    "Live cluster state\nSynced · Healthy", border=ACCENT2, size=13, bold=True)
box(s, Inches(9.65), Inches(2.0), Inches(2.85), Inches(0.85),
    "Drift\nreverted automatically", border=MUTED, size=13, bold=True)
arrow(s, Inches(3.3), Inches(2.42), Inches(3.75), Inches(2.42))
arrow(s, Inches(6.25), Inches(2.42), Inches(6.7), Inches(2.42))
arrow(s, Inches(9.2), Inches(2.42), Inches(9.65), Inches(2.42))

bullets(s, [
    ("Declared, not run.", "An Argo CD Application points at helm/mltracker in this "
     "repository. Nobody runs helm upgrade by hand; the desired state is a file."),
    ("The deployed version is a committed value.", "CI publishes images tagged with the "
     "commit SHA; which tag runs is a field in values-gitops.yaml. Changing the deployed "
     "version is therefore a commit, and Argo CD converges the cluster onto it."),
    ("Drift is corrected, not just detected.", "Delete a pod or hand-edit a replica count "
     "and the reconciliation loop puts it back — the cluster cannot quietly diverge from "
     "what is in Git."),
    ("Rollback is git revert.", "Because the whole desired state is version controlled, "
     "undoing a bad deploy is undoing a commit."),
], y=Inches(3.2), size=15, gap=13)
footer(s, 9)

# ───────────────────────── 10. Observability ────────────────────────
s = slide(); heading(s, "Observability", "Prometheus · Grafana")

box(s, Inches(0.8), Inches(1.95), Inches(2.45), Inches(0.8),
    "FastAPI /metrics\ninstrumentator", border=ACCENT, size=13, bold=True)
box(s, Inches(3.6), Inches(1.95), Inches(2.45), Inches(0.8),
    "ServiceMonitor\nscrape target, declared", border=MUTED, size=13, bold=True)
box(s, Inches(6.4), Inches(1.95), Inches(2.45), Inches(0.8),
    "Prometheus\nboth pods UP", border=WARN, size=13, bold=True)
box(s, Inches(9.2), Inches(1.95), Inches(3.3), Inches(0.8),
    "Grafana\n8 panels, from a ConfigMap", border=ACCENT2, size=13, bold=True)
arrow(s, Inches(3.25), Inches(2.35), Inches(3.6), Inches(2.35))
arrow(s, Inches(6.05), Inches(2.35), Inches(6.4), Inches(2.35))
arrow(s, Inches(8.85), Inches(2.35), Inches(9.2), Inches(2.35))

card(s, Inches(0.8), Inches(3.15), Inches(5.7), Inches(2.95),
     "The eight panels",
     ["·  request rate", "·  error rate", "·  p95 latency", "·  backend pods up",
      "·  request rate by endpoint", "·  responses by status class",
      "·  latency percentiles — p50 / p95 / p99", "·  CPU per pod"],
     border=ACCENT, title_size=16, body_size=13)

card(s, Inches(6.8), Inches(3.15), Inches(5.7), Inches(1.3),
     "The dashboard is a ConfigMap",
     ["Labelled grafana_dashboard: \"1\" and version-controlled — not clicked together in "
      "the UI and lost on the next reinstall."],
     border=ACCENT2, title_size=15, body_size=13)

card(s, Inches(6.8), Inches(4.7), Inches(5.7), Inches(1.4),
     "The load generator fails on purpose",
     ["scripts/load-test.sh mixes 404s and 422s into its traffic. A dashboard that only ever "
      "shows 200s proves nothing about its error-rate panels."],
     border=WARN, title_size=15, body_size=13)
footer(s, 10)

# ─────────────────────────── 11. Learnings ──────────────────────────
s = slide(); heading(s, "What this actually taught me", "Key learnings")
bullets(s, [
    ("Ordering guarantees are the whole game.", "The pre-install hook failure was not a Helm "
     "bug — it was me assuming \"before install\" meant \"after the database\". Hooks order "
     "against the release; initContainers order against the pod."),
    ("A security gate is only honest if it can fail.", "The first Trivy run broke both images "
     "and the build. That was the gate working. Scanning after the push would have been "
     "theatre."),
    ("Transitive dependencies are where the CVEs live.", "Nothing in this repository imports "
     "starlette or libssl. Both still shipped inside the images, and both still had to be "
     "fixed."),
    ("Measure before you fix.", "I \"fixed\" a mobile overflow twice before measuring and "
     "finding scrollWidth already equalled the viewport — my screenshot tool was wrong, "
     "not the CSS."),
    ("Not every 404 is a bug.", "Three failed POSTs turned out to be an ingress-nginx config "
     "reload race. Twenty requests later, all 200. Recognising transience saves hours."),
], y=Inches(1.9), size=15, gap=13)
footer(s, 11)

# ──────────────────────────── 12. Closing ───────────────────────────
s = slide()
accentbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.22), H)
accentbar.fill.solid(); accentbar.fill.fore_color.rgb = ACCENT
accentbar.line.fill.background(); accentbar.shadow.inherit = False

tf = textbox(s, Inches(1.1), Inches(2.3), Inches(11.0), Inches(0.4))
para(tf, "THE OBJECTIVE OF SESSION 21", size=14, color=ACCENT, bold=True,
     first=True, space_before=0)
tf = textbox(s, Inches(1.05), Inches(2.75), Inches(11.2), Inches(1.0))
para(tf, "One chain, end to end", size=44, color=WHITE, bold=True, first=True,
     space_before=0)

tf = textbox(s, Inches(1.1), Inches(3.95), Inches(11.0), Inches(1.2))
para(tf, "application  →  commit  →  pipeline  →  image  →  scan  →  registry\n"
         "→  Terraform  →  Kubernetes  →  Helm  →  Argo CD  →  Ingress\n"
         "→  autoscaling  →  monitoring  →  troubleshooting",
     size=18, color=ACCENT2, first=True, space_before=0, font="Menlo")

tf = textbox(s, Inches(1.1), Inches(5.6), Inches(11.0), Inches(0.9))
para(tf, "Anisha Singhal  ·  10020", size=20, color=TEXT, bold=True, first=True,
     space_before=0)
para(tf, "github.com/anisha-singhal/ml-experiment-tracker", size=15, color=MUTED,
     space_before=4)

prs.save(OUT)
print(f"wrote {OUT} — {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
