"""Seed the database with demo employees and one month of attendance.

Run:  python -m app.db.seed
"""
import random
from datetime import date, time, timedelta

from sqlalchemy import select

from app.db.database import Base, SessionLocal, engine
from app.models import Attendance, Employee, WorkSettings
from app.services.calculator import compute_day, rebuild_summaries

DEMO_EMPLOYEES = [
    ("1001", "مراد حسن", "Sales", "Manager"),
    ("1002", "أحمد علي", "Sales", "Sales Rep"),
    ("1003", "سارة محمود", "HR", "HR Specialist"),
    ("1004", "خالد يوسف", "IT", "Developer"),
    ("1005", "ليلى عمر", "Finance", "Accountant"),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ws = db.scalar(select(WorkSettings))
        if ws is None:
            ws = WorkSettings(hourly_rate=10.0, overtime_hourly_rate=15.0, company_name="Demo Company")
            db.add(ws)
        db.flush()

        rng = random.Random(42)
        today = date.today()
        month_start = today.replace(day=1)

        for code, name, dept, pos in DEMO_EMPLOYEES:
            emp = db.scalar(select(Employee).where(Employee.code == code))
            if emp is None:
                emp = Employee(code=code, name=name, department=dept, position=pos)
                db.add(emp)
                db.flush()

            day = month_start
            while day < today:
                exists = db.scalar(select(Attendance).where(
                    Attendance.employee_id == emp.id, Attendance.date == day))
                if exists is None:
                    weekday = day.strftime("%A")
                    att = Attendance(employee_id=emp.id, date=day, weekday=weekday)
                    if weekday not in (ws.weekend_days or []):
                        roll = rng.random()
                        if roll < 0.05:
                            att.file_absence = True  # absent day
                        elif roll < 0.10:
                            att.file_leave = True  # leave day
                        else:
                            late = rng.choice([0, 0, 0, 5, 12, 25, 40])
                            extra = rng.choice([0, 0, 0, 30, 60, 90])
                            att.check_in = time(8, late % 60) if late < 60 else time(9, late - 60)
                            out = time(17 + extra // 60, extra % 60)
                            att.check_out = out
                    compute_day(att, ws)
                    db.add(att)
                day += timedelta(days=1)

        db.flush()
        rebuild_summaries(db, year=today.year, month=today.month)
        db.commit()
        print(f"Seeded {len(DEMO_EMPLOYEES)} employees with attendance for {month_start} .. {today}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
