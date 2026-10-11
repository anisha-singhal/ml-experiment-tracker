from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["queued", "running", "completed", "failed"]


class ExperimentBase(BaseModel):
    # pydantic v2 reserves the "model_" prefix for its own API and warns on any
    # field using it. "model_type" is the domain's word, not pydantic's, so the
    # protection is switched off rather than the field renamed.
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(min_length=1, max_length=120)
    model_type: str = Field(min_length=1, max_length=60)
    dataset: str = Field(min_length=1, max_length=120)
    learning_rate: float = Field(default=0.001, gt=0, le=1)
    epochs: int = Field(default=10, ge=1, le=10_000)
    accuracy: float | None = Field(default=None, ge=0, le=1)
    status: Status = "queued"
    notes: str | None = None


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    """Every field optional, so PUT can patch a single value.

    `exclude_unset` at the call site is what distinguishes "not supplied" from
    "explicitly set to null" - without it, omitting accuracy would wipe it.
    """

    model_config = ConfigDict(protected_namespaces=())

    name: str | None = Field(default=None, min_length=1, max_length=120)
    model_type: str | None = Field(default=None, min_length=1, max_length=60)
    dataset: str | None = Field(default=None, min_length=1, max_length=120)
    learning_rate: float | None = Field(default=None, gt=0, le=1)
    epochs: int | None = Field(default=None, ge=1, le=10_000)
    accuracy: float | None = Field(default=None, ge=0, le=1)
    status: Status | None = None
    notes: str | None = None


class ExperimentOut(ExperimentBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    created_at: datetime


class StatsOut(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    best_accuracy: float | None
    average_accuracy: float | None
