"""Test fixtures.

The important thing here is that tests never touch PostgreSQL. The app's
`get_db` dependency is overridden to hand out sessions bound to a throwaway
SQLite file, so a test run cannot read, write or drop production data.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def db_engine():
    """A fresh SQLite database per test.

    StaticPool with a shared in-memory URI keeps every session on the same
    connection - without it, each session would get its own empty database and
    the tables created here would be invisible to the request under test.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # Leaving the override in place would leak into any later test module.
    app.dependency_overrides.clear()


@pytest.fixture
def sample_payload():
    return {
        "name": "resnet50-baseline",
        "model_type": "ResNet50",
        "dataset": "CIFAR-10",
        "learning_rate": 0.001,
        "epochs": 30,
        "status": "queued",
    }
