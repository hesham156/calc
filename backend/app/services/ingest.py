"""Background processing of an uploaded attendance file.

Reads the file, normalizes rows via the parser, upserts employees and
attendance (bulk, chunked — handles 100k+ rows), runs the calculator and
updates Upload.progress as it goes so the frontend can poll.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select, tuple_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models import Attendance, Employee, Upload
from app.services.calculator import compute_day, get_or_create_settings, rebuild_summaries
from app.services.parser.engine import parse_file

logger = logging.getLogger(__name__)

CHUNK = 2000


def _set_progress(db: Session, upload: Upload, progress: int, **kwargs) -> None:
    upload.progress = min(100, progress)
    for k, v in kwargs.items():
        setattr(upload, k, v)
    db.commit()


def process_upload(upload_id: int) -> None:
    db = SessionLocal()
    upload = db.get(Upload, upload_id)
    if upload is None:
        db.close()
        return
    try:
        _set_progress(db, upload, 5, status="processing")
        path = Path(settings.UPLOAD_DIR) / upload.stored_name
        result = parse_file(path)
        _set_progress(db, upload, 20, template=result.template, total_rows=result.total_rows)

        work_settings = get_or_create_settings(db)

        # ---- upsert employees ----
        codes = {r.employee_code for r in result.rows}
        existing = {e.code: e for e in db.scalars(select(Employee).where(Employee.code.in_(codes)))}
        for row in result.rows:
            emp = existing.get(row.employee_code)
            if emp is None:
                emp = Employee(
                    code=row.employee_code, name=row.employee_name,
                    department=row.department, position=row.position,
                )
                db.add(emp)
                existing[row.employee_code] = emp
            else:  # refresh descriptive fields from latest file
                if row.employee_name and row.employee_name != row.employee_code:
                    emp.name = row.employee_name
                emp.department = row.department or emp.department
                emp.position = row.position or emp.position
        db.flush()
        emp_ids = {code: emp.id for code, emp in existing.items()}
        _set_progress(db, upload, 30)

        # ---- replace existing rows for the same (employee, date), insert in chunks ----
        processed = 0
        for i in range(0, len(result.rows), CHUNK):
            chunk = result.rows[i:i + CHUNK]
            keys = [(emp_ids[r.employee_code], r.date) for r in chunk]
            db.execute(delete(Attendance).where(tuple_(Attendance.employee_id, Attendance.date).in_(keys)))
            objects = []
            seen: set[tuple[int, object]] = set()
            for r in chunk:
                key = (emp_ids[r.employee_code], r.date)
                if key in seen:  # duplicate row inside the file itself
                    continue
                seen.add(key)
                att = Attendance(
                    employee_id=key[0], upload_id=upload.id, date=r.date,
                    weekday=r.weekday, shift=r.shift,
                    scheduled_in=r.scheduled_in, scheduled_out=r.scheduled_out,
                    check_in=r.check_in, check_out=r.check_out, out_next_day=r.out_next_day,
                    break_minutes=r.break_minutes or 0,
                    file_worked_minutes=r.worked_minutes, file_late_minutes=r.late_minutes,
                    file_early_minutes=r.early_minutes, file_overtime_minutes=r.overtime_minutes,
                    file_absence=r.absence, file_leave=r.leave, file_status=r.status,
                )
                compute_day(att, work_settings)
                objects.append(att)
            db.add_all(objects)
            processed += len(chunk)
            _set_progress(db, upload, 30 + int(60 * processed / max(1, len(result.rows))),
                          processed_rows=processed)

        # ---- summaries for affected months ----
        months = {(r.date.year, r.date.month) for r in result.rows}
        for y, m in months:
            rebuild_summaries(db, year=y, month=m)
        db.commit()

        error_note = "; ".join(result.errors[:20]) if result.errors else ""
        _set_progress(db, upload, 100, status="completed", error=error_note,
                      finished_at=datetime.now(timezone.utc))
        logger.info("Upload %s processed: %s rows, template=%s", upload_id, processed, result.template)
    except Exception as exc:
        logger.exception("Upload %s failed", upload_id)
        db.rollback()
        _set_progress(db, upload, 100, status="failed", error=str(exc),
                      finished_at=datetime.now(timezone.utc))
    finally:
        db.close()
