from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import AttendanceSummary, Employee
from app.schemas import AnalyzeRequest, DashboardOut
from app.services.calculator import recompute_all

router = APIRouter(prefix="/api", tags=["summary"])


@router.get("/summary", response_model=DashboardOut)
def dashboard_summary(
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    stmt = select(
        func.count(func.distinct(AttendanceSummary.employee_id)),
        func.coalesce(func.sum(AttendanceSummary.worked_minutes), 0),
        func.coalesce(func.sum(AttendanceSummary.overtime_minutes), 0),
        func.coalesce(func.sum(AttendanceSummary.late_minutes), 0),
        func.coalesce(func.sum(AttendanceSummary.absent_days), 0),
        func.coalesce(func.sum(AttendanceSummary.present_days), 0),
        func.coalesce(func.sum(AttendanceSummary.leave_days), 0),
        func.coalesce(func.sum(AttendanceSummary.deduction_minutes), 0),
        func.coalesce(func.sum(AttendanceSummary.deduction_amount), 0.0),
        func.coalesce(func.sum(AttendanceSummary.overtime_amount), 0.0),
        func.coalesce(func.sum(AttendanceSummary.net_minutes), 0),
    )
    if year:
        stmt = stmt.where(AttendanceSummary.year == year)
    if month:
        stmt = stmt.where(AttendanceSummary.month == month)
    row = db.execute(stmt).one()
    total_employees = db.scalar(select(func.count(Employee.id))) or 0
    return DashboardOut(
        employees=row[0] or total_employees,
        worked_minutes=row[1], overtime_minutes=row[2], late_minutes=row[3],
        absent_days=row[4], present_days=row[5], leave_days=row[6],
        deduction_minutes=row[7], deduction_amount=round(row[8], 2),
        overtime_amount=round(row[9], 2), net_minutes=row[10],
    )


@router.post("/analyze")
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """Recompute all derived values + summaries with the current settings."""
    count = recompute_all(db, year=payload.year, month=payload.month)
    return {"recomputed_rows": count}
