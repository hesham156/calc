from datetime import date, time

from app.models import Attendance, WorkSettings
from app.services.calculator import compute_day, compute_deduction_minutes


def make_settings(**kwargs) -> WorkSettings:
    s = WorkSettings(
        work_start=time(8, 0), work_end=time(17, 0), daily_hours=8.0,
        break_minutes=60, grace_minutes=10, overtime_after=time(17, 0),
        hourly_rate=10.0, overtime_hourly_rate=15.0,
        deduction_policy="per_minute", deduction_free_minutes=15,
        count_early_leave=True, weekend_days=["Friday", "Saturday"],
    )
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def make_att(**kwargs) -> Attendance:
    att = Attendance(employee_id=1, date=date(2026, 7, 20), weekday="Monday")
    for k, v in kwargs.items():
        setattr(att, k, v)
    # SQLAlchemy column defaults only apply on flush — set them manually for unit tests
    for f in ("out_next_day", "file_absence", "file_leave"):
        if getattr(att, f) is None:
            setattr(att, f, False)
    if att.break_minutes is None:
        att.break_minutes = 0
    return att


class TestDayComputation:
    def test_normal_day(self):
        s = make_settings()
        att = make_att(check_in=time(8, 0), check_out=time(17, 0))
        compute_day(att, s)
        assert att.status == "present"
        assert att.worked_minutes == 8 * 60  # 9h - 1h break
        assert att.late_minutes == 0
        assert att.overtime_minutes == 0

    def test_late_within_grace(self):
        s = make_settings()
        att = make_att(check_in=time(8, 9), check_out=time(17, 0))
        compute_day(att, s)
        assert att.late_minutes == 0  # within 10 min grace

    def test_late_beyond_grace(self):
        s = make_settings()
        att = make_att(check_in=time(8, 25), check_out=time(17, 0))
        compute_day(att, s)
        assert att.late_minutes == 25
        assert att.deduction_minutes == 25
        assert att.deduction_amount == round(25 / 60 * 10, 2)

    def test_early_leave(self):
        s = make_settings()
        att = make_att(check_in=time(8, 0), check_out=time(16, 0))
        compute_day(att, s)
        assert att.early_leave_minutes == 60

    def test_overtime(self):
        s = make_settings()
        att = make_att(check_in=time(8, 0), check_out=time(19, 30))
        compute_day(att, s)
        assert att.overtime_minutes == 150
        assert att.overtime_amount == round(150 / 60 * 15, 2)

    def test_absent_no_punches(self):
        s = make_settings()
        att = make_att()
        compute_day(att, s)
        assert att.status == "absent"
        assert att.worked_minutes == 0

    def test_weekend(self):
        s = make_settings()
        att = make_att(date=date(2026, 7, 24))  # Friday
        compute_day(att, s)
        assert att.status == "weekend"

    def test_leave_flag(self):
        s = make_settings()
        att = make_att(file_leave=True)
        compute_day(att, s)
        assert att.status == "leave"

    def test_overnight_shift(self):
        s = make_settings()
        att = make_att(check_in=time(22, 0), check_out=time(6, 0), out_next_day=True)
        compute_day(att, s)
        assert att.status == "present"
        assert att.worked_minutes == 7 * 60  # 8h - 1h break

    def test_scheduled_shift_overrides_settings(self):
        s = make_settings()
        # employee scheduled 06:00-14:00 -> arriving 06:20 is 20 min late
        att = make_att(scheduled_in=time(6, 0), scheduled_out=time(14, 0),
                       check_in=time(6, 20), check_out=time(14, 0))
        compute_day(att, s)
        assert att.late_minutes == 20

    def test_scheduled_shift_drives_overtime(self):
        s = make_settings()
        # scheduled 10:00-19:00: leaving at 19:00 is a normal day, not 2h of
        # overtime against the 17:00 threshold meant for the 08:00 shift
        att = make_att(scheduled_in=time(10, 0), scheduled_out=time(19, 0),
                       check_in=time(10, 0), check_out=time(19, 0))
        compute_day(att, s)
        assert att.overtime_minutes == 0
        assert att.early_leave_minutes == 0
        # and an hour past that schedule is one hour of overtime
        att = make_att(scheduled_in=time(10, 0), scheduled_out=time(19, 0),
                       check_in=time(10, 0), check_out=time(20, 0))
        compute_day(att, s)
        assert att.overtime_minutes == 60

    def test_no_overtime_and_early_leave_on_the_same_day(self):
        s = make_settings()
        # scheduled 10:00-19:00, left at 18:00 -> 1h early, never also overtime
        att = make_att(scheduled_in=time(10, 0), scheduled_out=time(19, 0),
                       check_in=time(10, 0), check_out=time(18, 0))
        compute_day(att, s)
        assert att.early_leave_minutes == 60
        assert att.overtime_minutes == 0

    def test_placeholder_schedule_falls_back_to_settings(self):
        s = make_settings()
        # device writes 06:00 -> 06:00 on days with no timetable: a zero-length
        # window is not a schedule, so late/early come from the settings instead
        att = make_att(scheduled_in=time(6, 0), scheduled_out=time(6, 0),
                       check_in=time(11, 0), check_out=time(15, 0))
        compute_day(att, s)
        assert att.late_minutes == 180  # 11:00 vs the configured 08:00 start
        assert att.early_leave_minutes == 120  # 15:00 vs the configured 17:00 end

    def test_reversed_schedule_falls_back_to_settings(self):
        s = make_settings()
        # 09:00 -> 06:00 cannot be read as a same-day window
        att = make_att(scheduled_in=time(9, 0), scheduled_out=time(6, 0),
                       check_in=time(9, 0), check_out=time(17, 0))
        compute_day(att, s)
        assert att.late_minutes == 60  # 09:00 vs the configured 08:00 start


