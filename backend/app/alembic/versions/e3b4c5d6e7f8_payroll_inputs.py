"""Payroll monthly input and import tables

Revision ID: e3b4c5d6e7f8
Revises: e2a3b4c5d6e7
Create Date: 2026-11-28 00:00:00.000000

Five monthly-input and import tables. All columns, constraints, indexes, and
foreign-key behaviors follow docs/specs/payroll-management.md sections
4.16-4.20 and 16. The migration inserts no rows.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e3b4c5d6e7f8"
down_revision = "e2a3b4c5d6e7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_import_batch",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "preview",
                "committed",
                "superseded",
                "discarded",
                name="ck_payroll_import_batch_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "upload",
                "paste",
                name="ck_payroll_import_batch_source",
                native_enum=False,
                create_constraint=True,
                length=16,
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
            "header_columns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "column_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "parser_version",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
        ),
        sa.Column("source_rows", sa.Integer(), nullable=False),
        sa.Column("valid_records", sa.Integer(), nullable=False),
        sa.Column("error_records", sa.Integer(), nullable=False),
        sa.Column("warning_records", sa.Integer(), nullable=False),
        sa.Column(
            "warning_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("operator_id", sa.UUID(), nullable=True),
        sa.Column(
            "operator_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "discard_reason",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("payroll_month_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_payroll_import_batch_month_first_day",
        ),
        sa.CheckConstraint(
            "error_records >= 0",
            name="ck_payroll_import_batch_error_records_non_negative",
        ),
        sa.CheckConstraint(
            "source_rows >= 0",
            name="ck_payroll_import_batch_source_rows_non_negative",
        ),
        sa.CheckConstraint(
            "valid_records >= 0",
            name="ck_payroll_import_batch_valid_records_non_negative",
        ),
        sa.CheckConstraint(
            "warning_records >= 0",
            name="ck_payroll_import_batch_warning_records_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_payroll_import_batch_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["user.id"],
            name="fk_payroll_import_batch_operator_id_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_import_batch_payroll_month_id_payroll_month",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_batch_id"],
            ["payroll_import_batch.id"],
            name="fk_payroll_import_batch_superseded_by_batch_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payroll_import_batch_company_month_status_created_at",
        "payroll_import_batch",
        [
            "company_id",
            "month",
            "status",
            sa.literal_column("created_at DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "uq_payroll_import_batch_company_month_committed",
        "payroll_import_batch",
        ["company_id", "month"],
        unique=True,
        postgresql_where=sa.text("status = 'committed'"),
    )
    op.create_table(
        "payroll_month_input",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payroll_month_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_payroll_month_input_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_month_input_payroll_month_id_payroll_month",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payroll_month_id",
            "employee_id",
            name="uq_payroll_month_input_month_employee",
        ),
    )
    op.create_index(
        "ix_payroll_month_input_employee_id",
        "payroll_month_input",
        ["employee_id"],
        unique=False,
    )
    op.create_table(
        "payroll_import_batch_row",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=True),
        sa.Column(
            "employee_no_raw",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "values", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "status",
            sa.Enum(
                "valid",
                "error",
                "skipped",
                name="ck_payroll_import_batch_row_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "error_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.Column(
            "error_message",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column(
            "warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.CheckConstraint(
            "source_row_number >= 1",
            name="ck_payroll_import_batch_row_source_row_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["payroll_import_batch.id"],
            name="fk_payroll_import_batch_row_batch_id_payroll_import_batch",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_payroll_import_batch_row_employee_id_employee",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payroll_import_batch_row_batch_row",
        "payroll_import_batch_row",
        ["batch_id", "source_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_import_batch_row_batch_status",
        "payroll_import_batch_row",
        ["batch_id", "status"],
        unique=False,
    )
    op.create_table(
        "payroll_input_value",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("input_id", sa.UUID(), nullable=False),
        sa.Column("field_def_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "import",
                "manual",
                name="ck_payroll_input_value_source",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("source_batch_id", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_def_id"],
            ["salary_field_def.id"],
            name="fk_payroll_input_value_field_def_id_salary_field_def",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["input_id"],
            ["payroll_month_input.id"],
            name="fk_payroll_input_value_input_id_payroll_month_input",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_batch_id"],
            ["payroll_import_batch.id"],
            name="fk_payroll_input_value_source_batch_id_payroll_import_batch",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_payroll_input_value_updated_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "input_id",
            "field_def_id",
            name="uq_payroll_input_value_input_field",
        ),
    )
    op.create_index(
        "ix_payroll_input_value_field_def_id",
        "payroll_input_value",
        ["field_def_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_input_value_source_batch_id",
        "payroll_input_value",
        ["source_batch_id"],
        unique=False,
    )
    op.create_table(
        "payroll_import_mapping_template",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "column_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_payroll_import_mapping_template_company_id_company",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", name="uq_payroll_import_mapping_template_company"
        ),
    )


def downgrade() -> None:
    op.drop_table("payroll_import_mapping_template")
    op.drop_index(
        "ix_payroll_input_value_source_batch_id",
        table_name="payroll_input_value",
    )
    op.drop_index(
        "ix_payroll_input_value_field_def_id",
        table_name="payroll_input_value",
    )
    op.drop_table("payroll_input_value")
    op.drop_index(
        "ix_payroll_import_batch_row_batch_status",
        table_name="payroll_import_batch_row",
    )
    op.drop_index(
        "ix_payroll_import_batch_row_batch_row",
        table_name="payroll_import_batch_row",
    )
    op.drop_table("payroll_import_batch_row")
    op.drop_index(
        "ix_payroll_month_input_employee_id",
        table_name="payroll_month_input",
    )
    op.drop_table("payroll_month_input")
    op.drop_index(
        "uq_payroll_import_batch_company_month_committed",
        table_name="payroll_import_batch",
        postgresql_where=sa.text("status = 'committed'"),
    )
    op.drop_index(
        "ix_payroll_import_batch_company_month_status_created_at",
        table_name="payroll_import_batch",
    )
    op.drop_table("payroll_import_batch")
