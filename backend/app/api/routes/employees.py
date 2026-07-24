from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models import Attendance, AttendanceSummary, Employee, User
from app.schemas import AttendanceDayOut, EmployeeOut, EmployeeWithSummary, MonthOut, SummaryOut

router = APIRouter(prefix="/api", tags=["employees"])


@router.get("/months", response_model=list[MonthOut])
def available_months(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(AttendanceSummary.year, AttendanceSummary.month)
        .distinct()
        .order_by(AttendanceSummary.year.desc(), AttendanceSummary.month.desc())
    ).all()
    return [MonthOut(year=y, month=m) for y, m in rows]


@router.get("/employees", response_model=list[EmployeeWithSummary])
def list_employees(
    q: str = Query("", description="search by name or code"),
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Employee).order_by(Employee.name)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Employee.name.ilike(like), Employee.code.ilike(like)))
    employees = db.scalars(stmt).all()

    summaries: dict[int, AttendanceSummary] = {}
    if year and month:
        for s in db.scalars(
            select(AttendanceSummary).where(
                AttendanceSummary.year == year, AttendanceSummary.month == month
            )
        ):
            summaries[s.employee_id] = s

    out = []
    for e in employees:
        s = summaries.get(e.id)
        item = EmployeeWithSummary.model_validate(e)
        item.summary = SummaryOut.model_validate(s) if s else None
        out.append(item)
    return out


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(404, "Employee not found")
    return emp


@router.get("/employees/{employee_id}/attendance", response_model=list[AttendanceDayOut])
def employee_attendance(
    employee_id: int,
    year: int,
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return db.scalars(
        select(Attendance)
        .where(Attendance.employee_id == employee_id, Attendance.date >= start, Attendance.date < end)
        .order_by(Attendance.date)
    ).all()


@router.get("/employees/{employee_id}/summary", response_model=SummaryOut | None)
def employee_summary(
    employee_id: int,
    year: int,
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalar(
        select(AttendanceSummary).where(
            AttendanceSummary.employee_id == employee_id,
            AttendanceSummary.year == year,
            AttendanceSummary.month == month,
        )
    )
