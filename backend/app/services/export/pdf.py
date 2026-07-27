"""PDF export with Arabic shaping support (reportlab + arabic_reshaper + bidi)."""
import io
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Attendance, AttendanceSummary, Employee, WorkSettings
from app.services.calculator import effective_work_window
from app.services.export.excel import HEADERS, STATUS_AR, fmt_minutes, fmt_time, summary_rows, totals_row

_FONT_NAME = "Helvetica"
_ARABIC_OK = False

# Try to register an Arabic-capable font (bundled or from Windows/Linux system dirs)
_FONT_CANDIDATES = [
    Path(__file__).parent / "fonts" / "NotoNaskhArabic-Regular.ttf",
    Path("C:/Windows/Fonts/tahoma.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
]
for candidate in _FONT_CANDIDATES:
    if candidate.exists():
        try:
            pdfmetrics.registerFont(TTFont("ArabicFont", str(candidate)))
            _FONT_NAME = "ArabicFont"
            _ARABIC_OK = True
            break
        except Exception:
            continue


def ar(text: str) -> str:
    """Shape + reorder Arabic text for reportlab rendering."""
    if not _ARABIC_OK:
        return text
    return get_display(arabic_reshaper.reshape(str(text)))


def export_pdf(
    employee: Employee, rows: list[Attendance], summary: AttendanceSummary | None,
    year: int, month: int, work_settings: WorkSettings,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        rightMargin=10 * mm, leftMargin=10 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
    )
    title_style = ParagraphStyle("title", fontName=_FONT_NAME, fontSize=16, alignment=1, spaceAfter=4)
    sub_style = ParagraphStyle("sub", fontName=_FONT_NAME, fontSize=11, alignment=1, textColor=colors.HexColor("#475569"))

    company = work_settings.company_name or "Attendance Report"
    elements = [
        Paragraph(ar(company), title_style),
        Paragraph(ar(f"تقرير الحضور والانصراف — {employee.name} ({employee.code}) — {year}-{month:02d}"), sub_style),
        Spacer(1, 6 * mm),
    ]

    # detail table (headers reversed for RTL column order)
    header_row = [ar(h) for h in HEADERS][::-1]
    data = [header_row]
    for a in rows:
        work_start, work_end = effective_work_window(a, work_settings)
        row = [
            a.date.strftime("%Y-%m-%d"), ar(a.weekday), ar(a.shift or "-"),
            fmt_time(work_start), fmt_time(work_end),
            fmt_time(a.check_in), fmt_time(a.check_out) + ("+1" if a.out_next_day else ""),
            fmt_minutes(a.worked_minutes), fmt_minutes(a.late_minutes),
            fmt_minutes(a.early_leave_minutes), fmt_minutes(a.overtime_minutes),
            str(a.deduction_minutes), f"{a.deduction_amount:g}", ar(STATUS_AR.get(a.status, a.status)),
        ]
        data.append(row[::-1])

    data.append([ar(str(v)) for v in totals_row(rows)][::-1])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F1F5F9")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    # summary block
    s_data = [[ar(v), ar(k)] for k, v in summary_rows(summary)]
    if s_data:
        s_table = Table(s_data, colWidths=[60 * mm, 70 * mm], hAlign="RIGHT")
        s_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F8FAFC")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(s_table)

    elements.append(Spacer(1, 12 * mm))
    sig_style = ParagraphStyle("sig", fontName=_FONT_NAME, fontSize=10, alignment=1)
    sig = Table(
        [[Paragraph(ar("توقيع الموظف: ______________"), sig_style),
          Paragraph(ar("اعتماد المدير: ______________"), sig_style)]],
        colWidths=[120 * mm, 120 * mm],
    )
    elements.append(sig)

    doc.build(elements)
    return buf.getvalue()
