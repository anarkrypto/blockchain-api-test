from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    # Create a fresh in-memory engine for each test
    # with StaticPool to maintain a single connection
    engine = create_engine(
        'sqlite:///:memory:',
        future=True,
        connect_args={
            'check_same_thread': False,
        },
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables directly from the SQLAlchemy models
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


# Inject DB session into FastAPI
@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
