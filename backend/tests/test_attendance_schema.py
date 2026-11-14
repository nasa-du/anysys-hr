"""Schema contract for the Attendance persistence foundation.

These tests reflect the migrated PostgreSQL database. The migrations are the
deliverable, so the assertions are written from the approved specification in
``docs/specs/attendance-management.md`` (sections 4.10, 4.12, and 12) rather
than from the SQLModel metadata.
"""

import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import User
from tests.utils.attendance_tables import ATTENDANCE_TABLES

ColumnCheck = tuple[Callable[[sa.types.TypeEngine[Any]], bool], bool]


def _uuid_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Uuid) and value.as_uuid


def _varchar(length: int) -> Callable[[sa.types.TypeEngine[Any]], bool]:
    def check(value: sa.types.TypeEngine[Any]) -> bool:
        return isinstance(value, sa.String) and value.length == length

    return check


def _numeric(precision: int, scale: int) -> Callable[[sa.types.TypeEngine[Any]], bool]:
    def check(value: sa.types.TypeEngine[Any]) -> bool:
        return (
            isinstance(value, sa.Numeric)
            and value.precision == precision
            and value.scale == scale
        )

    return check


def _timestamp_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.DateTime) and value.timezone is True


def _date_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Date) and not isinstance(value, sa.DateTime)


def _time_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Time) and not isinstance(value, sa.DateTime)


def _integer_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Integer)


def _boolean_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Boolean)


def _jsonb_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, JSONB)


def _text(length: int, *, nullable: bool = False) -> ColumnCheck:
    return (_varchar(length), nullable)


def _uuid(*, nullable: bool = False) -> ColumnCheck:
    return (_uuid_type, nullable)


def _timestamp(*, nullable: bool = False) -> ColumnCheck:
    return (_timestamp_type, nullable)


def _jsonb(*, nullable: bool = False) -> ColumnCheck:
    return (_jsonb_type, nullable)


_ID = _uuid()
_CREATED = _timestamp()
_UPDATED = _timestamp()

_RULE_COLUMNS: dict[str, ColumnCheck] = {
    "punch_window_min": (_integer_type, False),
    "late_cap_min": (_integer_type, False),
    "early_cap_min": (_integer_type, False),
    "ot_max_min": (_integer_type, False),
    "late_grace_min": (_integer_type, False),
    "early_grace_min": (_integer_type, False),
    "ot_threshold_min": (_integer_type, False),
    "absent_if_no_punch": (_boolean_type, False),
    "break_punch_required": (_boolean_type, False),
    "break_punch_tolerance_min": (_integer_type, False),
    "absent_deduct_per_day": (_numeric(14, 2), False),
    "late_deduct_per_occurrence": (_numeric(14, 2), False),
    "early_deduct_per_occurrence": (_numeric(14, 2), False),
    "missing_punch_deduct_per_occurrence": (_numeric(14, 2), False),
}
_NULLABLE_RULE_COLUMNS: dict[str, ColumnCheck] = {
    name: (type_check, True) for name, (type_check, _nullable) in _RULE_COLUMNS.items()
}

