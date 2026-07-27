from datetime import date, datetime, time, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    department: Mapped[str] = mapped_column(String(255), default="")
    position: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attendance: Mapped[list["Attendance"]] = relationship(back_populates="employee")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    stored_name: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|completed|failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    template: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    weekday: Mapped[str] = mapped_column(String(20), default="")
    shift: Mapped[str] = mapped_column(String(128), default="")
    scheduled_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    scheduled_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    out_next_day: Mapped[bool] = mapped_column(Boolean, default=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    # values coming straight from the source file (may be empty -> computed instead)
    file_worked_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_late_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_early_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_overtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_absence: Mapped[bool] = mapped_column(Boolean, default=False)
    file_leave: Mapped[bool] = mapped_column(Boolean, default=False)
    file_status: Mapped[str] = mapped_column(String(64), default="")
    # derived values (recomputed whenever settings change)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deduction_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deduction_amount: Mapped[float] = mapped_column(Float, default=0.0)
    overtime_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="present")  # present|absent|leave|weekend|holiday|incomplete

    employee: Mapped["Employee"] = relationship(back_populates="attendance")


class AttendanceSummary(Base):
    __tablename__ = "attendance_summaries"
    __table_args__ = (UniqueConstraint("employee_id", "year", "month", name="uq_summary_employee_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    work_days: Mapped[int] = mapped_column(Integer, default=0)
    present_days: Mapped[int] = mapped_column(Integer, default=0)
    absent_days: Mapped[int] = mapped_column(Integer, default=0)
    leave_days: Mapped[int] = mapped_column(Integer, default=0)
    weekend_days: Mapped[int] = mapped_column(Integer, default=0)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deduction_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deduction_amount: Mapped[float] = mapped_column(Float, default=0.0)
    overtime_amount: Mapped[float] = mapped_column(Float, default=0.0)
    net_minutes: Mapped[int] = mapped_column(Integer, default=0)

    employee: Mapped["Employee"] = relationship()


class WorkSettings(Base):
    __tablename__ = "work_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_start: Mapped[time] = mapped_column(Time, default=time(8, 0))
    work_end: Mapped[time] = mapped_column(Time, default=time(17, 0))
    daily_hours: Mapped[float] = mapped_column(Float, default=8.0)
    break_minutes: Mapped[int] = mapped_column(Integer, default=60)
    grace_minutes: Mapped[int] = mapped_column(Integer, default=10)
    overtime_after: Mapped[time] = mapped_column(Time, default=time(17, 0))
    hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    overtime_hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # per_minute | free_then_all | round_hour | none
    deduction_policy: Mapped[str] = mapped_column(String(32), default="per_minute")
    deduction_free_minutes: Mapped[int] = mapped_column(Integer, default=15)
    count_early_leave: Mapped[bool] = mapped_column(Boolean, default=True)
    weekend_days: Mapped[list] = mapped_column(JSON, default=lambda: ["Friday", "Saturday"])
    company_name: Mapped[str] = mapped_column(String(255), default="")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))  # pdf | excel | csv
    file_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
