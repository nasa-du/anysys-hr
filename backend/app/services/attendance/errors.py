"""Attendance domain error codes.

These codes appear in the shared ``ErrorResponse`` envelope. Import
row-level error and warning codes are stored in ``import_batch_error`` only
and must not be promoted to this vocabulary.
"""

from enum import StrEnum


class AttendanceErrorCode(StrEnum):
    # Shared references and resources
    NOT_FOUND = "not_found"
    CROSS_COMPANY = "cross_company"
    INVALID_REFERENCE = "invalid_reference"
    INACTIVE_REFERENCE = "inactive_reference"
    REFERENCED = "referenced"
    DEACTIVATE_BLOCKED = "deactivate_blocked"
    ACTIVATION_BLOCKED = "activation_blocked"
    DUPLICATE_CODE = "duplicate_code"

    # Shifts, plans, and roster
    INVALID_TIME_RANGE = "invalid_time_range"
    INVALID_SCOPE = "invalid_scope"
    SCHEDULE_CONFLICT = "schedule_conflict"
    SCHEDULE_EXPANSION_BLOCKED = "schedule_expansion_blocked"
    PLAN_ARCHIVED = "plan_archived"
    EMPLOYEE_OUT_OF_RANGE = "employee_out_of_range"
    ROSTER_ENTRY_NOT_MANUAL = "roster_entry_not_manual"
    ROSTER_BATCH_INVALID = "roster_batch_invalid"

    # Months, calculation, and adjustments
    MONTH_CONFIRMED = "month_confirmed"
    MONTH_LOCKED = "month_locked"
    MONTH_NOT_CALCULATED = "month_not_calculated"
    MONTH_STALE = "month_stale"
    INVALID_MONTH_TRANSITION = "invalid_month_transition"
    CALC_IN_PROGRESS = "calc_in_progress"
    CALC_RUN_FAILED = "calc_run_failed"
    ADJUSTMENT_CONFLICT = "adjustment_conflict"

    # Holidays
    DUPLICATE_HOLIDAY = "duplicate_holiday"
    HOLIDAY_CONFLICT = "holiday_conflict"

    # Imports
    IMPORT_PARSE_FAILED = "import_parse_failed"
    MISSING_REQUIRED_COLUMN = "missing_required_column"
    SHEET_REQUIRED = "sheet_required"
    PREVIEW_EXPIRED = "preview_expired"
    IMPORT_COMMIT_CONFLICT = "import_commit_conflict"
    NO_VALID_ROWS = "no_valid_rows"
    BATCH_NOT_PREVIEW = "batch_not_preview"
    BATCH_NOT_REVOCABLE = "batch_not_revocable"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
