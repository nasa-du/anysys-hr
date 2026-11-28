"""Schema contract for the Payroll persistence foundation.

These tests reflect the migrated PostgreSQL database. The migrations are the
deliverable, so the assertions are written from the approved specification in
``docs/specs/payroll-management.md`` (sections 4.1-4.25 and 16) rather than
from the SQLModel metadata.
"""

import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.enums import PayrollGlobalParamType
from app.models import (
    Company,
    Department,
    Employee,
    PayrollGlobalParam,
    Position,
    User,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.payroll_tables import (
    PAYROLL_CONFIG_TABLES,
    PAYROLL_EXPORT_TABLES,
    PAYROLL_INPUT_TABLES,
    PAYROLL_MONTH_TABLES,
    PAYROLL_TABLES,
)

ColumnCheck = tuple[Callable[[sa.types.TypeEngine[Any]], bool], bool]


def _uuid_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Uuid) and value.as_uuid


def _varchar(length: int) -> Callable[[sa.types.TypeEngine[Any]], bool]:
    def check(value: sa.types.TypeEngine[Any]) -> bool:
        return isinstance(value, sa.String) and value.length == length

    return check


def _text_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Text)


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


def _integer_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.Integer) and not isinstance(value, sa.BigInteger)


def _bigint_type(value: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(value, sa.BigInteger)


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

_COMPOSITION_AMOUNTS = {
    "base_salary": (_numeric(14, 2), False),
    "hightemp_subsidy": (_numeric(14, 2), False),
    "performance_salary": (_numeric(14, 2), False),
    "overtime_pay": (_numeric(14, 2), False),
    "confidentiality_allowance": (_numeric(14, 2), False),
    "social_subsidy": (_numeric(14, 2), False),
    "noncompete_subsidy": (_numeric(14, 2), False),
}


COLUMNS: dict[str, dict[str, ColumnCheck]] = {
    "salary_field_def": {
        "id": _ID,
        "field_key": _text(64),
        "label": _text(100),
        "category": _text(16),
        "calc_mode": _text(16),
        "source_key": _text(64, nullable=True),
        "fixed_value": (_numeric(18, 4), True),
        "default_formula": (_text_type, True),
        "display_order": (_integer_type, False),
        "visible": (_boolean_type, False),
        "is_system": (_boolean_type, False),
        "is_active": (_boolean_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "compensation_composition": {
        "id": _ID,
        "company_id": _uuid(),
        "comp_code": _text(32),
        "comp_name": _text(100),
        "is_active": (_boolean_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "compensation_composition_version": {
        "id": _ID,
        "comp_id": _uuid(),
        "version_no": (_integer_type, False),
        **_COMPOSITION_AMOUNTS,
        "total_package": (_numeric(14, 2), False),
        "change_note": _text(500, nullable=True),
        "created_by": _uuid(nullable=True),
        "created_by_name": _text(100, nullable=True),
        "created_at": _CREATED,
    },
    "workday_param": {
        "id": _ID,
        "company_id": _uuid(),
        "workday_code": _text(32),
        "workday_name": _text(100),
        "avg_pay_days": (_numeric(5, 2), False),
        "work_hours": (_numeric(4, 2), False),
        "ot_mult_weekday": (_numeric(4, 2), False),
        "ot_mult_weekend": (_numeric(4, 2), False),
        "ot_mult_holiday": (_numeric(4, 2), False),
        "min_wage": (_numeric(14, 2), False),
        "min_wage_note": _text(500, nullable=True),
        "is_active": (_boolean_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "calc_scheme": {
        "id": _ID,
        "company_id": _uuid(),
        "calc_code": _text(32),
        "calc_name": _text(100),
        "is_active": (_boolean_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "calc_scheme_formula": {
        "id": _ID,
        "calc_scheme_id": _uuid(),
        "field_def_id": _uuid(),
        "formula_expr": (_text_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "position_payroll_config": {
        "id": _ID,
        "position_id": _uuid(),
        "comp_id": _uuid(),
        "calc_scheme_id": _uuid(),
        "workday_param_id": _uuid(),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_global_param": {
        "id": _ID,
        "key": _text(64),
        "label": _text(100),
        "category": _text(32),
        "value_type": _text(16),
        "numeric_value": (_numeric(18, 6), True),
        "json_value": (_jsonb_type, True),
        "display_order": (_integer_type, False),
        "is_active": (_boolean_type, False),
        "note": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_config_revision": {
        "id": _ID,
        "entity_type": _text(32),
        "entity_id": _uuid(),
        "version_no": (_integer_type, False),
        "snapshot": (_jsonb_type, False),
        "change_note": _text(500, nullable=True),
        "changed_by": _uuid(nullable=True),
        "changed_by_name": _text(100, nullable=True),
        "changed_at": _timestamp(),
    },
    "payroll_month": {
        "id": _ID,
        "company_id": _uuid(),
        "month": (_date_type, False),
        "status": _text(16),
        "input_version": (_integer_type, False),
        "config_stale": (_boolean_type, False),
        "config_stale_detail": (_jsonb_type, True),
        "calculated_at": _timestamp(nullable=True),
        "confirmed_at": _timestamp(nullable=True),
        "paid_at": _timestamp(nullable=True),
        "unlock_reason": _text(500, nullable=True),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_calc_run": {
        "id": _ID,
        "payroll_month_id": _uuid(),
        "trigger": _text(24),
        "status": _text(16),
        "config_snapshot_version": (_integer_type, False),
        "config_snapshot": (_jsonb_type, False),
        "input_version": (_integer_type, False),
        "input_snapshot": (_jsonb_type, False),
        "attendance_month_id": _uuid(nullable=True),
        "attendance_snapshot_id": _uuid(nullable=True),
        "attendance_snapshot_version": (_integer_type, True),
        "attendance_calc_run_id": _uuid(nullable=True),
        "calc_version": _text(32, nullable=True),
        "rules_version": _text(64, nullable=True),
        "attendance_locked_at": _timestamp(nullable=True),
        "summary": (_jsonb_type, True),
        "error_code": _text(50, nullable=True),
        "error_message": _text(500, nullable=True),
        "triggered_by": _uuid(nullable=True),
        "triggered_by_name": _text(100, nullable=True),
        "started_at": _timestamp(),
        "finished_at": _timestamp(nullable=True),
    },
    "payroll_result": {
        "id": _ID,
        "payroll_month_id": _uuid(),
        "calc_run_id": _uuid(),
        "company_id": _uuid(),
        "employee_id": _uuid(),
        "position_id": _uuid(),
        "dept_id": _uuid(),
        "cost_org_id": _uuid(nullable=True),
        "calc_scheme_id": _uuid(),
        "position_code": _text(32),
        "position_name": _text(100),
        "dept_code": _text(32),
        "dept_name": _text(100),
        "cost_org_code": _text(32, nullable=True),
        "cost_org_name": _text(100, nullable=True),
        "dept_path": (_jsonb_type, False),
        "cost_org_path": (_jsonb_type, False),
        "attendance_source": (_jsonb_type, False),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_result_value": {
        "id": _ID,
        "result_id": _uuid(),
        "field_def_id": _uuid(),
        "value": (_numeric(18, 4), False),
        "source": _text(16),
        "produced_by_run_id": _uuid(),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_month_snapshot": {
        "id": _ID,
        "payroll_month_id": _uuid(),
        "calc_run_id": _uuid(),
        "version": (_integer_type, False),
        "paid_at": _timestamp(),
        "paid_by": _uuid(),
        "paid_by_name": _text(100),
        "payload": (_jsonb_type, False),
    },
    "payroll_month_event": {
        "id": _ID,
        "payroll_month_id": _uuid(),
        "event": _text(16),
        "from_status": _text(16),
        "to_status": _text(16),
        "calc_run_id": _uuid(nullable=True),
        "snapshot_id": _uuid(nullable=True),
        "reason": _text(500, nullable=True),
        "operator_id": _uuid(nullable=True),
        "operator_name": _text(100, nullable=True),
        "created_at": _timestamp(),
    },
    "payroll_month_input": {
        "id": _ID,
        "payroll_month_id": _uuid(),
        "employee_id": _uuid(),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_input_value": {
        "id": _ID,
        "input_id": _uuid(),
        "field_def_id": _uuid(),
        "value": (_numeric(18, 4), False),
        "source": _text(16),
        "source_batch_id": _uuid(nullable=True),
        "updated_by": _uuid(nullable=True),
        "updated_by_name": _text(100, nullable=True),
        "updated_at": _timestamp(),
    },
    "payroll_import_batch": {
        "id": _ID,
        "company_id": _uuid(),
        "month": (_date_type, False),
        "status": _text(16),
        "source": _text(16),
        "file_name": _text(255, nullable=True),
        "file_size": (_integer_type, True),
        "file_sha256": _text(64, nullable=True),
        "sheet_name": _text(100, nullable=True),
        "header_row_number": (_integer_type, True),
        "header_columns": (_jsonb_type, True),
        "column_mapping": (_jsonb_type, True),
        "parser_version": _text(32),
        "source_rows": (_integer_type, False),
        "valid_records": (_integer_type, False),
        "error_records": (_integer_type, False),
        "warning_records": (_integer_type, False),
        "warning_counts": (_jsonb_type, True),
        "operator_id": _uuid(nullable=True),
        "operator_name": _text(100, nullable=True),
        "created_at": _timestamp(),
        "committed_at": _timestamp(nullable=True),
        "superseded_at": _timestamp(nullable=True),
        "discarded_at": _timestamp(nullable=True),
        "expires_at": _timestamp(nullable=True),
        "superseded_by_batch_id": _uuid(nullable=True),
        "discard_reason": _text(500, nullable=True),
        "payroll_month_id": _uuid(nullable=True),
    },
    "payroll_import_batch_row": {
        "id": _ID,
        "batch_id": _uuid(),
        "source_row_number": (_integer_type, False),
        "employee_id": _uuid(nullable=True),
        "employee_no_raw": _text(64, nullable=True),
        "values": (_jsonb_type, True),
        "status": _text(16),
        "error_code": _text(50, nullable=True),
        "error_message": _text(500, nullable=True),
        "warnings": (_jsonb_type, True),
        "raw_row": (_jsonb_type, True),
    },
    "payroll_import_mapping_template": {
        "id": _ID,
        "company_id": _uuid(),
        "column_mapping": (_jsonb_type, False),
        "created_at": _CREATED,
        "updated_at": _UPDATED,
    },
    "payroll_export": {
        "id": _ID,
        "company_id": _uuid(),
        "month": (_date_type, False),
        "export_type": _text(32),
        "format": _text(8),
        "mode": _text(16, nullable=True),
        "snapshot_id": _uuid(nullable=True),
        "snapshot_version": (_integer_type, True),
        "calc_run_id": _uuid(nullable=True),
        "month_status_at_creation": _text(16, nullable=True),
        "filter": (_jsonb_type, True),
        "filter_hash": _text(64, nullable=True),
        "employee_count": (_integer_type, False),
        "status": _text(16),
        "progress_done": (_integer_type, False),
        "progress_total": (_integer_type, False),
        "error_code": _text(50, nullable=True),
        "error_message": _text(500, nullable=True),
        "created_at": _timestamp(),
        "started_at": _timestamp(nullable=True),
        "finished_at": _timestamp(nullable=True),
        "artifact_path": _text(500, nullable=True),
        "artifact_size": (_bigint_type, True),
        "expires_at": _timestamp(nullable=True),
        "artifact_deleted_at": _timestamp(nullable=True),
        "operator_id": _uuid(nullable=True),
        "operator_name": _text(100, nullable=True),
        "template_version": _text(32, nullable=True),
        "download_count": (_integer_type, False),
        "last_downloaded_by": _uuid(nullable=True),
        "last_downloaded_by_name": _text(100, nullable=True),
        "last_downloaded_at": _timestamp(nullable=True),
    },
}

PRIMARY_KEYS: dict[str, tuple[str, ...]] = dict.fromkeys(PAYROLL_TABLES, ("id",))

UNIQUE_CONSTRAINTS: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    table: set() for table in PAYROLL_TABLES
}
UNIQUE_CONSTRAINTS.update(
    {
        "salary_field_def": {
            ("uq_salary_field_def_field_key", ("field_key",)),
            ("uq_salary_field_def_label", ("label",)),
        },
        "compensation_composition": {
            (
                "uq_compensation_composition_company_comp_code",
                ("company_id", "comp_code"),
            )
        },
        "compensation_composition_version": {
            (
                "uq_compensation_composition_version_comp_version",
                ("comp_id", "version_no"),
            )
        },
        "workday_param": {
            (
                "uq_workday_param_company_workday_code",
                ("company_id", "workday_code"),
            )
        },
        "calc_scheme": {
            ("uq_calc_scheme_company_calc_code", ("company_id", "calc_code"))
        },
        "calc_scheme_formula": {
            (
                "uq_calc_scheme_formula_scheme_field",
                ("calc_scheme_id", "field_def_id"),
            )
        },
        "position_payroll_config": {
            (
                "uq_position_payroll_config_position_id",
                ("position_id",),
            )
        },
        "payroll_global_param": {
            ("uq_payroll_global_param_key", ("key",)),
        },
        "payroll_config_revision": {
            (
                "uq_payroll_config_revision_entity_version",
                ("entity_type", "entity_id", "version_no"),
            )
        },
        "payroll_month": {("uq_payroll_month_company_month", ("company_id", "month"))},
        "payroll_result": {
            (
                "uq_payroll_result_month_employee",
                ("payroll_month_id", "employee_id"),
            )
        },
        "payroll_result_value": {
            (
                "uq_payroll_result_value_result_field",
                ("result_id", "field_def_id"),
            )
        },
        "payroll_month_snapshot": {
            (
                "uq_payroll_month_snapshot_month_version",
                ("payroll_month_id", "version"),
            )
        },
        "payroll_month_input": {
            (
                "uq_payroll_month_input_month_employee",
                ("payroll_month_id", "employee_id"),
            )
        },
        "payroll_input_value": {
            (
                "uq_payroll_input_value_input_field",
                ("input_id", "field_def_id"),
            )
        },
        "payroll_import_mapping_template": {
            (
                "uq_payroll_import_mapping_template_company",
                ("company_id",),
            )
        },
    }
)

PLAIN_INDEXES: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    table: set() for table in PAYROLL_TABLES
}
PLAIN_INDEXES.update(
    {
        "salary_field_def": {
            (
                "ix_salary_field_def_category_display_order",
                ("category", "display_order"),
            )
        },
        "compensation_composition": {
            (
                "ix_compensation_composition_company_active",
                ("company_id", "is_active"),
            )
        },
        "calc_scheme_formula": {
            ("ix_calc_scheme_formula_field_def_id", ("field_def_id",))
        },
        "position_payroll_config": {
            ("ix_position_payroll_config_comp_id", ("comp_id",)),
            ("ix_position_payroll_config_calc_scheme_id", ("calc_scheme_id",)),
            (
                "ix_position_payroll_config_workday_param_id",
                ("workday_param_id",),
            ),
        },
        "payroll_calc_run": {
            ("ix_payroll_calc_run_status", ("status",)),
        },
        "payroll_result": {
            ("ix_payroll_result_month_dept_id", ("payroll_month_id", "dept_id")),
            (
                "ix_payroll_result_month_position_id",
                ("payroll_month_id", "position_id"),
            ),
            (
                "ix_payroll_result_month_cost_org_id",
                ("payroll_month_id", "cost_org_id"),
            ),
            (
                "ix_payroll_result_month_cost_org_code",
                ("payroll_month_id", "cost_org_code"),
            ),
            (
                "ix_payroll_result_company_dept_code",
                ("company_id", "dept_code"),
            ),
            (
                "ix_payroll_result_company_cost_org_code",
                ("company_id", "cost_org_code"),
            ),
        },
        "payroll_result_value": {
            ("ix_payroll_result_value_field_def_id", ("field_def_id",)),
            ("ix_payroll_result_value_produced_by_run_id", ("produced_by_run_id",)),
        },
        "payroll_month_input": {
            ("ix_payroll_month_input_employee_id", ("employee_id",))
        },
        "payroll_input_value": {
            ("ix_payroll_input_value_field_def_id", ("field_def_id",)),
            ("ix_payroll_input_value_source_batch_id", ("source_batch_id",)),
        },
        "payroll_import_batch_row": {
            (
                "ix_payroll_import_batch_row_batch_status",
                ("batch_id", "status"),
            ),
            (
                "ix_payroll_import_batch_row_batch_row",
                ("batch_id", "source_row_number"),
            ),
        },
        "payroll_export": {
            ("ix_payroll_export_status_created_at", ("status", "created_at")),
            ("ix_payroll_export_expires_at", ("expires_at",)),
        },
    }
)

# name -> (columns, fragment that must appear in the normalized predicate)
PARTIAL_UNIQUE_INDEXES: dict[str, dict[str, tuple[tuple[str, ...], str]]] = {
    table: {} for table in PAYROLL_TABLES
}
PARTIAL_UNIQUE_INDEXES.update(
    {
        "salary_field_def": {
            "uq_salary_field_def_source_key": (
                ("source_key",),
                "source_key is not null",
            )
        },
        "payroll_import_batch": {
            "uq_payroll_import_batch_company_month_committed": (
                ("company_id", "month"),
                "committed",
            )
        },
    }
)

# Descending indexes cannot be asserted through the inspector's column list.
DESC_INDEX_FRAGMENTS: dict[str, str] = {
    "ix_payroll_config_revision_entity": "changed_at DESC",
    "ix_payroll_calc_run_month_started_at": "started_at DESC",
    "ix_payroll_month_event_month_created_at": "created_at DESC",
    "ix_payroll_import_batch_company_month_status_created_at": "created_at DESC",
    "ix_payroll_export_company_month_created_at": "created_at DESC",
}

GIN_INDEXES: dict[str, str] = {
    "ix_payroll_result_dept_path_gin": "dept_path",
    "ix_payroll_result_cost_org_path_gin": "cost_org_path",
}

_COMPOSITION_CHECK_FIELDS = (
    "base_salary",
    "hightemp_subsidy",
    "performance_salary",
    "overtime_pay",
    "confidentiality_allowance",
    "social_subsidy",
    "noncompete_subsidy",
)

CHECK_CONSTRAINTS: dict[str, set[str]] = {table: set() for table in PAYROLL_TABLES}
CHECK_CONSTRAINTS.update(
    {
        "salary_field_def": {
            "ck_salary_field_def_field_key_pattern",
            "ck_salary_field_def_category",
            "ck_salary_field_def_calc_mode",
        },
        "compensation_composition": {"ck_compensation_composition_comp_code_pattern"},
        "compensation_composition_version": {
            "ck_comp_ver_version_positive",
            *(
                f"ck_comp_ver_{field}_non_negative"
                for field in _COMPOSITION_CHECK_FIELDS
            ),
            "ck_comp_ver_total_package_sum",
        },
        "workday_param": {
            "ck_workday_param_workday_code_pattern",
            "ck_workday_param_avg_pay_days_positive",
            "ck_workday_param_work_hours_positive",
            "ck_workday_param_ot_mult_weekday_min",
            "ck_workday_param_ot_mult_weekend_min",
            "ck_workday_param_ot_mult_holiday_min",
            "ck_workday_param_min_wage_non_negative",
        },
        "calc_scheme": {"ck_calc_scheme_calc_code_pattern"},
        "payroll_global_param": {
            "ck_payroll_global_param_value_type",
            "ck_payroll_global_param_value_exclusive",
        },
        "payroll_config_revision": {
            "ck_payroll_config_revision_entity_type",
            "ck_payroll_config_revision_version_positive",
        },
        "payroll_month": {
            "ck_payroll_month_first_day",
            "ck_payroll_month_status",
            "ck_payroll_month_input_version_non_negative",
        },
        "payroll_calc_run": {
            "ck_payroll_calc_run_trigger",
            "ck_payroll_calc_run_status",
        },
        "payroll_result_value": {"ck_payroll_result_value_source"},
        "payroll_month_snapshot": {"ck_payroll_month_snapshot_version_positive"},
        "payroll_month_event": {"ck_payroll_month_event_event"},
        "payroll_input_value": {"ck_payroll_input_value_source"},
        "payroll_import_batch": {
            "ck_payroll_import_batch_status",
            "ck_payroll_import_batch_source",
            "ck_payroll_import_batch_month_first_day",
            "ck_payroll_import_batch_source_rows_non_negative",
            "ck_payroll_import_batch_valid_records_non_negative",
            "ck_payroll_import_batch_error_records_non_negative",
            "ck_payroll_import_batch_warning_records_non_negative",
        },
        "payroll_import_batch_row": {
            "ck_payroll_import_batch_row_status",
            "ck_payroll_import_batch_row_source_row_number_positive",
        },
        "payroll_export": {
            "ck_payroll_export_status",
            "ck_payroll_export_export_type",
            "ck_payroll_export_month_first_day",
            "ck_payroll_export_employee_count_non_negative",
            "ck_payroll_export_progress_done_non_negative",
            "ck_payroll_export_progress_total_non_negative",
            "ck_payroll_export_download_count_non_negative",
        },
    }
)

ENUM_CHECK_VALUES: dict[str, dict[str, set[str]]] = {
    "salary_field_def": {
        "ck_salary_field_def_category": {
            "earning",
            "addon",
            "deduction",
            "total",
            "reference",
        },
        "ck_salary_field_def_calc_mode": {"plan", "import", "formula", "fixed"},
    },
    "payroll_global_param": {
        "ck_payroll_global_param_value_type": {"number", "json"},
    },
    "payroll_config_revision": {
        "ck_payroll_config_revision_entity_type": {
            "compensation_composition",
            "calc_scheme",
            "workday_param",
            "salary_field_def",
            "payroll_global_param",
            "position_payroll_config",
        }
    },
    "payroll_month": {
        "ck_payroll_month_status": {
            "draft",
            "calculated",
            "confirmed",
            "paid",
        }
    },
    "payroll_calc_run": {
        "ck_payroll_calc_run_trigger": {
            "initial",
            "manual",
            "attendance_refresh",
        },
        "ck_payroll_calc_run_status": {"running", "succeeded", "failed"},
    },
    "payroll_result_value": {
        "ck_payroll_result_value_source": {
            "plan",
            "import",
            "formula",
            "fixed",
            "manual",
        }
    },
    "payroll_month_event": {
        "ck_payroll_month_event_event": {
            "confirmed",
            "unconfirmed",
            "paid",
            "unlocked",
        }
    },
    "payroll_input_value": {"ck_payroll_input_value_source": {"import", "manual"}},
    "payroll_import_batch": {
        "ck_payroll_import_batch_status": {
            "preview",
            "committed",
            "superseded",
            "discarded",
        },
        "ck_payroll_import_batch_source": {"upload", "paste"},
    },
    "payroll_import_batch_row": {
        "ck_payroll_import_batch_row_status": {"valid", "error", "skipped"}
    },
    "payroll_export": {
        "ck_payroll_export_export_type": {
            "payslip_single",
            "payslip_zip",
            "payslip_merged",
            "payroll_detail_xlsx",
            "department_summary_xlsx",
        },
        "ck_payroll_export_status": {
            "queued",
            "running",
            "succeeded",
            "failed",
            "expired",
        },
    },
}

FOREIGN_KEYS: dict[str, set[tuple[str, str, str, str | None]]] = {
    table: set() for table in PAYROLL_TABLES
}
FOREIGN_KEYS.update(
    {
        "compensation_composition": {
            (
                "fk_compensation_composition_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "compensation_composition_version": {
            (
                "fk_comp_version_comp_id_compensation_composition",
                "comp_id",
                "compensation_composition",
                "RESTRICT",
            ),
            (
                "fk_compensation_composition_version_created_by_user",
                "created_by",
                "user",
                "RESTRICT",
            ),
        },
        "workday_param": {
            (
                "fk_workday_param_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "calc_scheme": {
            (
                "fk_calc_scheme_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "calc_scheme_formula": {
            (
                "fk_calc_scheme_formula_calc_scheme_id_calc_scheme",
                "calc_scheme_id",
                "calc_scheme",
                "CASCADE",
            ),
            (
                "fk_calc_scheme_formula_field_def_id_salary_field_def",
                "field_def_id",
                "salary_field_def",
                "RESTRICT",
            ),
        },
        "position_payroll_config": {
            (
                "fk_position_payroll_config_position_id_position",
                "position_id",
                "position",
                "CASCADE",
            ),
            (
                "fk_position_payroll_config_comp_id_compensation_composition",
                "comp_id",
                "compensation_composition",
                "RESTRICT",
            ),
            (
                "fk_position_payroll_config_calc_scheme_id_calc_scheme",
                "calc_scheme_id",
                "calc_scheme",
                "RESTRICT",
            ),
            (
                "fk_position_payroll_config_workday_param_id_workday_param",
                "workday_param_id",
                "workday_param",
                "RESTRICT",
            ),
        },
        "payroll_config_revision": {
            (
                "fk_payroll_config_revision_changed_by_user",
                "changed_by",
                "user",
                "RESTRICT",
            )
        },
        "payroll_month": {
            (
                "fk_payroll_month_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            )
        },
        "payroll_calc_run": {
            (
                "fk_payroll_calc_run_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "CASCADE",
            ),
            (
                "fk_payroll_calc_run_triggered_by_user",
                "triggered_by",
                "user",
                "RESTRICT",
            ),
        },
        "payroll_result": {
            (
                "fk_payroll_result_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "CASCADE",
            ),
            (
                "fk_payroll_result_calc_run_id_payroll_calc_run",
                "calc_run_id",
                "payroll_calc_run",
                "CASCADE",
            ),
            (
                "fk_payroll_result_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_payroll_result_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
            (
                "fk_payroll_result_calc_scheme_id_calc_scheme",
                "calc_scheme_id",
                "calc_scheme",
                "RESTRICT",
            ),
        },
        "payroll_result_value": {
            (
                "fk_payroll_result_value_result_id_payroll_result",
                "result_id",
                "payroll_result",
                "CASCADE",
            ),
            (
                "fk_payroll_result_value_field_def_id_salary_field_def",
                "field_def_id",
                "salary_field_def",
                "RESTRICT",
            ),
            (
                "fk_payroll_result_value_produced_by_run_id_payroll_calc_run",
                "produced_by_run_id",
                "payroll_calc_run",
                "RESTRICT",
            ),
        },
        "payroll_month_snapshot": {
            (
                "fk_payroll_month_snapshot_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "CASCADE",
            ),
            (
                "fk_payroll_month_snapshot_calc_run_id_payroll_calc_run",
                "calc_run_id",
                "payroll_calc_run",
                "RESTRICT",
            ),
            (
                "fk_payroll_month_snapshot_paid_by_user",
                "paid_by",
                "user",
                "RESTRICT",
            ),
        },
        "payroll_month_event": {
            (
                "fk_payroll_month_event_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "CASCADE",
            ),
            (
                "fk_payroll_month_event_calc_run_id_payroll_calc_run",
                "calc_run_id",
                "payroll_calc_run",
                "SET NULL",
            ),
            (
                "fk_payroll_month_event_snapshot_id_payroll_month_snapshot",
                "snapshot_id",
                "payroll_month_snapshot",
                "SET NULL",
            ),
            (
                "fk_payroll_month_event_operator_id_user",
                "operator_id",
                "user",
                "RESTRICT",
            ),
        },
        "payroll_month_input": {
            (
                "fk_payroll_month_input_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "CASCADE",
            ),
            (
                "fk_payroll_month_input_employee_id_employee",
                "employee_id",
                "employee",
                "RESTRICT",
            ),
        },
        "payroll_input_value": {
            (
                "fk_payroll_input_value_input_id_payroll_month_input",
                "input_id",
                "payroll_month_input",
                "CASCADE",
            ),
            (
                "fk_payroll_input_value_field_def_id_salary_field_def",
                "field_def_id",
                "salary_field_def",
                "RESTRICT",
            ),
            (
                "fk_payroll_input_value_source_batch_id_payroll_import_batch",
                "source_batch_id",
                "payroll_import_batch",
                "SET NULL",
            ),
            (
                "fk_payroll_input_value_updated_by_user",
                "updated_by",
                "user",
                "RESTRICT",
            ),
        },
        "payroll_import_batch": {
            (
                "fk_payroll_import_batch_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_payroll_import_batch_operator_id_user",
                "operator_id",
                "user",
                "RESTRICT",
            ),
            (
                "fk_payroll_import_batch_superseded_by_batch_id",
                "superseded_by_batch_id",
                "payroll_import_batch",
                "SET NULL",
            ),
            (
                "fk_payroll_import_batch_payroll_month_id_payroll_month",
                "payroll_month_id",
                "payroll_month",
                "SET NULL",
            ),
        },
        "payroll_import_batch_row": {
            (
                "fk_payroll_import_batch_row_batch_id_payroll_import_batch",
                "batch_id",
                "payroll_import_batch",
                "CASCADE",
            ),
            (
                "fk_payroll_import_batch_row_employee_id_employee",
                "employee_id",
                "employee",
                "SET NULL",
            ),
        },
        "payroll_import_mapping_template": {
            (
                "fk_payroll_import_mapping_template_company_id_company",
                "company_id",
                "company",
                "CASCADE",
            )
        },
        "payroll_export": {
            (
                "fk_payroll_export_company_id_company",
                "company_id",
                "company",
                "RESTRICT",
            ),
            (
                "fk_payroll_export_snapshot_id_payroll_month_snapshot",
                "snapshot_id",
                "payroll_month_snapshot",
                "SET NULL",
            ),
            (
                "fk_payroll_export_calc_run_id_payroll_calc_run",
                "calc_run_id",
                "payroll_calc_run",
                "SET NULL",
            ),
            (
                "fk_payroll_export_operator_id_user",
                "operator_id",
                "user",
                "RESTRICT",
            ),
            (
                "fk_payroll_export_last_downloaded_by_user",
                "last_downloaded_by",
                "user",
                "RESTRICT",
            ),
        },
    }
)


@pytest.fixture(scope="module")
def inspector() -> sa.Inspector:
    return sa.inspect(engine)


def test_all_payroll_tables_exist(inspector: sa.Inspector) -> None:
    tables = set(inspector.get_table_names())

    assert len(PAYROLL_TABLES) == 21
    assert len(PAYROLL_CONFIG_TABLES) == 9
    assert len(PAYROLL_MONTH_TABLES) == 6
    assert len(PAYROLL_INPUT_TABLES) == 5
    assert len(PAYROLL_EXPORT_TABLES) == 1
    assert set(PAYROLL_TABLES) <= tables
    assert len(set(PAYROLL_TABLES)) == len(PAYROLL_TABLES)


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
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


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
def test_table_primary_key(inspector: sa.Inspector, table_name: str) -> None:
    primary_key = inspector.get_pk_constraint(table_name)

    assert tuple(primary_key["constrained_columns"]) == PRIMARY_KEYS[table_name]


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
def test_table_has_the_contract_unique_constraints(
    inspector: sa.Inspector, table_name: str
) -> None:
    unique_constraints = {
        (constraint["name"], tuple(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints(table_name)
    }

    assert unique_constraints == UNIQUE_CONSTRAINTS[table_name]


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
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
        and index["name"] not in (*DESC_INDEX_FRAGMENTS, *GIN_INDEXES)
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


def _index_definitions() -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = current_schema()"
            )
        ).all()
    return dict(rows)


def test_descending_indexes_match_the_contract() -> None:
    definitions = _index_definitions()

    for name, fragment in DESC_INDEX_FRAGMENTS.items():
        assert fragment.upper() in definitions[name].upper(), (
            name,
            definitions[name],
        )


def test_gin_indexes_match_the_contract() -> None:
    definitions = _index_definitions()

    for name, column in GIN_INDEXES.items():
        definition = definitions[name].lower()
        assert "using gin" in definition, definition
        assert column in definition, definition


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
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


@pytest.mark.parametrize("table_name", PAYROLL_TABLES)
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
        for name in (*PAYROLL_TABLES, "company", "department", "position", "employee")
    }


def _created_at_row() -> dict[str, Any]:
    return {"id": uuid.uuid7(), "created_at": datetime.now(UTC)}


def _created_updated_row() -> dict[str, Any]:
    now = datetime.now(UTC)
    return {"id": uuid.uuid7(), "created_at": now, "updated_at": now}


def _id_only_row() -> dict[str, Any]:
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


def _create_org(db: Session) -> tuple[Company, Department, Position, Employee]:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    employee = create_employee(db, dept=department, position=position)
    return company, department, position, employee


def _create_composition(
    db: Session,
    tables: dict[str, sa.Table],
    company_id: uuid.UUID,
    *,
    comp_code: str = "CMP1",
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "compensation_composition",
        {
            **_created_updated_row(),
            "company_id": company_id,
            "comp_code": comp_code,
            "comp_name": "标准薪酬构成",
            "is_active": True,
            "note": None,
        },
    )


def _create_composition_version(
    db: Session,
    tables: dict[str, sa.Table],
    comp_id: uuid.UUID,
    *,
    amounts: dict[str, Decimal] | None = None,
    total: Decimal | None = None,
    version_no: int = 1,
) -> uuid.UUID:
    line_items = amounts or dict.fromkeys(_COMPOSITION_CHECK_FIELDS, Decimal("100"))
    expected_total = (
        total if total is not None else sum(line_items.values(), Decimal("0"))
    )
    return _insert(
        db,
        tables,
        "compensation_composition_version",
        {
            **_created_at_row(),
            "comp_id": comp_id,
            "version_no": version_no,
            **line_items,
            "total_package": expected_total,
            "change_note": None,
            "created_by": None,
            "created_by_name": None,
        },
    )


def _create_scheme(
    db: Session,
    tables: dict[str, sa.Table],
    company_id: uuid.UUID,
    *,
    calc_code: str = "CALC1",
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "calc_scheme",
        {
            **_created_updated_row(),
            "company_id": company_id,
            "calc_code": calc_code,
            "calc_name": "标准计算方案",
            "is_active": True,
            "note": None,
        },
    )


def _create_workday_param(
    db: Session,
    tables: dict[str, sa.Table],
    company_id: uuid.UUID,
    *,
    workday_code: str = "WD1",
    avg_pay_days: Decimal = Decimal("21.75"),
    ot_mult_weekday: Decimal = Decimal("1.5"),
    min_wage: Decimal = Decimal("2000"),
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "workday_param",
        {
            **_created_updated_row(),
            "company_id": company_id,
            "workday_code": workday_code,
            "workday_name": "标准工作日",
            "avg_pay_days": avg_pay_days,
            "work_hours": Decimal("8"),
            "ot_mult_weekday": ot_mult_weekday,
            "ot_mult_weekend": Decimal("2"),
            "ot_mult_holiday": Decimal("3"),
            "min_wage": min_wage,
            "min_wage_note": None,
            "is_active": True,
            "note": None,
        },
    )


def _create_field_def(
    db: Session,
    tables: dict[str, sa.Table],
    *,
    field_key: str = "base_salary",
    label: str = "基本工资",
    category: str = "earning",
    calc_mode: str = "plan",
    source_key: str | None = "base_salary",
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "salary_field_def",
        {
            **_created_updated_row(),
            "field_key": field_key,
            "label": label,
            "category": category,
            "calc_mode": calc_mode,
            "source_key": source_key,
            "fixed_value": None,
            "default_formula": None,
            "display_order": 0,
            "visible": True,
            "is_system": True,
            "is_active": True,
            "note": None,
        },
    )


def _create_month(
    db: Session,
    tables: dict[str, sa.Table],
    company_id: uuid.UUID,
    *,
    month: date = date(2026, 9, 1),
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "payroll_month",
        {
            **_created_updated_row(),
            "company_id": company_id,
            "month": month,
            "status": "draft",
            "input_version": 0,
            "config_stale": False,
            "config_stale_detail": None,
            "calculated_at": None,
            "confirmed_at": None,
            "paid_at": None,
            "unlock_reason": None,
        },
    )


def _create_import_batch(
    db: Session,
    tables: dict[str, sa.Table],
    company_id: uuid.UUID,
    *,
    status: str = "preview",
    source: str = "upload",
    month: date = date(2026, 9, 1),
    source_rows: int = 0,
    payroll_month_id: uuid.UUID | None = None,
    committed_at: datetime | None = None,
) -> uuid.UUID:
    pasted = source == "paste"
    return _insert(
        db,
        tables,
        "payroll_import_batch",
        {
            **_created_at_row(),
            "company_id": company_id,
            "month": month,
            "status": status,
            "source": source,
            "file_name": None if pasted else "payroll.xlsx",
            "file_size": None if pasted else 100,
            "file_sha256": None if pasted else "a" * 64,
            "sheet_name": None if pasted else "Sheet1",
            "header_row_number": None if pasted else 1,
            "header_columns": None if pasted else [],
            "column_mapping": None if pasted else {},
            "parser_version": "payroll-import-v1",
            "source_rows": source_rows,
            "valid_records": 0,
            "error_records": 0,
            "warning_records": 0,
            "warning_counts": None,
            "operator_id": None,
            "operator_name": None,
            "committed_at": committed_at,
            "superseded_at": None,
            "discarded_at": None,
            "expires_at": None,
            "superseded_by_batch_id": None,
            "discard_reason": None,
            "payroll_month_id": payroll_month_id,
        },
    )


def _create_calc_run(
    db: Session,
    tables: dict[str, sa.Table],
    month_id: uuid.UUID,
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "payroll_calc_run",
        {
            **_id_only_row(),
            "payroll_month_id": month_id,
            "trigger": "manual",
            "status": "succeeded",
            "config_snapshot_version": 1,
            "config_snapshot": {},
            "input_version": 0,
            "input_snapshot": {},
            "attendance_month_id": None,
            "attendance_snapshot_id": None,
            "attendance_snapshot_version": None,
            "attendance_calc_run_id": None,
            "calc_version": "1.0.0",
            "rules_version": "rules-1",
            "attendance_locked_at": None,
            "summary": None,
            "error_code": None,
            "error_message": None,
            "triggered_by": None,
            "triggered_by_name": None,
            "started_at": datetime.now(UTC),
            "finished_at": None,
        },
    )


def _create_result(
    db: Session,
    tables: dict[str, sa.Table],
    *,
    month_id: uuid.UUID,
    run_id: uuid.UUID,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    position_id: uuid.UUID,
    dept_id: uuid.UUID,
    scheme_id: uuid.UUID,
) -> uuid.UUID:
    return _insert(
        db,
        tables,
        "payroll_result",
        {
            **_created_updated_row(),
            "payroll_month_id": month_id,
            "calc_run_id": run_id,
            "company_id": company_id,
            "employee_id": employee_id,
            "position_id": position_id,
            "dept_id": dept_id,
            "cost_org_id": None,
            "calc_scheme_id": scheme_id,
            "position_code": "P1",
            "position_name": "项目经理",
            "dept_code": "D1",
            "dept_name": "生产部",
            "cost_org_code": None,
            "cost_org_name": None,
            "dept_path": [],
            "cost_org_path": [],
            "attendance_source": {},
        },
    )


def test_composition_version_checks_and_uniqueness(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    comp_id = _create_composition(db, tables, company.id)
    _create_composition_version(db, tables, comp_id)

    with _integrity_error(db):
        _create_composition_version(
            db,
            tables,
            comp_id,
            amounts={"base_salary": Decimal("-1")},
            total=Decimal("699"),
            version_no=2,
        )

    with _integrity_error(db):
        _create_composition_version(
            db,
            tables,
            comp_id,
            total=Decimal("999"),
            version_no=3,
        )

    with _integrity_error(db):
        _create_composition_version(db, tables, comp_id, version_no=1)


def test_workday_parameter_checks(db: Session, tables: dict[str, sa.Table]) -> None:
    company = create_company(db)
    _create_workday_param(db, tables, company.id)

    with _integrity_error(db):
        _create_workday_param(
            db, tables, company.id, workday_code="WD2", avg_pay_days=Decimal("0")
        )
    with _integrity_error(db):
        _create_workday_param(
            db, tables, company.id, workday_code="WD3", ot_mult_weekday=Decimal("0.5")
        )
    with _integrity_error(db):
        _create_workday_param(
            db, tables, company.id, workday_code="WD4", min_wage=Decimal("-1")
        )


def test_global_statutory_parameter_value_type_is_exclusive(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    def row(
        *,
        key: str,
        value_type: str,
        numeric_value: Decimal | None,
        json_value: dict[str, Any] | None,
    ) -> dict[str, Any]:
        # Omit absent values so they bind as SQL NULL; the reflected JSONB
        # column would otherwise serialize ``None`` as JSON ``null``.
        payload: dict[str, Any] = {
            **_created_updated_row(),
            "key": key,
            "label": key,
            "category": "tax",
            "value_type": value_type,
            "display_order": 0,
            "is_active": True,
            "note": None,
        }
        if numeric_value is not None:
            payload["numeric_value"] = numeric_value
        if json_value is not None:
            payload["json_value"] = json_value
        return payload

    _insert(
        db,
        tables,
        "payroll_global_param",
        row(
            key="tax_threshold",
            value_type="number",
            numeric_value=Decimal("5000"),
            json_value=None,
        ),
    )
    _insert(
        db,
        tables,
        "payroll_global_param",
        row(
            key="confidentiality_tier",
            value_type="json",
            numeric_value=None,
            json_value=[],
        ),
    )

    with _integrity_error(db):
        _insert(
            db,
            tables,
            "payroll_global_param",
            row(
                key="bad_number",
                value_type="number",
                numeric_value=None,
                json_value=None,
            ),
        )
    with _integrity_error(db):
        _insert(
            db,
            tables,
            "payroll_global_param",
            row(
                key="bad_json",
                value_type="json",
                numeric_value=Decimal("1"),
                json_value=None,
            ),
        )
    with _integrity_error(db):
        _insert(
            db,
            tables,
            "payroll_global_param",
            row(
                key="bad_type",
                value_type="text",
                numeric_value=Decimal("1"),
                json_value=None,
            ),
        )


def test_model_writes_nullable_jsonb_none_as_sql_null(db: Session) -> None:
    param = PayrollGlobalParam(
        key="tax_rate",
        label="税率",
        category="tax",
        value_type=PayrollGlobalParamType.NUMBER,
        numeric_value=Decimal("0.03"),
        json_value=None,
    )
    db.add(param)
    db.commit()

    stored_is_null = db.execute(
        sa.text("SELECT json_value IS NULL FROM payroll_global_param WHERE id = :id"),
        {"id": param.id},
    ).scalar_one()

    assert stored_is_null is True


def test_month_is_unique_per_company_and_starts_on_the_first_day(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    _create_month(db, tables, company.id)

    with _integrity_error(db):
        _create_month(db, tables, company.id)
    with _integrity_error(db):
        _create_month(db, tables, company.id, month=date(2026, 9, 2))


def test_salary_field_def_uniqueness_and_source_key_partial_unique(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    _create_field_def(db, tables)
    _create_field_def(
        db,
        tables,
        field_key="custom_field",
        label="自定义字段",
        category="addon",
        calc_mode="import",
        source_key=None,
    )
    _create_field_def(
        db,
        tables,
        field_key="custom_field_2",
        label="自定义字段二",
        category="addon",
        calc_mode="import",
        source_key=None,
    )

    with _integrity_error(db):
        _create_field_def(
            db,
            tables,
            field_key="other_field",
            label="基本工资",
            category="addon",
            calc_mode="import",
            source_key=None,
        )
    with _integrity_error(db):
        _create_field_def(
            db,
            tables,
            field_key="third_field",
            label="第三个字段",
            category="addon",
            calc_mode="import",
            source_key="base_salary",
        )
    with _integrity_error(db):
        _create_field_def(
            db,
            tables,
            field_key="Bad-Key",
            label="非法键",
            category="addon",
            calc_mode="fixed",
            source_key=None,
        )


def test_payroll_month_cascades_runs_results_and_snapshots(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company, department, position, employee = _create_org(db)
    scheme_id = _create_scheme(db, tables, company.id)
    month_id = _create_month(db, tables, company.id)
    run_id = _create_calc_run(db, tables, month_id)
    result_id = _create_result(
        db,
        tables,
        month_id=month_id,
        run_id=run_id,
        company_id=company.id,
        employee_id=employee.id,
        position_id=position.id,
        dept_id=department.id,
        scheme_id=scheme_id,
    )
    snapshot_id = _insert(
        db,
        tables,
        "payroll_month_snapshot",
        {
            **_id_only_row(),
            "payroll_month_id": month_id,
            "calc_run_id": run_id,
            "version": 1,
            "paid_at": datetime.now(UTC),
            "paid_by": _superuser_id(db),
            "paid_by_name": "管理员",
            "payload": {},
        },
    )

    with _integrity_error(db):
        _create_result(
            db,
            tables,
            month_id=month_id,
            run_id=run_id,
            company_id=company.id,
            employee_id=employee.id,
            position_id=position.id,
            dept_id=department.id,
            scheme_id=scheme_id,
        )

    db.execute(
        sa.delete(tables["payroll_month"]).where(
            tables["payroll_month"].c.id == month_id
        )
    )
    db.commit()

    for table_name, row_id in (
        ("payroll_calc_run", run_id),
        ("payroll_result", result_id),
        ("payroll_month_snapshot", snapshot_id),
    ):
        assert (
            db.execute(
                sa.select(tables[table_name].c.id).where(
                    tables[table_name].c.id == row_id
                )
            ).first()
            is None
        )


def test_result_value_cascades_with_the_result_and_restricts_the_run(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company, department, position, employee = _create_org(db)
    scheme_id = _create_scheme(db, tables, company.id)
    field_id = _create_field_def(db, tables)
    month_id = _create_month(db, tables, company.id)
    run_id = _create_calc_run(db, tables, month_id)
    result_id = _create_result(
        db,
        tables,
        month_id=month_id,
        run_id=run_id,
        company_id=company.id,
        employee_id=employee.id,
        position_id=position.id,
        dept_id=department.id,
        scheme_id=scheme_id,
    )
    value_id = _insert(
        db,
        tables,
        "payroll_result_value",
        {
            **_created_updated_row(),
            "result_id": result_id,
            "field_def_id": field_id,
            "value": Decimal("5000"),
            "source": "plan",
            "produced_by_run_id": run_id,
        },
    )

    with _integrity_error(db):
        _create_result(
            db,
            tables,
            month_id=month_id,
            run_id=run_id,
            company_id=company.id,
            employee_id=employee.id,
            position_id=position.id,
            dept_id=department.id,
            scheme_id=scheme_id,
        )

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["payroll_calc_run"]).where(
                tables["payroll_calc_run"].c.id == run_id
            )
        )
        db.commit()

    db.execute(
        sa.delete(tables["payroll_result"]).where(
            tables["payroll_result"].c.id == result_id
        )
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["payroll_result_value"].c.id).where(
                tables["payroll_result_value"].c.id == value_id
            )
        ).first()
        is None
    )


def test_import_batch_committed_is_partial_unique(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    _create_import_batch(db, tables, company.id, status="committed")
    _create_import_batch(db, tables, company.id)
    _create_import_batch(db, tables, company.id)

    with _integrity_error(db):
        _create_import_batch(db, tables, company.id, status="committed")
    with _integrity_error(db):
        _create_import_batch(db, tables, company.id, source_rows=-1)
    with _integrity_error(db):
        _create_import_batch(db, tables, company.id, month=date(2026, 9, 2))


def test_import_batch_row_cascades_with_the_batch(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    batch_id = _create_import_batch(
        db, tables, company.id, source="paste", source_rows=1
    )
    row_id = _insert(
        db,
        tables,
        "payroll_import_batch_row",
        {
            **_id_only_row(),
            "batch_id": batch_id,
            "source_row_number": 2,
            "employee_id": None,
            "employee_no_raw": "E001",
            "values": {},
            "status": "valid",
            "error_code": None,
            "error_message": None,
            "warnings": None,
            "raw_row": None,
        },
    )

    with _integrity_error(db):
        _insert(
            db,
            tables,
            "payroll_import_batch_row",
            {
                **_id_only_row(),
                "batch_id": batch_id,
                "source_row_number": 0,
                "employee_id": None,
                "employee_no_raw": None,
                "values": None,
                "status": "valid",
                "error_code": None,
                "error_message": None,
                "warnings": None,
                "raw_row": None,
            },
        )

    db.execute(
        sa.delete(tables["payroll_import_batch"]).where(
            tables["payroll_import_batch"].c.id == batch_id
        )
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["payroll_import_batch_row"].c.id).where(
                tables["payroll_import_batch_row"].c.id == row_id
            )
        ).first()
        is None
    )


def test_input_value_source_batch_is_nulled_when_the_batch_is_deleted(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company, department, position, employee = _create_org(db)
    field_id = _create_field_def(
        db,
        tables,
        field_key="phone_allowance",
        label="话费补贴",
        category="addon",
        calc_mode="import",
        source_key="phone_allowance",
    )
    month_id = _create_month(db, tables, company.id)
    batch_id = _create_import_batch(
        db,
        tables,
        company.id,
        status="committed",
        source_rows=1,
        payroll_month_id=month_id,
        committed_at=datetime.now(UTC),
    )
    input_id = _insert(
        db,
        tables,
        "payroll_month_input",
        {
            **_created_updated_row(),
            "payroll_month_id": month_id,
            "employee_id": employee.id,
        },
    )
    value_id = _insert(
        db,
        tables,
        "payroll_input_value",
        {
            **_id_only_row(),
            "input_id": input_id,
            "field_def_id": field_id,
            "value": Decimal("100"),
            "source": "import",
            "source_batch_id": batch_id,
            "updated_by": None,
            "updated_by_name": None,
            "updated_at": datetime.now(UTC),
        },
    )

    db.execute(
        sa.delete(tables["payroll_import_batch"]).where(
            tables["payroll_import_batch"].c.id == batch_id
        )
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["payroll_input_value"].c.source_batch_id).where(
                tables["payroll_input_value"].c.id == value_id
            )
        ).scalar_one()
        is None
    )


def test_position_delete_cascades_the_payroll_assignment(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    department = create_department(db, company=company)
    position = create_position(db, company=company, dept=department)
    comp_id = _create_composition(db, tables, company.id)
    scheme_id = _create_scheme(db, tables, company.id)
    workday_id = _create_workday_param(db, tables, company.id)
    config_id = _insert(
        db,
        tables,
        "position_payroll_config",
        {
            **_created_updated_row(),
            "position_id": position.id,
            "comp_id": comp_id,
            "calc_scheme_id": scheme_id,
            "workday_param_id": workday_id,
            "note": None,
        },
    )

    db.execute(
        sa.delete(tables["position"]).where(tables["position"].c.id == position.id)
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["position_payroll_config"].c.id).where(
                tables["position_payroll_config"].c.id == config_id
            )
        ).first()
        is None
    )


def test_company_delete_is_restricted_by_payroll_configuration(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    _create_composition(db, tables, company.id)

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["company"]).where(tables["company"].c.id == company.id)
        )
        db.commit()


def test_snapshot_references_are_nulled_on_delete(
    db: Session, tables: dict[str, sa.Table]
) -> None:
    company = create_company(db)
    month_id = _create_month(db, tables, company.id)
    run_id = _create_calc_run(db, tables, month_id)
    snapshot_id = _insert(
        db,
        tables,
        "payroll_month_snapshot",
        {
            **_id_only_row(),
            "payroll_month_id": month_id,
            "calc_run_id": run_id,
            "version": 1,
            "paid_at": datetime.now(UTC),
            "paid_by": _superuser_id(db),
            "paid_by_name": "管理员",
            "payload": {},
        },
    )
    event_id = _insert(
        db,
        tables,
        "payroll_month_event",
        {
            **_id_only_row(),
            "payroll_month_id": month_id,
            "event": "paid",
            "from_status": "confirmed",
            "to_status": "paid",
            "calc_run_id": run_id,
            "snapshot_id": snapshot_id,
            "reason": None,
            "operator_id": None,
            "operator_name": None,
            "created_at": datetime.now(UTC),
        },
    )
    export_id = _insert(
        db,
        tables,
        "payroll_export",
        {
            **_created_at_row(),
            "company_id": company.id,
            "month": date(2026, 9, 1),
            "export_type": "payslip_zip",
            "format": "zip",
            "mode": "official",
            "snapshot_id": snapshot_id,
            "snapshot_version": 1,
            "calc_run_id": run_id,
            "month_status_at_creation": "paid",
            "filter": None,
            "filter_hash": None,
            "employee_count": 1,
            "status": "succeeded",
            "progress_done": 1,
            "progress_total": 1,
            "error_code": None,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
            "artifact_path": None,
            "artifact_size": None,
            "expires_at": None,
            "artifact_deleted_at": None,
            "operator_id": None,
            "operator_name": None,
            "template_version": None,
            "download_count": 0,
            "last_downloaded_by": None,
            "last_downloaded_by_name": None,
            "last_downloaded_at": None,
        },
    )

    with _integrity_error(db):
        db.execute(
            sa.delete(tables["payroll_calc_run"]).where(
                tables["payroll_calc_run"].c.id == run_id
            )
        )
        db.commit()

    db.execute(
        sa.delete(tables["payroll_month_snapshot"]).where(
            tables["payroll_month_snapshot"].c.id == snapshot_id
        )
    )
    db.commit()

    assert (
        db.execute(
            sa.select(tables["payroll_month_event"].c.snapshot_id).where(
                tables["payroll_month_event"].c.id == event_id
            )
        ).scalar_one()
        is None
    )
    assert (
        db.execute(
            sa.select(tables["payroll_export"].c.snapshot_id).where(
                tables["payroll_export"].c.id == export_id
            )
        ).scalar_one()
        is None
    )