class TestFileReportedValuesAreIgnored:
    """Only the shift window and the punches drive the numbers."""

    def test_file_late_does_not_override_computed(self):
        s = make_settings()
        # device claims 90 late minutes; the punch is on time against 08:00
        att = make_att(check_in=time(8, 0), check_out=time(17, 0), file_late_minutes=90)
        compute_day(att, s)
        assert att.late_minutes == 0

    def test_file_overtime_and_early_are_ignored(self):
        s = make_settings()
        att = make_att(check_in=time(8, 0), check_out=time(17, 0),
                       file_overtime_minutes=120, file_early_minutes=45)
        compute_day(att, s)
        assert att.overtime_minutes == 0
        assert att.early_leave_minutes == 0

    def test_file_worked_does_not_fill_a_day_without_punches(self):
        s = make_settings()
        att = make_att(file_worked_minutes=480)
        compute_day(att, s)
        assert att.status == "absent"
        assert att.worked_minutes == 0

    def test_absence_and_leave_flags_are_still_honoured(self):
        s = make_settings()
        att = make_att(file_leave=True)
        compute_day(att, s)
        assert att.status == "leave"


class TestDeductionPolicies:
    def test_per_minute(self):
        assert compute_deduction_minutes(30, 0, make_settings()) == 30

    def test_free_then_all_below(self):
        s = make_settings(deduction_policy="free_then_all", deduction_free_minutes=15)
        assert compute_deduction_minutes(12, 0, s) == 0

    def test_free_then_all_above(self):
        s = make_settings(deduction_policy="free_then_all", deduction_free_minutes=15)
        assert compute_deduction_minutes(20, 0, s) == 20

    def test_round_hour(self):
        s = make_settings(deduction_policy="round_hour")
        assert compute_deduction_minutes(61, 0, s) == 120
        assert compute_deduction_minutes(60, 0, s) == 60

    def test_none(self):
        s = make_settings(deduction_policy="none")
        assert compute_deduction_minutes(45, 30, s) == 0

    def test_early_leave_excluded(self):
        s = make_settings(count_early_leave=False)
        assert compute_deduction_minutes(10, 50, s) == 10