COLUMNS: dict[str, dict[str, ColumnCheck]] = {
    "shift": {
        "id": _ID,
        "company_id": _uuid(),
        "shift_code": _text(32),
        "shift_name": _text(100),
        "start_time": (_time_type, False),
        "end_time": (_time_type, False),
        "cross_day": (_boolean_type, False),
        "break_start": (_time_type, True),
        "break_end": (_time_type, True),
        "rest_minutes": (_integer_type, False),
        "color": _text(16, nullable=True),
        "note": _text(500, nullable=True),
        "is_active": (_boolean_type, False),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "holiday": {
        "id": _ID,
        "company_id": _uuid(),
        "date": (_date_type, False),
        "name": _text(100),
        "day_type": _text(16),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "attendance_rule": {
        "id": _ID,
        "company_id": _uuid(),
        **_RULE_COLUMNS,
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "attendance_month": {
        "id": _ID,
        "company_id": _uuid(),
        "month": (_date_type, False),
        "status": _text(10),
        "is_stale": (_boolean_type, False),
        "calculated_at": _timestamp(nullable=True),
        "confirmed_at": _timestamp(nullable=True),
        "locked_at": _timestamp(nullable=True),
        "unlock_reason": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "calc_run": {
        "id": _ID,
        "attendance_month_id": _uuid(),
        "trigger": _text(14),
        "status": _text(7),
        "calc_version": _text(32),
        "rules_version": _text(64),
        "roster_version": _text(64),
        "rules_snapshot": _jsonb(),
        "input_batches": _jsonb(),
        "summary": _jsonb(nullable=True),
        "error_code": _text(50, nullable=True),
        "error_message": _text(500, nullable=True),
        "started_at": _timestamp(),
        "finished_at": _timestamp(),
    },
    "attendance_month_snapshot": {
        "id": _ID,
        "attendance_month_id": _uuid(),
        "calc_run_id": _uuid(),
        "version": (_integer_type, False),
        "locked_at": _timestamp(),
        "locked_by": _uuid(),
        "payload": _jsonb(),
    },
    "schedule_plan": {
        "id": _ID,
        "company_id": _uuid(),
        "month": (_date_type, False),
        "plan_name": _text(100),
        "scope_type": _text(8),
        "status": _text(8),
        "copied_from_plan_id": _uuid(nullable=True),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "plan_scope": {
        "id": _ID,
        "plan_id": _uuid(),
        "scope_id": _uuid(),
    },
    "plan_day": {
        "id": _ID,
        "plan_id": _uuid(),
        "day_of_month": (_integer_type, False),
        "seq": (_integer_type, False),
        "shift_id": _uuid(),
    },
    "plan_rule_override": {
        "plan_id": _uuid(),
        **_NULLABLE_RULE_COLUMNS,
    },
    "roster_entry": {
        "id": _ID,
        "company_id": _uuid(),
        "employee_id": _uuid(),
        "work_date": (_date_type, False),
        "state": _text(4),
        "source": _text(6),
        "plan_id": _uuid(nullable=True),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "roster_entry_shift": {
        "id": _ID,
        "roster_entry_id": _uuid(),
        "seq": (_integer_type, False),
        "shift_id": _uuid(),
        "shift_code": _text(32),
        "shift_name": _text(100),
        "start_time": (_time_type, False),
        "end_time": (_time_type, False),
        "cross_day": (_boolean_type, False),
        "break_start": (_time_type, True),
        "break_end": (_time_type, True),
        "rest_minutes": (_integer_type, False),
    },
    "import_batch": {
        "id": _ID,
        "company_id": _uuid(),
        "data_type": _text(5),
        "month": (_date_type, False),
        "status": _text(10),
        "source": _text(6),
        "file_name": _text(255, nullable=True),
        "file_size": (_integer_type, True),
        "file_sha256": _text(64, nullable=True),
        "sheet_name": _text(100, nullable=True),
        "header_row_number": (_integer_type, True),
        "header_columns": _jsonb(),
        "column_mapping": _jsonb(),
        "parser_version": _text(32),
        "source_rows": (_integer_type, False),
        "valid_records": (_integer_type, False),
        "skipped_records": (_integer_type, False),
        "error_records": (_integer_type, False),
        "warning_records": (_integer_type, False),
        "skip_counts": _jsonb(),
        "warning_counts": _jsonb(),
        "operator_id": _uuid(),
        "created_at": _CREATED,
        "committed_at": _timestamp(nullable=True),
        "superseded_at": _timestamp(nullable=True),
        "discarded_at": _timestamp(nullable=True),
        "revoked_at": _timestamp(nullable=True),
        "expires_at": _timestamp(nullable=True),
        "superseded_by_batch_id": _uuid(nullable=True),
        "discard_reason": _text(32, nullable=True),
    },
    "import_batch_error": {
        "id": _ID,
        "batch_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "column_name": _text(100, nullable=True),
        "code": _text(50),
        "message": _text(500),
        "severity": _text(7),
        "raw_row": _jsonb(),
        "created_at": _CREATED,
    },
    "import_mapping_template": {
        "id": _ID,
        "company_id": _uuid(),
        "data_type": _text(5),
        "mapping": _jsonb(),
        "header_columns": _jsonb(),
        "updated_by": _uuid(),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "punch_record": {
        "id": _ID,
        "company_id": _uuid(),
        "batch_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "employee_id": _uuid(),
        "employee_no_raw": _text(32),
        "employee_name_raw": _text(100),
        "department_raw": _text(100),
        "attendance_date": (_date_type, False),
        "punch_time": _timestamp(),
        "punch_result_raw": _text(50),
        "device_raw": _text(200, nullable=True),
        "address_raw": _text(200, nullable=True),
        "raw_row": _jsonb(),
        "created_at": _CREATED,
    },
    "oa_trip": {
        "id": _ID,
        "company_id": _uuid(),
        "batch_id": _uuid(),
        "employee_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "split_index": (_integer_type, False),
        "approval_no": _text(100, nullable=True),
        "employee_name_raw": _text(100),
        "department_raw": _text(100),
        "application_type_raw": _text(100, nullable=True),
        "approval_result_raw": _text(50),
        "approval_status_raw": _text(50),
        "start_at": _timestamp(),
        "end_at": _timestamp(),
        "start_date": (_date_type, False),
        "end_date": (_date_type, False),
        "days_declared": (_numeric(6, 2), True),
        "reason": _text(500, nullable=True),
        "raw_row": _jsonb(),
        "created_at": _CREATED,
    },
    "oa_overtime": {
        "id": _ID,
        "company_id": _uuid(),
        "batch_id": _uuid(),
        "employee_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "approval_no": _text(100, nullable=True),
        "employee_name_raw": _text(100),
        "department_raw": _text(100),
        "approval_result_raw": _text(50),
        "approval_status_raw": _text(50),
        "start_at": _timestamp(),
        "end_at": _timestamp(),
        "declared_raw": _text(50, nullable=True),
        "reason": _text(500, nullable=True),
        "raw_row": _jsonb(),
        "created_at": _CREATED,
    },
    "oa_overtime_day": {
        "id": _ID,
        "company_id": _uuid(),
        "overtime_id": _uuid(),
        "work_date": (_date_type, False),
        "minutes": (_integer_type, False),
        "created_at": _CREATED,
    },
    "oa_leave": {
        "id": _ID,
        "company_id": _uuid(),
        "batch_id": _uuid(),
        "employee_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "approval_no": _text(100, nullable=True),
        "employee_name_raw": _text(100),
        "department_raw": _text(100),
        "leave_type_raw": _text(100),
        "leave_kind": _text(6),
        "days": (_numeric(5, 2), False),
        "rest_start_at": _timestamp(),
        "rest_end_at": _timestamp(),
        "rest_start_date": (_date_type, False),
        "rest_end_date": (_date_type, False),
        "work_start_at": _timestamp(nullable=True),
        "work_end_at": _timestamp(nullable=True),
        "work_start_date": (_date_type, True),
        "work_end_date": (_date_type, True),
        "balance_days_declared": (_numeric(6, 2), True),
        "reason": _text(500, nullable=True),
        "approval_result_raw": _text(50),
        "approval_status_raw": _text(50),
        "raw_row": _jsonb(),
        "created_at": _CREATED,
    },
    "attendance_day_result": {
        "id": _ID,
        "company_id": _uuid(),
        "attendance_month_id": _uuid(),
        "calc_run_id": _uuid(),
        "employee_id": _uuid(),
        "work_date": (_date_type, False),
        "day_type": _text(7),
        "roster_state": _text(11),
        "day_status": _text(22),
        "day_flags": _jsonb(),
        "attendance_fraction": (_numeric(3, 1), False),
        "scheduled_minutes": (_integer_type, False),
        "worked_minutes": (_integer_type, False),
        "late_minutes": (_integer_type, False),
        "early_minutes": (_integer_type, False),
        "late_count": (_integer_type, False),
        "early_count": (_integer_type, False),
        "missing_punch_count": (_integer_type, False),
        "leave_kind": _text(6, nullable=True),
        "leave_days": (_numeric(3, 1), False),
        "paid_leave_days": (_numeric(3, 1), False),
        "unpaid_leave_days": (_numeric(3, 1), False),
        "comp_leave_days": (_numeric(3, 1), False),
        "trip_kind": _text(8, nullable=True),
        "trip_fraction": (_numeric(3, 1), False),
        "ot_weekday_minutes": (_integer_type, False),
        "ot_weekend_minutes": (_integer_type, False),
        "ot_holiday_minutes": (_integer_type, False),
        "comp_offset_minutes": (_integer_type, False),
        "comp_offset_unused_minutes": (_integer_type, False),
        "absent_deduct_amount": (_numeric(14, 2), False),
        "late_deduct_amount": (_numeric(14, 2), False),
        "early_deduct_amount": (_numeric(14, 2), False),
        "missing_punch_deduct_amount": (_numeric(14, 2), False),
        "deduction_total": (_numeric(14, 2), False),
        "is_adjusted": (_boolean_type, False),
        "adjustment_id": _uuid(nullable=True),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "attendance_day_shift_result": {
        "id": _ID,
        "company_id": _uuid(),
        "day_result_id": _uuid(),
        "calc_run_id": _uuid(),
        "employee_id": _uuid(),
        "work_date": (_date_type, False),
        "seq": (_integer_type, False),
        "shift_id": _uuid(),
        "shift_code": _text(32),
        "shift_name": _text(100),
        "start_time": (_time_type, False),
        "end_time": (_time_type, False),
        "cross_day": (_boolean_type, False),
        "break_start": (_time_type, True),
        "break_end": (_time_type, True),
        "rest_minutes": (_integer_type, False),
        "shift_status": _text(22),
        "shift_flags": _jsonb(),
        "punch_in_at": _timestamp(nullable=True),
        "punch_out_at": _timestamp(nullable=True),
        "break_out_at": _timestamp(nullable=True),
        "break_in_at": _timestamp(nullable=True),
        "scheduled_minutes": (_integer_type, False),
        "worked_minutes": (_integer_type, False),
        "late_minutes": (_integer_type, False),
        "early_minutes": (_integer_type, False),
        "missing_punch_count": (_integer_type, False),
        "ot_minutes": (_integer_type, False),
        "comp_offset_minutes": (_integer_type, False),
        "leave_days": (_numeric(3, 1), False),
        "note": _text(500, nullable=True),
    },
    "attendance_month_summary": {
        "id": _ID,
        "company_id": _uuid(),
        "attendance_month_id": _uuid(),
        "calc_run_id": _uuid(),
        "employee_id": _uuid(),
        "weekday_full": (_numeric(5, 1), False),
        "weekend_full": (_numeric(5, 1), False),
        "weekday_attended": (_numeric(5, 1), False),
        "weekend_attended": (_numeric(5, 1), False),
        "paid_leave_days": (_numeric(5, 1), False),
        "unpaid_leave_days": (_numeric(5, 1), False),
        "comp_leave_days": (_numeric(5, 1), False),
        "trip_days": (_numeric(5, 1), False),
        "ot_weekday_minutes": (_integer_type, False),
        "ot_weekend_minutes": (_integer_type, False),
        "ot_holiday_minutes": (_integer_type, False),
        "ot_weekday_hours": (_numeric(7, 2), False),
        "ot_weekend_hours": (_numeric(7, 2), False),
        "ot_holiday_hours": (_numeric(7, 2), False),
        "comp_leave_used_hours": (_numeric(7, 2), False),
        "comp_offset_unused_minutes": (_integer_type, False),
        "late_count": (_integer_type, False),
        "late_minutes": (_integer_type, False),
        "early_count": (_integer_type, False),
        "early_minutes": (_integer_type, False),
        "missing_punch_count": (_integer_type, False),
        "absent_days": (_integer_type, False),
        "worked_minutes": (_integer_type, False),
        "attendance_deduct": (_numeric(14, 2), False),
        "is_adjusted": (_boolean_type, False),
        "calc_version": _text(32),
        "rules_version": _text(64),
        "created_at": _CREATED,
    },
    "attendance_result_adjustment": {
        "id": _ID,
        "company_id": _uuid(),
        "attendance_month_id": _uuid(),
        "employee_id": _uuid(),
        "work_date": (_date_type, False),
        "version": (_integer_type, False),
        "status": _text(10),
        "original_values": _jsonb(),
        "adjusted_values": _jsonb(),
        "reason": _text(500),
        "adjusted_by": _uuid(),
        "adjusted_at": _timestamp(),
        "calc_run_id": _uuid(),
    },
}

PRIMARY_KEYS: dict[str, tuple[str, ...]] = dict.fromkeys(ATTENDANCE_TABLES, ("id",))
PRIMARY_KEYS["plan_rule_override"] = ("plan_id",)

UNIQUE_CONSTRAINTS: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    "shift": {("uq_shift_company_shift_code", ("company_id", "shift_code"))},
    "holiday": {("uq_holiday_company_date", ("company_id", "date"))},
    "attendance_rule": {("uq_attendance_rule_company", ("company_id",))},
    "attendance_month": {
        ("uq_attendance_month_company_month", ("company_id", "month"))
    },
    "calc_run": set(),
    "attendance_month_snapshot": {
        (
            "uq_attendance_month_snapshot_month_version",
            ("attendance_month_id", "version"),
        )
    },
    "schedule_plan": set(),
    "plan_scope": {("uq_plan_scope_plan_scope_id", ("plan_id", "scope_id"))},
    "plan_day": {
        ("uq_plan_day_plan_day_seq", ("plan_id", "day_of_month", "seq")),
        ("uq_plan_day_plan_day_shift", ("plan_id", "day_of_month", "shift_id")),
    },
    "plan_rule_override": set(),
    "roster_entry": {("uq_roster_entry_employee_date", ("employee_id", "work_date"))},
    "roster_entry_shift": {
        ("uq_roster_entry_shift_entry_seq", ("roster_entry_id", "seq"))
    },
    "import_batch": set(),
    "import_batch_error": set(),
    "import_mapping_template": {
        (
            "uq_import_mapping_template_company_type",
            ("company_id", "data_type"),
        )
    },
    "punch_record": {
        (
            "uq_punch_record_batch_employee_date_time",
            ("batch_id", "employee_id", "attendance_date", "punch_time"),
        ),
        ("uq_punch_record_batch_row", ("batch_id", "source_row_number")),
    },
    "oa_trip": {
        (
            "uq_oa_trip_batch_row_split",
            ("batch_id", "source_row_number", "split_index"),
        )
    },
    "oa_overtime": {("uq_oa_overtime_batch_row", ("batch_id", "source_row_number"))},
    "oa_overtime_day": {
        ("uq_oa_overtime_day_overtime_date", ("overtime_id", "work_date"))
    },
    "oa_leave": {("uq_oa_leave_batch_row", ("batch_id", "source_row_number"))},
    "attendance_day_result": {
        (
            "uq_attendance_day_result_month_employee_date",
            ("attendance_month_id", "employee_id", "work_date"),
        )
    },
    "attendance_day_shift_result": {
        ("uq_attendance_day_shift_result_day_seq", ("day_result_id", "seq"))
    },
    "attendance_month_summary": {
        (
            "uq_attendance_month_summary_month_employee",
            ("attendance_month_id", "employee_id"),
        )
    },
    "attendance_result_adjustment": set(),
}

PLAIN_INDEXES: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    table: set() for table in ATTENDANCE_TABLES
}
PLAIN_INDEXES.update(
    {
        "schedule_plan": {
            (
                "ix_schedule_plan_company_month_status",
                ("company_id", "month", "status"),
            )
        },
        "roster_entry": {
            ("ix_roster_entry_company_date", ("company_id", "work_date")),
            ("ix_roster_entry_employee_date", ("employee_id", "work_date")),
            ("ix_roster_entry_plan_id", ("plan_id",)),
        },
        "holiday": {("ix_holiday_company_date", ("company_id", "date"))},
        "attendance_month": {
            ("ix_attendance_month_company_status", ("company_id", "status"))
        },
        "calc_run": {
            ("ix_calc_run_month_started", ("attendance_month_id", "started_at"))
        },
        "import_batch": {
            (
                "ix_import_batch_company_type_month_status",
                ("company_id", "data_type", "month", "status"),
            ),
            ("ix_import_batch_expires_at", ("expires_at",)),
        },
        "import_batch_error": {
            (
                "ix_import_batch_error_batch_severity",
                ("batch_id", "severity"),
            ),
            ("ix_import_batch_error_batch_row", ("batch_id", "source_row_number")),
        },
        "punch_record": {
            (
                "ix_punch_record_company_employee_date",
                ("company_id", "employee_id", "attendance_date"),
            ),
            ("ix_punch_record_company_date", ("company_id", "attendance_date")),
            ("ix_punch_record_batch_id", ("batch_id",)),
        },
        "oa_trip": {
            (
                "ix_oa_trip_company_dates",
                ("company_id", "start_date", "end_date"),
            ),
            ("ix_oa_trip_batch_id", ("batch_id",)),
        },
        "oa_overtime": {
            ("ix_oa_overtime_company_range", ("company_id", "start_at", "end_at")),
            ("ix_oa_overtime_batch_id", ("batch_id",)),
        },
        "oa_overtime_day": {
            ("ix_oa_overtime_day_company_date", ("company_id", "work_date")),
            ("ix_oa_overtime_day_overtime_id", ("overtime_id",)),
        },
        "oa_leave": {
            (
                "ix_oa_leave_company_dates",
                ("company_id", "rest_start_date", "rest_end_date"),
            ),
            ("ix_oa_leave_batch_id", ("batch_id",)),
        },
        "attendance_day_result": {
            ("ix_attendance_day_result_company_date", ("company_id", "work_date")),
            (
                "ix_attendance_day_result_employee_date",
                ("employee_id", "work_date"),
            ),
            ("ix_attendance_day_result_calc_run", ("calc_run_id",)),
        },
        "attendance_day_shift_result": {
            ("ix_attendance_day_shift_result_calc_run", ("calc_run_id",)),
            (
                "ix_attendance_day_shift_result_employee_date",
                ("employee_id", "work_date"),
            ),
        },
        "attendance_month_summary": {
            ("ix_attendance_month_summary_calc_run", ("calc_run_id",)),
            (
                "ix_attendance_month_summary_company_employee",
                ("company_id", "employee_id"),
            ),
        },
    }
)

# name -> (columns, fragment that must appear in the normalized predicate)
PARTIAL_UNIQUE_INDEXES: dict[str, dict[str, tuple[tuple[str, ...], str]]] = {
    table: {} for table in ATTENDANCE_TABLES
}
PARTIAL_UNIQUE_INDEXES.update(
    {
        "import_batch": {
            "uq_import_batch_company_type_month_committed": (
                ("company_id", "data_type", "month"),
                "committed",
            )
        },
        "oa_trip": {
            "uq_oa_trip_batch_approval_employee": (
                ("batch_id", "approval_no", "employee_id"),
                "approval_no is not null",
            )
        },
        "oa_overtime": {
            "uq_oa_overtime_batch_approval_employee": (
                ("batch_id", "approval_no", "employee_id"),
                "approval_no is not null",
            )
        },
        "oa_leave": {
            "uq_oa_leave_batch_approval_employee": (
                ("batch_id", "approval_no", "employee_id"),
                "approval_no is not null",
            )
        },
        "attendance_result_adjustment": {
            "uq_attendance_result_adjustment_month_employee_date_active": (
                ("attendance_month_id", "employee_id", "work_date"),
                "active",
            )
        },
    }
)

_RULE_FIELDS: tuple[str, ...] = (
    "punch_window_min",
    "late_cap_min",
    "early_cap_min",
    "ot_max_min",
    "late_grace_min",
    "early_grace_min",
    "ot_threshold_min",
    "break_punch_tolerance_min",
    "absent_deduct_per_day",
    "late_deduct_per_occurrence",
    "early_deduct_per_occurrence",
    "missing_punch_deduct_per_occ",
)

CHECK_CONSTRAINTS: dict[str, set[str]] = {table: set() for table in ATTENDANCE_TABLES}
CHECK_CONSTRAINTS.update(
    {
        "shift": {
            "ck_shift_cross_day",
            "ck_shift_break_pair",
            "ck_shift_rest_minutes",
        },
        "holiday": {"ck_holiday_day_type"},
        "attendance_rule": {
            f"ck_attendance_rule_{field}_non_negative" for field in _RULE_FIELDS
        },
        "attendance_month": {"ck_attendance_month_status"},
        "calc_run": {"ck_calc_run_trigger", "ck_calc_run_status"},
        "schedule_plan": {
            "ck_schedule_plan_month_first_day",
            "ck_schedule_plan_scope_type",
            "ck_schedule_plan_status",
        },
        "plan_day": {
            "ck_plan_day_day_of_month_range",
            "ck_plan_day_seq_non_negative",
        },
        "plan_rule_override": {
            f"ck_plan_rule_override_{field}_non_negative" for field in _RULE_FIELDS
        },
        "roster_entry": {"ck_roster_entry_state", "ck_roster_entry_source"},
        "roster_entry_shift": {"ck_roster_entry_shift_seq_non_negative"},
        "import_batch": {
            "ck_import_batch_data_type",
            "ck_import_batch_month_first_day",
            "ck_import_batch_source",
            "ck_import_batch_status",
        },
        "import_batch_error": {"ck_import_batch_error_severity"},
        "import_mapping_template": {"ck_import_mapping_template_data_type"},
        "oa_overtime_day": {"ck_oa_overtime_day_minutes_range"},
        "oa_leave": {"ck_oa_leave_days_positive", "ck_oa_leave_leave_kind"},
        "attendance_day_result": {
            "ck_attendance_day_result_day_status",
            "ck_attendance_day_result_day_type",
            "ck_attendance_day_result_leave_kind",
            "ck_attendance_day_result_roster_state",
            "ck_attendance_day_result_trip_kind",
        },
        "attendance_day_shift_result": {"ck_attendance_day_shift_result_shift_status"},
        "attendance_result_adjustment": {"ck_attendance_result_adjustment_status"},
    }
)

ENUM_CHECK_VALUES: dict[str, dict[str, set[str]]] = {
    "holiday": {
        "ck_holiday_day_type": {"holiday", "adjusted_workday"},
    },
    "attendance_month": {
        "ck_attendance_month_status": {
            "draft",
            "calculated",
            "confirmed",
            "locked",
        },
    },
    "calc_run": {
        "ck_calc_run_trigger": {
            "initial",
            "manual",
            "reimport",
            "roster_change",
            "rule_change",
            "holiday_change",
        },
        "ck_calc_run_status": {"success", "failed"},
    },
    "schedule_plan": {
        "ck_schedule_plan_scope_type": {"all", "dept", "position", "employee"},
        "ck_schedule_plan_status": {"enabled", "archived"},
    },
    "roster_entry": {
        "ck_roster_entry_state": {"work", "rest"},
        "ck_roster_entry_source": {"plan", "manual"},
    },
    "import_batch": {
        "ck_import_batch_data_type": {"punch", "trip", "ot", "leave"},
        "ck_import_batch_status": {
            "preview",
            "committed",
            "superseded",
            "discarded",
            "revoked",
        },
        "ck_import_batch_source": {"upload", "paste"},
    },
    "import_batch_error": {
        "ck_import_batch_error_severity": {"error", "warning"},
    },
    "import_mapping_template": {
        "ck_import_mapping_template_data_type": {"punch", "trip", "ot", "leave"},
    },
    "oa_leave": {
        "ck_oa_leave_leave_kind": {"paid", "unpaid", "comp"},
    },
    "attendance_day_result": {
        "ck_attendance_day_result_day_type": {"workday", "weekend", "holiday"},
        "ck_attendance_day_result_roster_state": {"work", "rest", "unscheduled"},
        "ck_attendance_day_result_day_status": {
            "normal",
            "late",
            "early",
            "missing_punch",
            "absent",
            "overtime",
            "trip_out",
            "trip_business",
            "personal_leave",
            "paid_leave",
            "comp_leave",
            "rest",
            "unscheduled_attendance",
        },
        "ck_attendance_day_result_leave_kind": {"paid", "unpaid", "comp"},
        "ck_attendance_day_result_trip_kind": {"out", "business"},
    },
    "attendance_day_shift_result": {
        "ck_attendance_day_shift_result_shift_status": {
            "normal",
            "late",
            "early",
            "missing_punch",
            "absent",
            "overtime",
            "trip_out",
            "trip_business",
            "personal_leave",
            "paid_leave",
            "comp_leave",
            "rest",
            "unscheduled_attendance",
        },
    },
    "attendance_result_adjustment": {
        "ck_attendance_result_adjustment_status": {
            "active",
            "superseded",
            "orphaned",
        },
    },
}

FOREIGN_KEYS: dict[str, set[tuple[str, str, str, str | None]]] = {
    table: set() for table in ATTENDANCE_TABLES
}
FOREIGN_KEYS.update(
    {
        "shift": {("fk_shift_company_id_company", "company_id", "company", "RESTRICT")},
        "holiday": {
            ("fk_holiday_company_id_company", "company_id", "company", "RESTRICT")
        },
        "attendance_rule": {
            (
                "fk_attendance_rule_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "attendance_month": {
            (
                "fk_attendance_month_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "calc_run": {
            (
                "fk_calc_run_attendance_month_id_attendance_month",
                "attendance_month_id",
                "attendance_month",
                "CASCADE",
            )
        },
        "attendance_month_snapshot": {
            (
                "fk_attendance_month_snapshot_month_id_attendance_month",
                "attendance_month_id",
                "attendance_month",
                "CASCADE",
            ),
            (
                "fk_attendance_month_snapshot_calc_run_id_calc_run",
                "calc_run_id",
                "calc_run",
                "RESTRICT",
            ),
            (
                "fk_attendance_month_snapshot_locked_by_user",
                "locked_by",
                "user",
                "RESTRICT",
            ),
        },
        "schedule_plan": {
            (
                "fk_schedule_plan_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_schedule_plan_copied_from_plan_id_schedule_plan",
                "copied_from_plan_id",
                "schedule_plan",
                "SET NULL",
            ),
        },
        "plan_scope": {
            (
                "fk_plan_scope_plan_id_schedule_plan",
                "plan_id",
                "schedule_plan",
                "CASCADE",
            )
        },
        "plan_day": {
            (
                "fk_plan_day_plan_id_schedule_plan",
                "plan_id",
                "schedule_plan",
                "CASCADE",
            ),
            ("fk_plan_day_shift_id_shift", "shift_id", "shift", "RESTRICT"),
        },
        "plan_rule_override": {
            (
                "fk_plan_rule_override_plan_id_schedule_plan",
                "plan_id",
                "schedule_plan",
                "CASCADE",
            )
        },
        "roster_entry": {
            (
                "fk_roster_entry_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_roster_entry_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
            (
                "fk_roster_entry_plan_id_schedule_plan",
                "plan_id",
                "schedule_plan",
                "SET NULL",
            ),
        },
        "roster_entry_shift": {
            (
                "fk_roster_entry_shift_roster_entry_id_roster_entry",
                "roster_entry_id",
                "roster_entry",
                "CASCADE",
            ),
            (
                "fk_roster_entry_shift_shift_id_shift",
                "shift_id",
                "shift",
                "RESTRICT",
            ),
        },
        "import_batch": {
            (
                "fk_import_batch_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_import_batch_operator_id_user",
                "operator_id",
                "user",
                "RESTRICT",
            ),
            (
                "fk_import_batch_superseded_by_batch_id_import_batch",
                "superseded_by_batch_id",
                "import_batch",
                "SET NULL",
            ),
        },
        "import_batch_error": {
            (
                "fk_import_batch_error_batch_id_import_batch",
                "batch_id",
                "import_batch",
                "CASCADE",
            )
        },
        "import_mapping_template": {
            (
                "fk_import_mapping_template_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_import_mapping_template_updated_by_user",
                "updated_by",
                "user",
                "RESTRICT",
            ),
        },
        "punch_record": {
            (
                "fk_punch_record_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_punch_record_batch_id_import_batch",
                "batch_id",
                "import_batch",
                "CASCADE",
            ),
            (
                "fk_punch_record_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "oa_trip": {
            ("fk_oa_trip_company_id_company", "company_id", "company", "RESTRICT"),
            (
                "fk_oa_trip_batch_id_import_batch",
                "batch_id",
                "import_batch",
                "CASCADE",
            ),
            (
                "fk_oa_trip_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "oa_overtime": {
            (
                "fk_oa_overtime_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_oa_overtime_batch_id_import_batch",
                "batch_id",
                "import_batch",
                "CASCADE",
            ),
            (
                "fk_oa_overtime_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "oa_overtime_day": {
            (
                "fk_oa_overtime_day_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_oa_overtime_day_overtime_id_oa_overtime",
                "overtime_id",
                "oa_overtime",
                "CASCADE",
            ),
        },
        "oa_leave": {
            (
                "fk_oa_leave_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_oa_leave_batch_id_import_batch",
                "batch_id",
                "import_batch",
                "CASCADE",
            ),
            (
                "fk_oa_leave_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "attendance_day_result": {
            (
                "fk_attendance_day_result_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_attendance_day_result_attendance_month_id_attendance_month",
                "attendance_month_id",
                "attendance_month",
                "CASCADE",
            ),
            (
                "fk_attendance_day_result_calc_run_id_calc_run",
                "calc_run_id",
                "calc_run",
                "RESTRICT",
            ),
            (
                "fk_attendance_day_result_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "attendance_day_shift_result": {
            (
                "fk_attendance_day_shift_result_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_attendance_day_shift_result_day_id_attendance_day_result",
                "day_result_id",
                "attendance_day_result",
                "CASCADE",
            ),
            (
                "fk_attendance_day_shift_result_calc_run_id_calc_run",
                "calc_run_id",
                "calc_run",
                "RESTRICT",
            ),
            (
                "fk_attendance_day_shift_result_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "attendance_month_summary": {
            (
                "fk_attendance_month_summary_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_attendance_month_summary_month_id_attendance_month",
                "attendance_month_id",
                "attendance_month",
                "CASCADE",
            ),
            (
                "fk_attendance_month_summary_calc_run_id_calc_run",
                "calc_run_id",
                "calc_run",
                "RESTRICT",
            ),
            (
                "fk_attendance_month_summary_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "attendance_result_adjustment": {
            (
                "fk_attendance_result_adjustment_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_attendance_result_adjustment_month_id_attendance_month",
                "attendance_month_id",
                "attendance_month",
                "CASCADE",
            ),
            (
                "fk_attendance_result_adjustment_calc_run_id_calc_run",
                "calc_run_id",
                "calc_run",
                "RESTRICT",
            ),
            (
                "fk_attendance_result_adjustment_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
            (
                "fk_attendance_result_adjustment_adjusted_by_user",
                "adjusted_by",
                "user",
                "RESTRICT",
            ),
        },
    }
)


@pytest.fixture(scope="module")
def inspector() -> sa.Inspector:
    return sa.inspect(engine)


def test_all_attendance_tables_exist(inspector: sa.Inspector) -> None:
    tables = set(inspector.get_table_names())

    assert len(ATTENDANCE_TABLES) == 24
    assert set(ATTENDANCE_TABLES) <= tables


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_has_the_contract_columns(
    inspector: sa.Inspector, table_name: str
) -> None:
    columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    expected = COLUMNS[table_name]

    assert set(columns) == set(expected)
    for name, (type_check, nullable) in expected.items():
        column = columns[name]
        assert type_check(column["type"]), (
            f"{table_name}.{name} has type {column['type']!r}"
        )
        assert column["nullable"] is nullable, (
            f"{table_name}.{name} nullable is {column['nullable']}, expected {nullable}"
        )


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_primary_key(inspector: sa.Inspector, table_name: str) -> None:
    primary_key = inspector.get_pk_constraint(table_name)

    assert tuple(primary_key["constrained_columns"]) == PRIMARY_KEYS[table_name]


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_has_the_contract_unique_constraints(
    inspector: sa.Inspector, table_name: str
) -> None:
    unique_constraints = {
        (constraint["name"], tuple(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints(table_name)
    }

    assert unique_constraints == UNIQUE_CONSTRAINTS[table_name]


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_has_the_contract_indexes(
    inspector: sa.Inspector, table_name: str
) -> None:
    # PostgreSQL reports indexes backing unique constraints here too; those
    # constraints are asserted by the unique-constraint test.
    indexes = [
        index
        for index in inspector.get_indexes(table_name)
        if index.get("duplicates_constraint") is None
    ]
    plain = {
        (index["name"], tuple(index["column_names"]))
        for index in indexes
        if not index["unique"]
    }
    partial = {
        index["name"]: (
            tuple(index["column_names"]),
            " ".join(
                str(index.get("dialect_options", {}).get("postgresql_where", ""))
                .lower()
                .split()
            ),
        )
        for index in indexes
        if index["unique"]
    }

    assert plain == PLAIN_INDEXES[table_name]
    assert set(partial) == set(PARTIAL_UNIQUE_INDEXES[table_name])
    for name, (columns, predicate_fragment) in PARTIAL_UNIQUE_INDEXES[
        table_name
    ].items():
        assert partial[name][0] == columns
        assert predicate_fragment in partial[name][1], (
            f"{table_name}.{name} predicate is {partial[name][1]!r}"
        )


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_has_the_contract_check_constraints(
    inspector: sa.Inspector, table_name: str
) -> None:
    check_constraints = {
        constraint["name"] for constraint in inspector.get_check_constraints(table_name)
    }

    assert check_constraints == CHECK_CONSTRAINTS[table_name]


def _enum_check_definitions(table_name: str) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                """
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = to_regclass(:table_name) AND contype = 'c'
                """
            ),
            {"table_name": table_name},
        ).all()
    return dict(rows)


def test_enum_checks_have_the_contract_vocabulary() -> None:
    for table_name, checks in ENUM_CHECK_VALUES.items():
        definitions = _enum_check_definitions(table_name)
        for constraint_name, expected_values in checks.items():
            definition = definitions[constraint_name]
            actual_values = set(re.findall(r"'([^']*)'", definition))
            assert actual_values == expected_values, (
                table_name,
                constraint_name,
                definition,
            )


@pytest.mark.parametrize("table_name", ATTENDANCE_TABLES)
def test_table_has_the_contract_foreign_keys(
    inspector: sa.Inspector, table_name: str
) -> None:
    foreign_keys = {
        (
            foreign_key["name"],
            foreign_key["constrained_columns"][0],
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in inspector.get_foreign_keys(table_name)
    }

    assert foreign_keys == FOREIGN_KEYS[table_name]


@pytest.fixture(scope="module")
def tables() -> dict[str, sa.Table]:
    metadata = sa.MetaData()
    return {
        name: sa.Table(name, metadata, autoload_with=engine)
        for name in (*ATTENDANCE_TABLES, "company")
    }


def _base_row() -> dict[str, Any]:
    now = datetime.now(UTC)
    return {"id": uuid.uuid7(), "created_at": now, "updated_at": now}


def _created_row() -> dict[str, Any]:
    return {"id": uuid.uuid7(), "created_at": datetime.now(UTC)}


def _id_row() -> dict[str, Any]:
    return {"id": uuid.uuid7()}


def _superuser_id(db: Session) -> uuid.UUID:
    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()
    return user.id


def _insert(
    db: Session, tables: dict[str, sa.Table], table_name: str, row: dict[str, Any]
) -> uuid.UUID:
    db.execute(sa.insert(tables[table_name]).values(**row))
    db.commit()
    return row["id"]


@contextmanager
def _integrity_error(db: Session) -> Iterator[None]:
    try:
        with pytest.raises(IntegrityError):
            yield
    finally:
        db.rollback()


def test_core_cascade_and_restrict_foreign_keys(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    from tests.utils.factories import create_company

    company = create_company(db)
    month = _insert(
        db,
        tables,
        "attendance_month",
        {
            **_base_row(),
            "company_id": company.id,
            "month": date(2026, 9, 1),
            "status": "draft",
            "is_stale": True,
            "calculated_at": None,
            "confirmed_at": None,
            "locked_at": None,
            "unlock_reason": None,
        },
    )
    calc_run = _insert(
        db,
        tables,
        "calc_run",
        {
            **_id_row(),
            "attendance_month_id": month,
            "trigger": "manual",
            "status": "success",
            "calc_version": "attendance-calc-v1",
            "rules_version": "rules",
            "roster_version": "roster",
            "rules_snapshot": {},
            "input_batches": {},
            "summary": None,
            "error_code": None,
            "error_message": None,
            "started_at": datetime.now(UTC),
            "finished_at": datetime.now(UTC),
        },
    )
    snapshot = _insert(
        db,
        tables,
        "attendance_month_snapshot",
        {
            **_id_row(),
            "attendance_month_id": month,
            "calc_run_id": calc_run,
            "version": 1,
            "locked_at": datetime.now(UTC),
            "locked_by": _superuser_id(db),
            "payload": {},
        },
    )

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["calc_run"]).where(tables["calc_run"].c.id == calc_run)
        )
        db.commit()

    db.execute(
        sa.delete(tables["attendance_month"]).where(
            tables["attendance_month"].c.id == month
        )
    )
    db.commit()

    for table_name, row_id in (
        ("attendance_month_snapshot", snapshot),
        ("calc_run", calc_run),
    ):
        assert (
            db.execute(
                sa.select(tables[table_name].c.id).where(
                    tables[table_name].c.id == row_id
                )
            ).first()
            is None
        )


def test_import_children_cascade_with_their_batch(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    from tests.utils.factories import create_company

    company = create_company(db)
    batch = _insert(
        db,
        tables,
        "import_batch",
        {
            **_created_row(),
            "company_id": company.id,
            "data_type": "punch",
            "month": date(2026, 9, 1),
            "status": "preview",
            "source": "upload",
            "file_name": "punch.csv",
            "file_size": 10,
            "file_sha256": "hash",
            "sheet_name": None,
            "header_row_number": 1,
            "header_columns": [],
            "column_mapping": {},
            "parser_version": "attendance-import-v1",
            "source_rows": 0,
            "valid_records": 0,
            "skipped_records": 0,
            "error_records": 0,
            "warning_records": 0,
            "skip_counts": {},
            "warning_counts": {},
            "operator_id": _superuser_id(db),
            "committed_at": None,
            "superseded_at": None,
            "discarded_at": None,
            "revoked_at": None,
            "expires_at": None,
            "superseded_by_batch_id": None,
            "discard_reason": None,
        },
    )
    error_id = _insert(
        db,
        tables,
        "import_batch_error",
        {
            **_created_row(),
            "batch_id": batch,
            "source_row_number": 2,
            "column_name": None,
            "code": "unknown_employee",
            "message": "员工不存在",
            "severity": "error",
            "raw_row": {},
        },
    )

    db.execute(
        sa.delete(tables["import_batch"]).where(tables["import_batch"].c.id == batch)
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["import_batch_error"].c.id).where(
                tables["import_batch_error"].c.id == error_id
            )
        ).first()
        is None
    )


def test_roster_plan_reference_is_nulled_on_plan_delete(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    from tests.utils.factories import (
        create_company,
        create_department,
        create_employee,
        create_position,
    )

    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(db, dept=department, position=position)
    plan = _insert(
        db,
        tables,
        "schedule_plan",
        {
            **_base_row(),
            "company_id": company.id,
            "month": date(2026, 9, 1),
            "plan_name": "行政班",
            "scope_type": "all",
            "status": "enabled",
            "copied_from_plan_id": None,
            "note": None,
        },
    )
    entry = _insert(
        db,
        tables,
        "roster_entry",
        {
            **_base_row(),
            "company_id": company.id,
            "employee_id": employee.id,
            "work_date": date(2026, 9, 1),
            "state": "work",
            "source": "plan",
            "plan_id": plan,
            "note": None,
        },
    )

    db.execute(
        sa.delete(tables["schedule_plan"]).where(tables["schedule_plan"].c.id == plan)
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["roster_entry"].c.plan_id).where(
                tables["roster_entry"].c.id == entry
            )
        ).scalar_one()
        is None
    )


def test_company_delete_is_restricted_by_attendance_data(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    from tests.utils.factories import create_company

    company = create_company(db)
    _insert(
        db,
        tables,
        "shift",
        {
            **_base_row(),
            "company_id": company.id,
            "shift_code": "ADM",
            "shift_name": "行政班",
            "start_time": time(8, 30),
            "end_time": time(17, 30),
            "cross_day": False,
            "break_start": None,
            "break_end": None,
            "rest_minutes": 60,
            "color": None,
            "note": None,
            "is_active": True,
        },
    )

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["company"]).where(tables["company"].c.id == company.id)
        )
        db.commit()


def test_enum_and_range_checks_reject_invalid_values(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    from tests.utils.factories import create_company

    company = create_company(db)

    with _integrity_error(db):
        _insert(
            db,
            tables,
            "attendance_month",
            {
                **_base_row(),
                "company_id": company.id,
                "month": date(2026, 9, 1),
                "status": "drafting",
                "is_stale": True,
                "calculated_at": None,
                "confirmed_at": None,
                "locked_at": None,
                "unlock_reason": None,
            },
        )

    with _integrity_error(db):
        _insert(
            db,
            tables,
            "attendance_rule",
            {
                **_base_row(),
                "company_id": company.id,
                "punch_window_min": -1,
                "late_cap_min": 240,
                "early_cap_min": 240,
                "ot_max_min": 600,
                "late_grace_min": 5,
                "early_grace_min": 5,
                "ot_threshold_min": 30,
                "absent_if_no_punch": True,
                "break_punch_required": True,
                "break_punch_tolerance_min": 60,
                "absent_deduct_per_day": Decimal("0"),
                "late_deduct_per_occurrence": Decimal("0"),
                "early_deduct_per_occurrence": Decimal("0"),
                "missing_punch_deduct_per_occurrence": Decimal("0"),
            },
        )
