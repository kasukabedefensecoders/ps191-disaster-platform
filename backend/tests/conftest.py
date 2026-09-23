import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
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


# Connects as the migration/owner role (bypasses RLS) so tests can clean up
# rows they created through the API — app_user has DELETE only on the four
# tables migration 0006 scoped it to (relocation_records, surveys,
# handoff_logs, incident_outcomes; Backend Schema §7), and none at all on
# everything else (zones, households, audit_log, ...), so cleanup generally
# can't go through the app's own session. Only ever used for test teardown,
# never application logic.
_AdminSession = sessionmaker(bind=create_engine(settings.migration_database_url))


@pytest.fixture
def admin_db():
    session = _AdminSession()
    try:
        yield session
    finally:
        session.close()


def delete_zone(admin_db, zone_id) -> None:
    admin_db.execute(text("delete from zones where zone_id = :zone_id"), {"zone_id": str(zone_id)})
    admin_db.commit()


def login(client: TestClient, email: str) -> dict:
    response = client.post("/auth/login", data={"username": email, "password": SEED_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()
