"""Independent list of the 21 payroll tables, grouped by migration.

Tests keep their own copy so a missing model or migration cannot silently
shorten the isolation, schema, and migration assertions.
"""

from sqlalchemy import text
from sqlmodel import Session

PAYROLL_CONFIG_TABLES: tuple[str, ...] = (
    "salary_field_def",
    "compensation_composition",
    "compensation_composition_version",
    "workday_param",
    "calc_scheme",
    "calc_scheme_formula",
    "position_payroll_config",
    "payroll_global_param",
    "payroll_config_revision",
)

PAYROLL_MONTH_TABLES: tuple[str, ...] = (
    "payroll_month",
    "payroll_calc_run",
    "payroll_result",
    "payroll_result_value",
    "payroll_month_snapshot",
    "payroll_month_event",
)

PAYROLL_INPUT_TABLES: tuple[str, ...] = (
    "payroll_month_input",
    "payroll_input_value",
    "payroll_import_batch",
    "payroll_import_batch_row",
    "payroll_import_mapping_template",
)

PAYROLL_EXPORT_TABLES: tuple[str, ...] = ("payroll_export",)

PAYROLL_TABLES: tuple[str, ...] = (
    *PAYROLL_CONFIG_TABLES,
    *PAYROLL_MONTH_TABLES,
    *PAYROLL_INPUT_TABLES,
    *PAYROLL_EXPORT_TABLES,
)

# System-owned payroll tables have no ``company`` foreign key, so
# ``TRUNCATE company CASCADE`` cannot clear them between tests.
PAYROLL_SYSTEM_TABLES: tuple[str, ...] = (
    "salary_field_def",
    "payroll_global_param",
    "payroll_config_revision",
)

# Row counts every test starts with once isolation has cleared company data,
# truncated the system tables, and re-run ``ensure_payroll_defaults``.
PAYROLL_STARTING_COUNTS: dict[str, int] = {
    **dict.fromkeys(PAYROLL_TABLES, 0),
    "salary_field_def": 32,
    "payroll_global_param": 6,
}


def truncate_payroll_system_tables(db: Session) -> None:
    db.execute(text("TRUNCATE TABLE " + ", ".join(PAYROLL_SYSTEM_TABLES) + " CASCADE"))
