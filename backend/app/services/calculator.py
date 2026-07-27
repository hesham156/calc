"""Attendance business calculations.

Every derived value (late, early leave, overtime, deductions, status, summary)
is computed here from the raw punches + the editable WorkSettings, so changing
a setting and re-running /analyze recomputes everything consistently.
"""
import math
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attendance, AttendanceSummary, WorkSettings


def get_or_create_settings(db: Session) -> WorkSettings:
    """Column defaults only materialize on INSERT — persist a row if missing."""
    s = db.scalar(select(WorkSettings))
    if s is None:
        s = WorkSettings()
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _duration_minutes(check_in: time, check_out: time, out_next_day: bool) -> int:
    start = datetime(2000, 1, 1, check_in.hour, check_in.minute)
    end_day = date(2000, 1, 2) if out_next_day else date(2000, 1, 1)
    end = datetime(end_day.year, end_day.month, end_day.day, check_out.hour, check_out.minute)
    return max(0, int((end - start).total_seconds() // 60))


def compute_deduction_minutes(late: int, early: int, s: WorkSettings) -> int:
    base = late + (early if s.count_early_leave else 0)
    if base <= 0 or s.deduction_policy == "none":
        return 0
    if s.deduction_policy == "per_minute":
        return base
    if s.deduction_policy == "free_then_all":
        return 0 if base <= s.deduction_free_minutes else base
    if s.deduction_policy == "round_hour":
        return math.ceil(base / 60) * 60
    return base


def has_own_schedule(att: Attendance) -> bool:
    """True when the file gave this row a usable shift window of its own."""
    return bool(att.scheduled_in and att.scheduled_out and att.scheduled_in < att.scheduled_out)


def effective_work_window(att: Attendance, s: WorkSettings) -> tuple[time, time]:
    """The shift start/end this row is judged against.

    The per-day schedule exported by the device wins when it forms a valid
    same-day window. Devices write placeholders on unscheduled days (e.g.
    06:00 -> 06:00) and reversed windows on some shifts; reading those as a real
    schedule inflated the late minutes, so anything unusable falls back to the
    configured work day. Used both by the calculator and by the API, so the
    times shown in the tables are exactly the ones the numbers came from.
    """
    if has_own_schedule(att):
        return att.scheduled_in, att.scheduled_out
    return s.work_start, s.work_end


def compute_day(att: Attendance, s: WorkSettings) -> None:
    """Fill the derived fields of one attendance row in place."""
    weekday = att.date.strftime("%A")
    is_weekend = weekday in (s.weekend_days or [])
    has_punch = att.check_in is not None or att.check_out is not None

    status_lower = (att.file_status or "").strip().lower()

    # ----- status -----
    if att.file_leave or status_lower in {"leave", "vacation", "اجازة", "إجازة"}:
        att.status = "leave"
    elif not has_punch and is_weekend:
        att.status = "weekend"
    elif att.file_absence and not has_punch:
        att.status = "absent"
    elif not has_punch:
        att.status = "absent"
    elif att.check_in is None or att.check_out is None:
        att.status = "incomplete"
    else:
        att.status = "present"

    # The per-day schedule exported by the device is trusted only when it forms a
    # valid same-day window. Devices write placeholders on unscheduled days (e.g.
    # 06:00 -> 06:00), and reading those as a 06:00 start inflated the late
    # minutes; anything unusable falls back to the configured work day.
    work_start, work_end = effective_work_window(att, s)
    # Overtime is measured from the end of that row's own work day, so an
    # employee scheduled 10:00-19:00 does not collect overtime from the moment
    # the 08:00 crowd goes home. The configured threshold is the fallback for
    # rows that carry no schedule of their own.
    overtime_after = work_end if has_own_schedule(att) else s.overtime_after

    late = early = worked = overtime = 0
    break_minutes = att.break_minutes or 0

    if att.status in ("present", "incomplete") and att.check_in and att.check_out:
        gross = _duration_minutes(att.check_in, att.check_out, att.out_next_day)
        if not break_minutes and gross > s.break_minutes:
            break_minutes = s.break_minutes
        worked = max(0, gross - break_minutes)

        # late: minutes after scheduled start, only when beyond the grace period
        raw_late = max(0, _minutes(att.check_in) - _minutes(work_start))
        late = raw_late if raw_late > s.grace_minutes else 0

        # early leave: minutes before scheduled end (never for overnight rows)
        if not att.out_next_day:
            early = max(0, _minutes(work_end) - _minutes(att.check_out))

        # overtime: worked time after the end of this row's work day
        if att.out_next_day:
            overtime = _duration_minutes(overtime_after, att.check_out, True)
        elif _minutes(att.check_out) > _minutes(overtime_after):
            overtime = _minutes(att.check_out) - _minutes(overtime_after)

    # Everything above is derived from the shift window and the punches alone.
    # The late/early/overtime/worked columns the device writes into the file are
    # deliberately ignored: they are computed against the device's own rules and
    # contradicted the schedule we calculate from. file_absence / file_leave are
    # still honoured (in the status block) since no punch pattern implies them.

    if att.status not in ("present", "incomplete"):
        late = early = overtime = worked = 0
        break_minutes = 0

    ded_minutes = compute_deduction_minutes(late, early, s)

    att.break_minutes = break_minutes
    att.worked_minutes = worked
    att.late_minutes = late
    att.early_leave_minutes = early
    att.overtime_minutes = overtime
    att.deduction_minutes = ded_minutes
    att.deduction_amount = round(ded_minutes / 60 * (s.hourly_rate or 0), 2)
    att.overtime_amount = round(overtime / 60 * (s.overtime_hourly_rate or s.hourly_rate or 0), 2)


def recompute_all(db: Session, year: int | None = None, month: int | None = None) -> int:
    """Recompute derived fields for all (or one month of) attendance rows."""
    s = get_or_create_settings(db)
    q = select(Attendance)
    if year:
        start = date(year, month or 1, 1)
        end = date(year + 1, 1, 1) if not month else (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1))
        q = q.where(Attendance.date >= start, Attendance.date < end)
    count = 0
    for att in db.scalars(q).yield_per(2000):
        compute_day(att, s)
        count += 1
    db.flush()
    rebuild_summaries(db, year=year, month=month)
    db.commit()
    return count


def rebuild_summaries(db: Session, year: int | None = None, month: int | None = None) -> None:
    # aggregation done in python for portability (sqlite + postgres)
    q = select(Attendance)
    if year:
        start = date(year, month or 1, 1)
        end = date(year + 1, 1, 1) if not month else (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1))
        q = q.where(Attendance.date >= start, Attendance.date < end)

    buckets: dict[tuple[int, int, int], dict] = {}
    for att in db.scalars(q).yield_per(2000):
        key = (att.employee_id, att.date.year, att.date.month)
        b = buckets.setdefault(key, {
            "work_days": 0, "present_days": 0, "absent_days": 0, "leave_days": 0,
            "weekend_days": 0, "worked_minutes": 0, "late_minutes": 0,
            "early_leave_minutes": 0, "overtime_minutes": 0, "break_minutes": 0,
            "deduction_minutes": 0, "deduction_amount": 0.0, "overtime_amount": 0.0,
        })
        b["work_days"] += 1 if att.status != "weekend" else 0
        b["present_days"] += 1 if att.status in ("present", "incomplete") else 0
        b["absent_days"] += 1 if att.status == "absent" else 0
        b["leave_days"] += 1 if att.status == "leave" else 0
        b["weekend_days"] += 1 if att.status == "weekend" else 0
        b["worked_minutes"] += att.worked_minutes
        b["late_minutes"] += att.late_minutes
        b["early_leave_minutes"] += att.early_leave_minutes
        b["overtime_minutes"] += att.overtime_minutes
        b["break_minutes"] += att.break_minutes
        b["deduction_minutes"] += att.deduction_minutes
        b["deduction_amount"] += att.deduction_amount
        b["overtime_amount"] += att.overtime_amount

    for (emp_id, y, m), b in buckets.items():
        summary = db.scalar(
            select(AttendanceSummary).where(
                AttendanceSummary.employee_id == emp_id,
                AttendanceSummary.year == y,
                AttendanceSummary.month == m,
            )
        )
        if summary is None:
            summary = AttendanceSummary(employee_id=emp_id, year=y, month=m)
            db.add(summary)
        for k, v in b.items():
            setattr(summary, k, round(v, 2) if isinstance(v, float) else v)
        summary.net_minutes = b["worked_minutes"] + b["overtime_minutes"] - b["deduction_minutes"]
    db.flush()
