import logging

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Experiment
from app.schemas import ExperimentCreate, ExperimentOut, ExperimentUpdate, StatsOut

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title=settings.app_name,
    description="Track machine-learning training runs: configuration, status and results.",
    version="1.0.0",
)

# The browser talks to nginx, which proxies /api to this service, so same-origin
# in every deployed path. CORS is here only for `npm run dev` against a locally
# running backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exposes /metrics in Prometheus text format. Mounted before startup so the
# endpoint exists even if the database is unreachable - a pod that cannot reach
# Postgres is exactly when you most want its metrics.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/", tags=["meta"])
def root():
    return {"app": settings.app_name, "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    """Liveness: is the process up?

    Deliberately does NOT touch the database. A liveness probe that depends on
    Postgres restarts every API pod when the database blips, turning one outage
    into two.
    """
    return {"status": "healthy", "environment": settings.environment}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness: can this pod actually serve traffic?

    This one DOES check the database, because a pod that cannot reach Postgres
    should be removed from the Service endpoints rather than restarted.
    """
    try:
        db.execute(select(1))
    except SQLAlchemyError as exc:
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return {"status": "ready"}


@app.get("/api/experiments", response_model=list[ExperimentOut], tags=["experiments"])
def list_experiments(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(Experiment).order_by(Experiment.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Experiment.status == status_filter)
    return db.scalars(stmt).all()


@app.get("/api/experiments/stats", response_model=StatsOut, tags=["experiments"])
def experiment_stats(db: Session = Depends(get_db)):
    """Aggregates computed in SQL rather than by loading every row into Python.

    Declared before /api/experiments/{experiment_id} on purpose: FastAPI matches
    routes in definition order, so the other order would make "stats" parse as an
    id and return 422.
    """
    counts = dict(
        db.execute(select(Experiment.status, func.count()).group_by(Experiment.status)).all()
    )
    best, average = db.execute(
        select(func.max(Experiment.accuracy), func.avg(Experiment.accuracy))
    ).one()
    return StatsOut(
        total=sum(counts.values()),
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        best_accuracy=best,
        average_accuracy=round(average, 4) if average is not None else None,
    )


@app.get("/api/experiments/{experiment_id}", response_model=ExperimentOut, tags=["experiments"])
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@app.post(
    "/api/experiments",
    response_model=ExperimentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["experiments"],
)
def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    experiment = Experiment(**payload.model_dump())
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    logger.info("created experiment id=%s name=%s", experiment.id, experiment.name)
    return experiment


@app.put("/api/experiments/{experiment_id}", response_model=ExperimentOut, tags=["experiments"])
def update_experiment(
    experiment_id: int, payload: ExperimentUpdate, db: Session = Depends(get_db)
):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # exclude_unset so a request that sends only {"status": "completed"} does not
    # null out every other column with the schema's defaults.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(experiment, field, value)

    db.commit()
    db.refresh(experiment)
    return experiment


@app.delete(
    "/api/experiments/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["experiments"],
)
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(experiment)
    db.commit()
