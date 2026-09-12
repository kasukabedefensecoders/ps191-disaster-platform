import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.seed import SEED_PASSWORD


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def login(client: TestClient, email: str) -> dict:
    response = client.post("/auth/login", data={"username": email, "password": SEED_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()
