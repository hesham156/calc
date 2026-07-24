"""File reading, template detection and row normalization.

Templates live in ``templates/*.json`` — adding support for a new fingerprint
device is a matter of dropping a new JSON file there, no code changes needed.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
from dateutil import parser as dateparser

from app.services.parser.column_mapper import (
    map_columns_generic,
    map_columns_with_template,
    normalize_header,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}


@dataclass
class NormalizedRow:
    employee_code: str
    employee_name: str = ""
    department: str = ""
    position: str = ""
    date: date | None = None
    weekday: str = ""
    shift: str = ""
    scheduled_in: time | None = None
    scheduled_out: time | None = None
    check_in: time | None = None
    check_out: time | None = None
    out_next_day: bool = False
    break_minutes: int | None = None
    worked_minutes: int | None = None
    late_minutes: int | None = None
    early_minutes: int | None = None
    overtime_minutes: int | None = None
    absence: bool = False
    leave: bool = False
    status: str = ""


@dataclass
class ParseResult:
    template: str
    mapping: dict[str, str]
    rows: list[NormalizedRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_rows: int = 0


def load_templates() -> list[dict]:
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            templates.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # pragma: no cover - bad template file
            logger.exception("Failed to load template %s", path)
    return templates


def read_dataframe(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "cp1256", "latin-1"):
            try:
                return pd.read_csv(path, dtype=str, encoding=encoding, keep_default_na=False)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file")
    engine = "xlrd" if ext == ".xls" else "openpyxl"
    df = pd.read_excel(path, dtype=str, engine=engine, keep_default_na=False)
    return df


def detect_template(headers: list[str]) -> dict | None:
    norm = {normalize_header(h) for h in headers}
    for template in load_templates():
        detection = template.get("detection", {})
        ok = all(any(normalize_header(a) in norm for a in [req]) for req in detection.get("required_all", []))
        if not ok:
            continue
        groups = detection.get("required_any", [])
        if all(any(normalize_header(a) in norm for a in group) for group in groups):
            return template
    return None


# ---------- value parsing helpers ----------

_TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm|ص|م)?\s*$", re.IGNORECASE)


def parse_time_value(value) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    s = str(value).strip()
    if not s or s in {"-", "--", "nan", "NaT", "0"}:
        return None
    m = _TIME_RE.match(s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        ss = int(m.group(3) or 0)
        suffix = (m.group(4) or "").lower()
        if suffix in ("pm", "م") and hh < 12:
            hh += 12
        if suffix in ("am", "ص") and hh == 12:
            hh = 0
        if hh == 24:
            hh = 0
        if hh > 23 or mm > 59:
            return None
        return time(hh, mm, ss)
    try:
        return dateparser.parse(s).time()
    except (ValueError, OverflowError):
        return None


def parse_date_value(value, dayfirst: bool = True) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.lower() in {"nan", "nat"}:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return dateparser.parse(s, dayfirst=dayfirst).date()
    except (ValueError, OverflowError):
        return None


def parse_duration_minutes(value) -> int | None:
    """'01:30' -> 90, '1.5' -> 90 (hours), '90m' -> 90, '' -> None."""
    if value is None:
        return None
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    s = str(value).strip().lower()
    if not s or s in {"-", "--", "nan"}:
        return None
    m = re.match(r"^(\d{1,3}):(\d{2})(?::\d{2})?$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(h|hr|hrs|hours|ساعة)?$", s)
    if m and not s.endswith(("m", "min")):
        try:
            return round(float(m.group(1)) * 60)
        except ValueError:
            return None
    m = re.match(r"^(\d+)\s*(m|min|mins|minutes|دقيقة)$", s)
    if m:
        return int(m.group(1))
    return None


def parse_bool_flag(value) -> bool:
    s = str(value).strip().lower()
    if not s or s in {"nan", "0", "0.0", "no", "false", "-"}:
        return False
    try:
        return float(s) > 0
    except ValueError:
        return s in {"yes", "true", "y", "absent", "leave", "نعم", "غياب", "اجازة", "إجازة"}


def resolve_ambiguous_out(check_in: time | None, check_out: time | None) -> tuple[time | None, bool]:
    """BioTime writes 2 PM as 02:00 (12h clock without AM/PM).

    If out < in: prefer interpreting it as PM when that yields a sane (<=16h)
    working day, otherwise treat it as an overnight shift ending next day.
    Returns (fixed_out, out_next_day).
    """
    if check_in is None or check_out is None:
        return check_out, False
    if check_out > check_in:
        return check_out, False
    if check_out.hour < 12:
        pm = time(check_out.hour + 12, check_out.minute, check_out.second)
        if pm > check_in:
            worked_h = (pm.hour * 60 + pm.minute - check_in.hour * 60 - check_in.minute) / 60
            if worked_h <= 16:
                return pm, False
    if check_out == check_in:
        return check_out, False
    return check_out, True  # overnight shift


def parse_file(path: str | Path) -> ParseResult:
    df = read_dataframe(path)
    df.columns = [str(c) for c in df.columns]
    headers = list(df.columns)

    template = detect_template(headers)
    if template:
        mapping = map_columns_with_template(headers, template["columns"])
        # fill any canonical fields the template missed via generic matching
        generic = map_columns_generic([h for h in headers if h not in mapping.values()])
        for k, v in generic.items():
            mapping.setdefault(k, v)
        template_name = template["name"]
        dayfirst = template.get("date_dayfirst", True)
    else:
        mapping = map_columns_generic(headers)
        template_name = "auto"
        dayfirst = True

    if "date" not in mapping:
        raise ValueError("Could not detect a Date column in the file")
    if "employee_id" not in mapping and "employee_name" not in mapping:
        raise ValueError("Could not detect an Employee ID or Name column in the file")

    result = ParseResult(template=template_name, mapping=mapping, total_rows=len(df))

    def cell(row, key):
        col = mapping.get(key)
        if col is None:
            return None
        v = row.get(col)
        if v is None:
            return None
        s = str(v).strip()
        return s if s and s.lower() not in {"nan", "nat"} else None

    for idx, row in enumerate(df.to_dict(orient="records")):
        try:
            d = parse_date_value(cell(row, "date"), dayfirst=dayfirst)
            if d is None:
                result.errors.append(f"Row {idx + 2}: invalid or missing date")
                continue
            code = cell(row, "employee_id") or cell(row, "employee_name") or ""
            code = re.sub(r"\.0$", "", str(code).strip())
            if not code:
                result.errors.append(f"Row {idx + 2}: missing employee id")
                continue

            check_in = parse_time_value(cell(row, "check_in"))
            check_out = parse_time_value(cell(row, "check_out"))
            check_out, out_next_day = resolve_ambiguous_out(check_in, check_out)

            nrow = NormalizedRow(
                employee_code=code,
                employee_name=cell(row, "employee_name") or code,
                department=cell(row, "department") or "",
                position=cell(row, "position") or "",
                date=d,
                weekday=cell(row, "weekday") or d.strftime("%A"),
                shift=cell(row, "shift") or "",
                scheduled_in=parse_time_value(cell(row, "scheduled_in")),
                scheduled_out=parse_time_value(cell(row, "scheduled_out")),
                check_in=check_in,
                check_out=check_out,
                out_next_day=out_next_day,
                break_minutes=parse_duration_minutes(cell(row, "break_minutes")),
                worked_minutes=parse_duration_minutes(cell(row, "worked")),
                late_minutes=parse_duration_minutes(cell(row, "late")),
                early_minutes=parse_duration_minutes(cell(row, "early_leave")),
                overtime_minutes=parse_duration_minutes(cell(row, "overtime")),
                absence=parse_bool_flag(cell(row, "absence")),
                leave=parse_bool_flag(cell(row, "leave")),
                status=cell(row, "status") or "",
            )
            result.rows.append(nrow)
        except Exception as exc:  # keep going on malformed rows
            result.errors.append(f"Row {idx + 2}: {exc}")

    return result
