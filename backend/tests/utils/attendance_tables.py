"""Independent list of the 24 attendance tables.

Tests keep their own copy so a missing model cannot silently shorten the
isolation and migration assertions.
"""

CORE_TABLES: tuple[str, ...] = (
    "shift",
    "holiday",
    "attendance_rule",
    "attendance_month",
    "calc_run",
    "attendance_month_snapshot",
)

SCHEDULING_TABLES: tuple[str, ...] = (
    "schedule_plan",
    "plan_scope",
    "plan_day",
    "plan_rule_override",
    "roster_entry",
    "roster_entry_shift",
)

IMPORT_TABLES: tuple[str, ...] = (
    "import_batch",
    "import_batch_error",
    "import_mapping_template",
    "punch_record",
    "oa_trip",
    "oa_overtime",
    "oa_overtime_day",
    "oa_leave",
)

RESULT_TABLES: tuple[str, ...] = (
    "attendance_day_result",
    "attendance_day_shift_result",
    "attendance_month_summary",
    "attendance_result_adjustment",
)

ATTENDANCE_TABLES: tuple[str, ...] = (
    *CORE_TABLES,
    *SCHEDULING_TABLES,
    *IMPORT_TABLES,
    *RESULT_TABLES,
)
