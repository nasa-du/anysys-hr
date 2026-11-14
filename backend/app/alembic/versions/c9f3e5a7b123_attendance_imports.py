"""Attendance imports tables

Revision ID: c9f3e5a7b123
Revises: b8e2d4f6a012
Create Date: 2026-11-14 00:00:00.000000

All columns, constraints, indexes, and foreign-key behaviors follow
docs/specs/attendance-management.md sections 4.10, 4.12, and 12.
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c9f3e5a7b123"
down_revision = "b8e2d4f6a012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batch",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "data_type",
            sa.Enum(
                "punch",
                "trip",
                "ot",
                "leave",
                name="ck_import_batch_data_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "preview",
                "committed",
                "superseded",
                "discarded",
                "revoked",
                name="ck_import_batch_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "upload",
                "paste",
                name="ck_import_batch_source",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "file_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column(
            "file_sha256", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "sheet_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column("header_row_number", sa.Integer(), nullable=True),
        sa.Column(
            "header_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "parser_version",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
        ),
        sa.Column("source_rows", sa.Integer(), nullable=False),
        sa.Column("valid_records", sa.Integer(), nullable=False),
        sa.Column("skipped_records", sa.Integer(), nullable=False),
        sa.Column("error_records", sa.Integer(), nullable=False),
        sa.Column("warning_records", sa.Integer(), nullable=False),
        sa.Column(
            "skip_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "warning_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "discard_reason", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_import_batch_month_first_day"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_import_batch_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["user.id"],
            name="fk_import_batch_operator_id_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_batch_id"],
            ["import_batch.id"],
            name="fk_import_batch_superseded_by_batch_id_import_batch",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_batch_company_type_month_status",
        "import_batch",
        ["company_id", "data_type", "month", "status"],
        unique=False,
    )
    op.create_index(
        "ix_import_batch_expires_at", "import_batch", ["expires_at"], unique=False
    )
    op.create_index(
        "uq_import_batch_company_type_month_committed",
        "import_batch",
        ["company_id", "data_type", "month"],
        unique=True,
        postgresql_where=sa.text("status = 'committed'"),
    )
    op.create_table(
        "import_batch_error",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column(
            "column_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column(
            "message", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "error",
                "warning",
                name="ck_import_batch_error_severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batch.id"],
            name="fk_import_batch_error_batch_id_import_batch",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_batch_error_batch_row",
        "import_batch_error",
        ["batch_id", "source_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_import_batch_error_batch_severity",
        "import_batch_error",
        ["batch_id", "severity"],
        unique=False,
    )
    op.create_table(
        "import_mapping_template",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "data_type",
            sa.Enum(
                "punch",
                "trip",
                "ot",
                "leave",
                name="ck_import_mapping_template_data_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "header_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_import_mapping_template_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_import_mapping_template_updated_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "data_type", name="uq_import_mapping_template_company_type"
        ),
    )
    op.create_table(
        "punch_record",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column(
            "employee_no_raw",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
        ),
        sa.Column(
            "employee_name_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "department_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("punch_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "punch_result_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column(
            "device_raw", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True
        ),
        sa.Column(
            "address_raw", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True
        ),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batch.id"],
            name="fk_punch_record_batch_id_import_batch",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_punch_record_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_punch_record_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "employee_id",
            "attendance_date",
            "punch_time",
            name="uq_punch_record_batch_employee_date_time",
        ),
        sa.UniqueConstraint(
            "batch_id", "source_row_number", name="uq_punch_record_batch_row"
        ),
    )
    op.create_index(
        "ix_punch_record_batch_id", "punch_record", ["batch_id"], unique=False
    )
    op.create_index(
        "ix_punch_record_company_date",
        "punch_record",
        ["company_id", "attendance_date"],
        unique=False,
    )
    op.create_index(
        "ix_punch_record_company_employee_date",
        "punch_record",
        ["company_id", "employee_id", "attendance_date"],
        unique=False,
    )
    op.create_table(
        "oa_trip",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("split_index", sa.Integer(), nullable=False),
        sa.Column(
            "approval_no", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column(
            "employee_name_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "department_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "application_type_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column(
            "approval_result_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column(
            "approval_status_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days_declared", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batch.id"],
            name="fk_oa_trip_batch_id_import_batch",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_oa_trip_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_oa_trip_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "source_row_number",
            "split_index",
            name="uq_oa_trip_batch_row_split",
        ),
    )
    op.create_index("ix_oa_trip_batch_id", "oa_trip", ["batch_id"], unique=False)
    op.create_index(
        "ix_oa_trip_company_dates",
        "oa_trip",
        ["company_id", "start_date", "end_date"],
        unique=False,
    )
    op.create_index(
        "uq_oa_trip_batch_approval_employee",
        "oa_trip",
        ["batch_id", "approval_no", "employee_id"],
        unique=True,
        postgresql_where=sa.text("approval_no IS NOT NULL"),
    )
    op.create_table(
        "oa_overtime",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column(
            "approval_no", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column(
            "employee_name_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "department_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "approval_result_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column(
            "approval_status_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "declared_raw", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.Column(
            "reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batch.id"],
            name="fk_oa_overtime_batch_id_import_batch",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_oa_overtime_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_oa_overtime_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "source_row_number", name="uq_oa_overtime_batch_row"
        ),
    )
    op.create_index(
        "ix_oa_overtime_batch_id", "oa_overtime", ["batch_id"], unique=False
    )
    op.create_index(
        "ix_oa_overtime_company_range",
        "oa_overtime",
        ["company_id", "start_at", "end_at"],
        unique=False,
    )
    op.create_index(
        "uq_oa_overtime_batch_approval_employee",
        "oa_overtime",
        ["batch_id", "approval_no", "employee_id"],
        unique=True,
        postgresql_where=sa.text("approval_no IS NOT NULL"),
    )
    op.create_table(
        "oa_overtime_day",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("overtime_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "minutes BETWEEN 0 AND 480", name="ck_oa_overtime_day_minutes_range"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_oa_overtime_day_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["overtime_id"],
            ["oa_overtime.id"],
            name="fk_oa_overtime_day_overtime_id_oa_overtime",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "overtime_id", "work_date", name="uq_oa_overtime_day_overtime_date"
        ),
    )
    op.create_index(
        "ix_oa_overtime_day_company_date",
        "oa_overtime_day",
        ["company_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_oa_overtime_day_overtime_id",
        "oa_overtime_day",
        ["overtime_id"],
        unique=False,
    )
    op.create_table(
        "oa_leave",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column(
            "approval_no", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column(
            "employee_name_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "department_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "leave_type_raw",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "leave_kind",
            sa.Enum(
                "paid",
                "unpaid",
                "comp",
                name="ck_oa_leave_leave_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("days", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("rest_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rest_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rest_start_date", sa.Date(), nullable=False),
        sa.Column("rest_end_date", sa.Date(), nullable=False),
        sa.Column("work_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_start_date", sa.Date(), nullable=True),
        sa.Column("work_end_date", sa.Date(), nullable=True),
        sa.Column(
            "balance_days_declared", sa.Numeric(precision=6, scale=2), nullable=True
        ),
        sa.Column(
            "reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "approval_result_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column(
            "approval_status_raw",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("days > 0", name="ck_oa_leave_days_positive"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batch.id"],
            name="fk_oa_leave_batch_id_import_batch",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_oa_leave_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_oa_leave_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "source_row_number", name="uq_oa_leave_batch_row"
        ),
    )
    op.create_index("ix_oa_leave_batch_id", "oa_leave", ["batch_id"], unique=False)
    op.create_index(
        "ix_oa_leave_company_dates",
        "oa_leave",
        ["company_id", "rest_start_date", "rest_end_date"],
        unique=False,
    )
    op.create_index(
        "uq_oa_leave_batch_approval_employee",
        "oa_leave",
        ["batch_id", "approval_no", "employee_id"],
        unique=True,
        postgresql_where=sa.text("approval_no IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("oa_leave")
    op.drop_table("oa_overtime_day")
    op.drop_table("oa_overtime")
    op.drop_table("oa_trip")
    op.drop_table("punch_record")
    op.drop_table("import_mapping_template")
    op.drop_table("import_batch_error")
    op.drop_table("import_batch")
