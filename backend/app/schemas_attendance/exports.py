"""Export helpers shared by the payroll and detail CSV endpoints."""

from datetime import date, datetime, time
from decimal import Decimal

PAYROLL_COLUMNS: tuple[str, ...] = (
    "attendance_month",
    "company_name",
    "employee_no",
    "employee_name",
    "department_name",
    "weekday_full",
    "weekend_full",
    "weekday_attended",
    "weekend_attended",
    "paid_leave_days",
    "ot_weekday_hours",
    "ot_weekend_hours",
    "ot_holiday_hours",
    "attendance_deduct",
)

DETAIL_RECORD_TYPES: tuple[str, ...] = (
    "month_summary",
    "day_result",
    "shift_result",
)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def escape_csv_cell(value: object) -> str:
    """Render one CSV cell, neutralising spreadsheet formulas in strings.

    Numeric values are never escaped. String values starting with a formula
    character receive a leading single quote, as required by the export
    contract.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return f"'{text}"
    return text
