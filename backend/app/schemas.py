from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

# ---------- Settings ----------


class WorkSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    work_start: time
    work_end: time
    daily_hours: float
    break_minutes: int
    grace_minutes: int
    overtime_after: time
    hourly_rate: float | None
    overtime_hourly_rate: float | None
    deduction_policy: str
    deduction_free_minutes: int
    count_early_leave: bool
    weekend_days: list[str]
    company_name: str


class WorkSettingsUpdate(BaseModel):
    work_start: time | None = None
    work_end: time | None = None
    daily_hours: float | None = Field(default=None, gt=0, le=24)
    break_minutes: int | None = Field(default=None, ge=0, le=480)
    grace_minutes: int | None = Field(default=None, ge=0, le=240)
    overtime_after: time | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    overtime_hourly_rate: float | None = Field(default=None, ge=0)
    deduction_policy: str | None = Field(default=None, pattern="^(per_minute|free_then_all|round_hour|none)$")
    deduction_free_minutes: int | None = Field(default=None, ge=0, le=240)
    count_early_leave: bool | None = None
    weekend_days: list[str] | None = None
    company_name: str | None = None


# ---------- Uploads ----------


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    status: str
    progress: int
    total_rows: int
    processed_rows: int
    template: str
    error: str
    created_at: datetime


# ---------- Employees / attendance ----------


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    department: str
    position: str


class AttendanceDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    weekday: str
    shift: str
    check_in: time | None
    check_out: time | None
    out_next_day: bool
    break_minutes: int
    worked_minutes: int
    late_minutes: int
    early_leave_minutes: int
    overtime_minutes: int
    deduction_minutes: int
    deduction_amount: float
    overtime_amount: float
    status: str


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    year: int
    month: int
    work_days: int
    present_days: int
    absent_days: int
    leave_days: int
    weekend_days: int
    worked_minutes: int
    late_minutes: int
    early_leave_minutes: int
    overtime_minutes: int
    break_minutes: int
    deduction_minutes: int
    deduction_amount: float
    overtime_amount: float
    net_minutes: int


class EmployeeWithSummary(EmployeeOut):
    summary: SummaryOut | None = None


class DashboardOut(BaseModel):
    employees: int
    worked_minutes: int
    overtime_minutes: int
    late_minutes: int
    absent_days: int
    present_days: int
    leave_days: int
    deduction_minutes: int
    deduction_amount: float
    overtime_amount: float
    net_minutes: int


class AnalyzeRequest(BaseModel):
    year: int | None = None
    month: int | None = Field(default=None, ge=1, le=12)


class MonthOut(BaseModel):
    year: int
    month: int
