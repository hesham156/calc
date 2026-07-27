from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_work_settings
from app.db.database import get_db
from app.models import Attendance, AttendanceSummary, Employee, Report
from app.services.export.excel import export_csv, export_excel
from app.services.export.pdf import export_pdf

router = APIRouter(prefix="/api/export", tags=["export"])

MEDIA = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}
EXT = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}


def _load(db: Session, employee_id: int, year: int, month: int):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(404, "Employee not found")
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    rows = db.scalars(
        select(Attendance)
        .where(Attendance.employee_id == employee_id, Attendance.date >= start, Attendance.date < end)
        .order_by(Attendance.date)
    ).all()
    summary = db.scalar(
        select(AttendanceSummary).where(
            AttendanceSummary.employee_id == employee_id,
            AttendanceSummary.year == year,
            AttendanceSummary.month == month,
        )
    )
    return emp, rows, summary


@router.get("/{kind}")
def export_report(
    kind: str,
    employee_id: int,
    year: int,
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    if kind not in MEDIA:
        raise HTTPException(404, "Unknown export format (pdf | excel | csv)")
    emp, rows, summary = _load(db, employee_id, year, month)
    ws = get_work_settings(db)

    if kind == "pdf":
        content = export_pdf(emp, rows, summary, year, month, ws)
    elif kind == "excel":
        content = export_excel(emp, rows, summary, year, month, ws)
    else:
        content = export_csv(emp, rows, summary)

    db.add(Report(employee_id=employee_id, year=year, month=month, kind=kind, file_path=""))
    db.commit()

    filename = f"attendance_{emp.code}_{year}-{month:02d}.{EXT[kind]}"
    return Response(
        content=content,
        media_type=MEDIA[kind],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
