from datetime import date, time
from pathlib import Path

from app.services.parser.column_mapper import map_columns_generic
from app.services.parser.engine import (
    detect_template,
    parse_date_value,
    parse_duration_minutes,
    parse_file,
    parse_time_value,
    resolve_ambiguous_out,
)

DATA = Path(__file__).parent / "data"


class TestValueParsing:
    def test_time_formats(self):
        assert parse_time_value("08:00:00") == time(8, 0)
        assert parse_time_value("8:05") == time(8, 5)
        assert parse_time_value("2:30 PM") == time(14, 30)
        assert parse_time_value("12:00 AM") == time(0, 0)
        assert parse_time_value("") is None
        assert parse_time_value("-") is None

    def test_date_formats(self):
        assert parse_date_value("20-07-2026") == date(2026, 7, 20)
        assert parse_date_value("2026-07-20") == date(2026, 7, 20)
        assert parse_date_value("07/20/2026", dayfirst=False) == date(2026, 7, 20)

    def test_durations(self):
        assert parse_duration_minutes("01:30") == 90
        assert parse_duration_minutes("1.5") == 90
        assert parse_duration_minutes("0:10") == 10
        assert parse_duration_minutes("45m") == 45
        assert parse_duration_minutes("") is None

    def test_ambiguous_pm_checkout(self):
        # BioTime writes 2 PM as 02:00 -> should become 14:00 same day
        out, next_day = resolve_ambiguous_out(time(8, 0), time(2, 0))
        assert out == time(14, 0) and next_day is False

    def test_overnight_shift(self):
        # 22:00 -> 06:00 is a genuine overnight shift
        out, next_day = resolve_ambiguous_out(time(22, 0), time(6, 0))
        assert out == time(6, 0) and next_day is True


class TestColumnMapping:
    def test_generic_aliases(self):
        headers = ["Emp No", "Full Name", "Att Date", "Punch In", "Punch Out", "OT"]
        m = map_columns_generic(headers)
        assert m["employee_id"] == "Emp No"
        assert m["employee_name"] == "Full Name"
        assert m["date"] == "Att Date"
        assert m["check_in"] == "Punch In"
        assert m["check_out"] == "Punch Out"
        assert m["overtime"] == "OT"

    def test_arabic_headers(self):
        headers = ["رقم الموظف", "الاسم", "التاريخ", "دخول", "خروج"]
        m = map_columns_generic(headers)
        assert m["employee_id"] == "رقم الموظف"
        assert m["check_in"] == "دخول"
        assert m["check_out"] == "خروج"


class TestBioTimeFile:
    def test_template_detected(self):
        headers = ["Employee ID", "Check In", "Check Out", "Clock In", "Clock Out", "Duty Duration", "Timetable", "Date"]
        t = detect_template(headers)
        assert t is not None and t["name"] == "zkteco_biotime"

    def test_parse_real_export(self):
        result = parse_file(DATA / "zkteco_biotime_sample.csv")
        assert result.template == "zkteco_biotime"
        assert len(result.rows) == 4
        r0 = result.rows[0]
        assert r0.employee_code == "1"
        assert r0.employee_name == "مراد"
        assert r0.date == date(2026, 7, 20)
        # BioTime: Check In/Out columns are the SCHEDULE, Clock In/Out the punches
        assert r0.scheduled_in == time(6, 0)
        assert r0.check_in is None
        # absence flag row (Absence(D) = 1.0)
        r2 = result.rows[2]
        assert r2.date == date(2026, 7, 22)
        assert r2.absence is True
        assert r2.shift == "ets duty"
