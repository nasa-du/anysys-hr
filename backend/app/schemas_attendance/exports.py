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

# Common identity columns first, then every month-summary field, then the
# day-result and shift-result fields. ``day_`` / ``shift_`` prefixes keep the
# union unambiguous where a field (for example ``worked_minutes``) exists in
# more than one record type.
DETAIL_COLUMNS: tuple[str, ...] = (
    "record_type",
    "attendance_month",
    "company_name",
    "company_id",
    "attendance_month_id",
    "employee_no",
    "employee_name",
    "department_name",
    "employee_id",
    "work_date",
    "calc_run_id",
    "month_summary_id",
    # Month summary (spec section 4.9.3)
    "weekday_full",
    "weekend_full",
    "weekday_attended",
    "weekend_attended",
    "paid_leave_days",
    "unpaid_leave_days",
    "comp_leave_days",
    "trip_days",
    "ot_weekday_minutes",
    "ot_weekend_minutes",
    "ot_holiday_minutes",
    "ot_weekday_hours",
    "ot_weekend_hours",
    "ot_holiday_hours",
    "comp_leave_used_hours",
    "comp_offset_unused_minutes",
    "late_count",
    "late_minutes",
    "early_count",
    "early_minutes",
    "missing_punch_count",
    "absent_days",
    "worked_minutes",
    "attendance_deduct",
    "is_adjusted",
    "calc_version",
    "rules_version",
    "month_summary_created_at",
    # Day result (spec section 4.9.1)
    "day_id",
    "day_type",
    "roster_state",
    "day_status",
    "day_flags",
    "is_abnormal",
    "day_attendance_fraction",
    "day_scheduled_minutes",
    "day_worked_minutes",
    "day_late_minutes",
    "day_early_minutes",
    "day_late_count",
    "day_early_count",
    "day_missing_punch_count",
    "day_leave_kind",
    "day_leave_days",
    "day_paid_leave_days",
    "day_unpaid_leave_days",
    "day_comp_leave_days",
    "day_trip_kind",
    "day_trip_fraction",
    "day_ot_weekday_minutes",
    "day_ot_weekend_minutes",
    "day_ot_holiday_minutes",
    "day_comp_offset_minutes",
    "day_comp_offset_unused_minutes",
    "day_absent_deduct_amount",
    "day_late_deduct_amount",
    "day_early_deduct_amount",
    "day_missing_punch_deduct_amount",
    "day_deduction_total",
    "day_is_adjusted",
    "day_adjustment_id",
    "day_note",
    "day_created_at",
    "day_updated_at",
    # Shift result (spec section 4.9.2)
    "shift_result_id",
    "shift_day_result_id",
    "shift_id",
    "shift_seq",
    "shift_code",
    "shift_name",
    "shift_start_time",
    "shift_end_time",
    "shift_cross_day",
    "shift_break_start",
    "shift_break_end",
    "shift_rest_minutes",
    "shift_status",
    "shift_flags",
    "shift_punch_in_at",
    "shift_punch_out_at",
    "shift_break_out_at",
    "shift_break_in_at",
    "shift_scheduled_minutes",
    "shift_worked_minutes",
    "shift_late_minutes",
    "shift_early_minutes",
    "shift_missing_punch_count",
    "shift_ot_minutes",
    "shift_comp_offset_minutes",
    "shift_leave_days",
    "shift_note",
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
