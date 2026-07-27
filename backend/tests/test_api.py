import time as time_mod
from datetime import date, time
from pathlib import Path

DATA = Path(__file__).parent / "data"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_settings_roundtrip(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["grace_minutes"] == 10
    r = client.put("/api/settings", json={"grace_minutes": 20, "deduction_policy": "round_hour"})
    assert r.status_code == 200
    assert r.json()["grace_minutes"] == 20
    assert r.json()["deduction_policy"] == "round_hour"


def test_settings_validation(client):
    r = client.put("/api/settings", json={"deduction_policy": "bogus"})
    assert r.status_code == 422


def test_upload_rejects_bad_extension(client):
    r = client.post("/api/upload", files={"file": ("evil.exe", b"MZ...", "application/x-msdownload")})
    assert r.status_code == 400


def test_upload_rejects_empty(client):
    r = client.post("/api/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_full_upload_flow(client):
    content = (DATA / "zkteco_biotime_sample.csv").read_bytes()
    r = client.post("/api/upload", files={"file": ("timecard.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    upload_id = r.json()["id"]

    # background task runs inside TestClient synchronously after response
    for _ in range(50):
        status = client.get(f"/api/uploads/{upload_id}").json()
        if status["status"] in ("completed", "failed"):
            break
        time_mod.sleep(0.1)
    assert status["status"] == "completed", status["error"]
    assert status["template"] == "zkteco_biotime"

    employees = client.get("/api/employees").json()
    assert len(employees) == 1
    emp = employees[0]
    assert emp["name"] == "مراد"

    days = client.get(f"/api/employees/{emp['id']}/attendance", params={"year": 2026, "month": 7}).json()
    assert len(days) == 4

    summary = client.get(f"/api/employees/{emp['id']}/summary", params={"year": 2026, "month": 7}).json()
    assert summary is not None
    assert summary["absent_days"] >= 1

    dash = client.get("/api/summary", params={"year": 2026, "month": 7}).json()
    assert dash["employees"] == 1

    reports = client.get("/api/reports", params={"year": 2026, "month": 7}).json()
    assert len(reports) == 4

    for kind in ("csv", "excel", "pdf"):
        r = client.get(f"/api/export/{kind}", params={"employee_id": emp["id"], "year": 2026, "month": 7})
        assert r.status_code == 200, f"{kind}: {r.text[:200]}"
        assert len(r.content) > 100


def test_report_day_filters(client):
    from app.db.database import SessionLocal
    from app.models import Attendance, Employee

    db = SessionLocal()
    emp = Employee(code="9001", name="موظف تجريبي")
    db.add(emp)
    db.flush()
    db.add_all([
        Attendance(employee_id=emp.id, date=date(2026, 7, 1), status="absent"),
        Attendance(employee_id=emp.id, date=date(2026, 7, 2), status="incomplete", check_in=time(8, 0)),
        Attendance(employee_id=emp.id, date=date(2026, 7, 3), status="present", late_minutes=25),
        Attendance(employee_id=emp.id, date=date(2026, 7, 4), status="present", early_leave_minutes=40),
        Attendance(employee_id=emp.id, date=date(2026, 7, 5), status="present", overtime_minutes=90),
        Attendance(employee_id=emp.id, date=date(2026, 7, 6), status="present"),
    ])
    db.commit()
    db.close()

    def dates(**params):
        r = client.get("/api/reports", params={"year": 2026, "month": 7, **params})
        assert r.status_code == 200, r.text
        return sorted(row["date"] for row in r.json())

    assert len(dates()) == 6
    assert dates(flags="absent") == ["2026-07-01"]
    assert dates(flags="single_punch") == ["2026-07-02"]
    assert dates(flags="late") == ["2026-07-03"]
    assert dates(flags="early_leave") == ["2026-07-04"]
    assert dates(flags="overtime") == ["2026-07-05"]
    # several flags are OR-combined, and still stack with the other filters
    assert dates(flags=["late", "overtime"]) == ["2026-07-03", "2026-07-05"]
    assert dates(flags=["absent", "late"], status="absent") == ["2026-07-01"]
    assert dates(flags=["late"], q="9001") == ["2026-07-03"]


def test_rows_expose_the_shift_window_they_were_judged_against(client):
    from app.db.database import SessionLocal
    from app.models import Attendance, Employee

    db = SessionLocal()
    emp = Employee(code="9002", name="ورديتان")
    db.add(emp)
    db.flush()
    db.add_all([
        # own schedule from the file
        Attendance(employee_id=emp.id, date=date(2026, 7, 1), status="present",
                   scheduled_in=time(10, 0), scheduled_out=time(19, 0),
                   check_in=time(10, 0), check_out=time(19, 0)),
        # unusable placeholder -> falls back to the configured work day
        Attendance(employee_id=emp.id, date=date(2026, 7, 2), status="present",
                   scheduled_in=time(6, 0), scheduled_out=time(6, 0),
                   check_in=time(8, 0), check_out=time(17, 0)),
    ])
    db.commit()
    emp_id = emp.id
    db.close()

    settings = client.get("/api/settings").json()
    rows = {r["date"]: r for r in client.get("/api/reports", params={"year": 2026, "month": 7}).json()}
    assert (rows["2026-07-01"]["work_start"], rows["2026-07-01"]["work_end"]) == ("10:00", "19:00")
    assert rows["2026-07-02"]["work_start"] == settings["work_start"][:5]
    assert rows["2026-07-02"]["work_end"] == settings["work_end"][:5]

    days = {d["date"]: d for d in
            client.get(f"/api/employees/{emp_id}/attendance", params={"year": 2026, "month": 7}).json()}
    assert days["2026-07-01"]["work_start"] == "10:00:00"
    assert days["2026-07-01"]["work_end"] == "19:00:00"
    assert days["2026-07-02"]["work_start"] == settings["work_start"]


def test_report_rejects_unknown_filter(client):
    r = client.get("/api/reports", params={"flags": "bogus"})
    assert r.status_code == 400
    assert "bogus" in r.json()["detail"]


def test_analyze_recompute(client):
    content = (DATA / "zkteco_biotime_sample.csv").read_bytes()
    client.post("/api/upload", files={"file": ("timecard.csv", content, "text/csv")})
    r = client.post("/api/analyze", json={"year": 2026, "month": 7})
    assert r.status_code == 200
    assert r.json()["recomputed_rows"] >= 4
