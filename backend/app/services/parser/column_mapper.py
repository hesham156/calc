"""Automatic column detection.

Maps arbitrary source-file headers (English/Arabic, any order, any device brand)
onto the canonical field names used by the rest of the system. Matching order:
template aliases -> generic aliases (exact normalized) -> substring -> fuzzy.
"""
import difflib
import re

CANONICAL_FIELDS = [
    "employee_id", "employee_name", "department", "position", "date", "weekday",
    "shift", "scheduled_in", "scheduled_out", "check_in", "check_out",
    "break_minutes", "worked", "late", "early_leave", "overtime",
    "absence", "leave", "status",
]

# Generic aliases used when no device template matches (auto-discovery mode).
GENERIC_ALIASES: dict[str, list[str]] = {
    "employee_id": [
        "employee id", "emp id", "employee no", "emp no", "staff id", "personnel id",
        "badge number", "badge", "user id", "id", "no", "رقم الموظف", "الرقم الوظيفي", "الرقم",
    ],
    "employee_name": [
        "employee name", "full name", "first name", "name", "user name", "staff name",
        "اسم الموظف", "الاسم", "اسم",
    ],
    "department": ["department", "dept", "section", "القسم", "الادارة", "الإدارة"],
    "position": ["position", "job title", "title", "designation", "الوظيفة", "المسمى الوظيفي"],
    "date": ["date", "att date", "attendance date", "work date", "day date", "التاريخ"],
    "weekday": ["weekday", "day name", "day of week", "day", "اليوم"],
    "shift": ["shift", "timetable", "schedule", "shift name", "الوردية", "الدوام"],
    "scheduled_in": ["on duty", "duty on", "schedule in", "shift start", "بداية الدوام"],
    "scheduled_out": ["off duty", "duty off", "schedule out", "shift end", "نهاية الدوام"],
    "check_in": [
        "check in", "checkin", "clock in", "punch in", "start time", "arrival",
        "in time", "time in", "first punch", "first in", "in", "دخول", "الحضور", "حضور", "وقت الدخول",
    ],
    "check_out": [
        "check out", "checkout", "clock out", "punch out", "end time", "departure",
        "out time", "time out", "last punch", "last out", "out", "خروج", "الانصراف", "انصراف", "وقت الخروج",
    ],
    "break_minutes": ["break duration", "break time", "break", "rest", "استراحة", "الراحة", "راحة"],
    "worked": [
        "worked hours", "work hours", "work time", "worked time", "total time",
        "total hours", "duration", "ساعات العمل", "مدة العمل",
    ],
    "late": ["late in", "late arrival", "late", "delay", "تأخير", "التأخير"],
    "early_leave": ["early out", "early leave", "early departure", "early", "انصراف مبكر", "خروج مبكر"],
    "overtime": ["overtime", "normal ot", "ot hours", "ot", "extra time", "اوفر تايم", "إضافي", "اضافي", "العمل الاضافي"],
    "absence": ["absence", "absent", "غياب", "الغياب"],
    "leave": ["leave", "vacation", "holiday taken", "fild", "اجازة", "إجازة", "الاجازة"],
    "status": ["status", "attendance status", "الحالة", "حالة"],
}


def normalize_header(header: str) -> str:
    """lowercase, strip decorations: 'Late In(HH:MM)' -> 'late in(hh:mm)' and 'late in'."""
    h = str(header).strip().lower()
    h = re.sub(r"\s+", " ", h)
    return h


def strip_units(header: str) -> str:
    """Remove unit suffixes like (hh:mm), (h), (d), (min)."""
    return re.sub(r"\s*\((hh:mm|h|d|m|min|mins|hrs|hours|days)\)\s*$", "", header).strip()


def _match_alias(norm_headers: dict[str, str], aliases: list[str]) -> str | None:
    """Return original column name whose normalized form matches one of the aliases."""
    for alias in aliases:
        for original, norm in norm_headers.items():
            if norm == alias or strip_units(norm) == alias:
                return original
    return None


def map_columns_with_template(headers: list[str], template_columns: dict[str, list[str]]) -> dict[str, str]:
    norm = {h: normalize_header(h) for h in headers}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for field, aliases in template_columns.items():
        col = _match_alias({k: v for k, v in norm.items() if k not in used}, [normalize_header(a) for a in aliases])
        if col:
            mapping[field] = col
            used.add(col)
    return mapping


def map_columns_generic(headers: list[str]) -> dict[str, str]:
    norm = {h: normalize_header(h) for h in headers}
    mapping: dict[str, str] = {}
    used: set[str] = set()

    # pass 1: exact normalized match (longest aliases first so 'check in' wins over 'in')
    for field in CANONICAL_FIELDS:
        aliases = sorted(GENERIC_ALIASES.get(field, []), key=len, reverse=True)
        col = _match_alias({k: v for k, v in norm.items() if k not in used}, aliases)
        if col:
            mapping[field] = col
            used.add(col)

    # pass 2: substring containment for still-unmapped fields
    for field in CANONICAL_FIELDS:
        if field in mapping:
            continue
        for alias in sorted(GENERIC_ALIASES.get(field, []), key=len, reverse=True):
            if len(alias) < 4:
                continue  # too short for substring matching ("in", "out", "id")
            for original, n in norm.items():
                if original in used:
                    continue
                if alias in n:
                    mapping[field] = original
                    used.add(original)
                    break
            if field in mapping:
                break

    # pass 3: fuzzy ratio for anything left
    for field in CANONICAL_FIELDS:
        if field in mapping:
            continue
        best, best_score = None, 0.0
        for alias in GENERIC_ALIASES.get(field, []):
            for original, n in norm.items():
                if original in used:
                    continue
                score = difflib.SequenceMatcher(None, alias, strip_units(n)).ratio()
                if score > best_score:
                    best, best_score = original, score
        if best and best_score >= 0.85:
            mapping[field] = best
            used.add(best)

    return mapping
