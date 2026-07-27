from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Attendance, Employee

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports")
def reports(
    q: str = Query("", description="search employee name/code"),
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    status: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Attendance, Employee)
        .join(Employee, Attendance.employee_id == Employee.id)
        .order_by(Attendance.date.desc(), Employee.name)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Employee.name.ilike(like), Employee.code.ilike(like)))
    if year and month:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        stmt = stmt.where(Attendance.date >= start, Attendance.date < end)
    elif year:
        stmt = stmt.where(Attendance.date >= date(year, 1, 1), Attendance.date < date(year + 1, 1, 1))
    if status:
        stmt = stmt.where(Attendance.status == status)

    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return [
        {
            "id": a.id,
            "employee_id": e.id,
            "employee_name": e.name,
            "employee_code": e.code,
            "date": a.date.isoformat(),
            "weekday": a.weekday,
            "check_in": a.check_in.strftime("%H:%M") if a.check_in else None,
            "check_out": a.check_out.strftime("%H:%M") if a.check_out else None,
            "out_next_day": a.out_next_day,
            "worked_minutes": a.worked_minutes,
            "late_minutes": a.late_minutes,
            "early_leave_minutes": a.early_leave_minutes,
            "overtime_minutes": a.overtime_minutes,
            "deduction_minutes": a.deduction_minutes,
            "deduction_amount": a.deduction_amount,
            "status": a.status,
        }
        for a, e in rows
    ]
