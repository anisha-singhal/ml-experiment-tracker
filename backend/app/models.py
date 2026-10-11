from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Experiment(Base):
    """One training run.

    Accuracy is nullable on purpose: a run is created when it is queued, long
    before it has a result, so "no accuracy yet" and "scored 0.0" have to be
    distinguishable.
    """

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(60), nullable=False)
    dataset: Mapped[str] = mapped_column(String(120), nullable=False)
    learning_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.001)
    epochs: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
