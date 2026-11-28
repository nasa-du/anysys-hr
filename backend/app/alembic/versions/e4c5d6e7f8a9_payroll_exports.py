"""Payroll export job table

Revision ID: e4c5d6e7f8a9
Revises: e3b4c5d6e7f8
Create Date: 2026-11-28 00:00:00.000000

The export audit table. Columns, constraints, indexes, and foreign-key
behaviors follow docs/specs/payroll-management.md sections 4.21 and 16. The
migration inserts no rows.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e4c5d6e7f8a9"
down_revision = "e3b4c5d6e7f8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_export",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "export_type",
            sa.Enum(
                "payslip_single",
                "payslip_zip",
                "payslip_merged",
                "payroll_detail_xlsx",
                "department_summary_xlsx",
                name="ck_payroll_export_export_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("format", sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
        sa.Column("mode", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True),
        sa.Column("snapshot_id", sa.UUID(), nullable=True),
        sa.Column("snapshot_version", sa.Integer(), nullable=True),
        sa.Column("calc_run_id", sa.UUID(), nullable=True),
        sa.Column(
            "month_status_at_creation",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=True,
        ),
        sa.Column("filter", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "filter_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column("employee_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "failed",
                "expired",
                name="ck_payroll_export_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("progress_done", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column(
            "error_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.Column(
            "error_message", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "artifact_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("artifact_size", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artifact_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_id", sa.UUID(), nullable=True),
        sa.Column(
            "operator_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column(
            "template_version",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=True,
        ),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("last_downloaded_by", sa.UUID(), nullable=True),
        sa.Column(
            "last_downloaded_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("last_downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_payroll_export_month_first_day"
        ),
        sa.CheckConstraint(
            "download_count >= 0",
            name="ck_payroll_export_download_count_non_negative",
        ),
        sa.CheckConstraint(
            "employee_count >= 0",
            name="ck_payroll_export_employee_count_non_negative",
        ),
        sa.CheckConstraint(
            "progress_done >= 0",
            name="ck_payroll_export_progress_done_non_negative",
        ),
        sa.CheckConstraint(
            "progress_total >= 0",
            name="ck_payroll_export_progress_total_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["payroll_calc_run.id"],
            name="fk_payroll_export_calc_run_id_payroll_calc_run",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_payroll_export_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["last_downloaded_by"],
            ["user.id"],
            name="fk_payroll_export_last_downloaded_by_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["user.id"],
            name="fk_payroll_export_operator_id_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["payroll_month_snapshot.id"],
            name="fk_payroll_export_snapshot_id_payroll_month_snapshot",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payroll_export_company_month_created_at",
        "payroll_export",
        ["company_id", "month", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_payroll_export_expires_at",
        "payroll_export",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_export_status_created_at",
        "payroll_export",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_export_status_created_at", table_name="payroll_export")
    op.drop_index("ix_payroll_export_expires_at", table_name="payroll_export")
    op.drop_index(
        "ix_payroll_export_company_month_created_at",
        table_name="payroll_export",
    )
    op.drop_table("payroll_export")
