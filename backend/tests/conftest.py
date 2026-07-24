import os
import sys
from pathlib import Path

# isolate test artifacts + sqlite DB in the tests folder
TESTS_DIR = Path(__file__).parent
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TESTS_DIR / 'test.db'}")
os.environ.setdefault("UPLOAD_DIR", str(TESTS_DIR / "tmp_uploads"))
os.environ.setdefault("EXPORT_DIR", str(TESTS_DIR / "tmp_exports"))
os.environ.setdefault("SECRET_KEY", "test-secret")

sys.path.insert(0, str(TESTS_DIR.parent))

import pytest
from fastapi.testclient import TestClient

from app.db.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    r = client.post("/api/auth/register", json={"email": "admin@test.com", "password": "secret123"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
