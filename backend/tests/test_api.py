import time as time_mod
from pathlib import Path

DATA = Path(__file__).parent / "data"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_auth_required(client):
    assert client.get("/api/employees").status_code == 401


def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 201
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_settings_roundtrip(auth_client):
    r = auth_client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["grace_minutes"] == 10
    r = auth_client.put("/api/settings", json={"grace_minutes": 20, "deduction_policy": "round_hour"})
    assert r.status_code == 200
    assert r.json()["grace_minutes"] == 20
    assert r.json()["deduction_policy"] == "round_hour"


def test_settings_validation(auth_client):
    r = auth_client.put("/api/settings", json={"deduction_policy": "bogus"})
    assert r.status_code == 422


def test_upload_rejects_bad_extension(auth_client):
    r = auth_client.post("/api/upload", files={"file": ("evil.exe", b"MZ...", "application/x-msdownload")})
    assert r.status_code == 400


def test_upload_rejects_empty(auth_client):
    r = auth_client.post("/api/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_full_upload_flow(auth_client):
    content = (DATA / "zkteco_biotime_sample.csv").read_bytes()
    r = auth_client.post("/api/upload", files={"file": ("timecard.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    upload_id = r.json()["id"]

    # background task runs inside TestClient synchronously after response
    for _ in range(50):
        status = auth_client.get(f"/api/uploads/{upload_id}").json()
        if status["status"] in ("completed", "failed"):
            break
        time_mod.sleep(0.1)
    assert status["status"] == "completed", status["error"]
    assert status["template"] == "zkteco_biotime"

    employees = auth_client.get("/api/employees").json()
    assert len(employees) == 1
    emp = employees[0]
    assert emp["name"] == "مراد"

    days = auth_client.get(f"/api/employees/{emp['id']}/attendance", params={"year": 2026, "month": 7}).json()
    assert len(days) == 4

    summary = auth_client.get(f"/api/employees/{emp['id']}/summary", params={"year": 2026, "month": 7}).json()
    assert summary is not None
    assert summary["absent_days"] >= 1

    dash = auth_client.get("/api/summary", params={"year": 2026, "month": 7}).json()
    assert dash["employees"] == 1

    reports = auth_client.get("/api/reports", params={"year": 2026, "month": 7}).json()
    assert len(reports) == 4

    for kind in ("csv", "excel", "pdf"):
        r = auth_client.get(f"/api/export/{kind}", params={"employee_id": emp["id"], "year": 2026, "month": 7})
        assert r.status_code == 200, f"{kind}: {r.text[:200]}"
        assert len(r.content) > 100


def test_analyze_recompute(auth_client):
    content = (DATA / "zkteco_biotime_sample.csv").read_bytes()
    auth_client.post("/api/upload", files={"file": ("timecard.csv", content, "text/csv")})
    r = auth_client.post("/api/analyze", json={"year": 2026, "month": 7})
    assert r.status_code == 200
    assert r.json()["recomputed_rows"] >= 4
