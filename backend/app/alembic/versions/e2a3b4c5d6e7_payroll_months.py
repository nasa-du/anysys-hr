"""Payroll month, calculation run, and result tables

Revision ID: e2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-28 00:00:00.000000

Six month/result tables. All columns, constraints, indexes, and foreign-key
behaviors follow docs/specs/payroll-management.md sections 4.10-4.15 and 16.
The migration inserts no rows.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_month",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "calculated",
                "confirmed",
                "paid",
                name="ck_payroll_month_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("input_version", sa.Integer(), nullable=False),
        sa.Column("config_stale", sa.Boolean(), nullable=False),
        sa.Column(
            "config_stale_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unlock_reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_payroll_month_first_day"
        ),
        sa.CheckConstraint(
            "input_version >= 0", name="ck_payroll_month_input_version_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_payroll_month_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "month", name="uq_payroll_month_company_month"
        ),
    )
    op.create_table(
        "payroll_calc_run",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payroll_month_id", sa.UUID(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "initial",
                "manual",
                "attendance_refresh",
                name="ck_payroll_calc_run_trigger",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "succeeded",
                "failed",
                name="ck_payroll_calc_run_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("config_snapshot_version", sa.Integer(), nullable=False),
        sa.Column(
            "config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("input_version", sa.Integer(), nullable=False),
        sa.Column(
            "input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("attendance_month_id", sa.UUID(), nullable=True),
        sa.Column("attendance_snapshot_id", sa.UUID(), nullable=True),
        sa.Column("attendance_snapshot_version", sa.Integer(), nullable=True),
        sa.Column("attendance_calc_run_id", sa.UUID(), nullable=True),
        sa.Column(
            "calc_version", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True
        ),
        sa.Column(
            "rules_version", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column("attendance_locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "error_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.Column(
            "error_message", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.Column(
            "triggered_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_calc_run_payroll_month_id_payroll_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"],
            ["user.id"],
            name="fk_payroll_calc_run_triggered_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payroll_calc_run_month_started_at",
        "payroll_calc_run",
        ["payroll_month_id", sa.literal_column("started_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_payroll_calc_run_status",
        "payroll_calc_run",
        ["status"],
        unique=False,
    )
    op.create_table(
        "payroll_result",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payroll_month_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("position_id", sa.UUID(), nullable=False),
        sa.Column("dept_id", sa.UUID(), nullable=False),
        sa.Column("cost_org_id", sa.UUID(), nullable=True),
        sa.Column("calc_scheme_id", sa.UUID(), nullable=False),
        sa.Column(
            "position_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "position_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column(
            "dept_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "dept_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column(
            "cost_org_code",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=True,
        ),
        sa.Column(
            "cost_org_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("dept_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "cost_org_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "attendance_source",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["payroll_calc_run.id"],
            name="fk_payroll_result_calc_run_id_payroll_calc_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calc_scheme_id"],
            ["calc_scheme.id"],
            name="fk_payroll_result_calc_scheme_id_calc_scheme",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_payroll_result_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_payroll_result_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_result_payroll_month_id_payroll_month",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payroll_month_id",
            "employee_id",
            name="uq_payroll_result_month_employee",
        ),
    )
    op.create_index(
        "ix_payroll_result_company_cost_org_code",
        "payroll_result",
        ["company_id", "cost_org_code"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_company_dept_code",
        "payroll_result",
        ["company_id", "dept_code"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_cost_org_path_gin",
        "payroll_result",
        ["cost_org_path"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_payroll_result_dept_path_gin",
        "payroll_result",
        ["dept_path"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_payroll_result_month_cost_org_code",
        "payroll_result",
        ["payroll_month_id", "cost_org_code"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_month_cost_org_id",
        "payroll_result",
        ["payroll_month_id", "cost_org_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_month_dept_id",
        "payroll_result",
        ["payroll_month_id", "dept_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_month_position_id",
        "payroll_result",
        ["payroll_month_id", "position_id"],
        unique=False,
    )
    op.create_table(
        "payroll_result_value",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("result_id", sa.UUID(), nullable=False),
        sa.Column("field_def_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "plan",
                "import",
                "formula",
                "fixed",
                "manual",
                name="ck_payroll_result_value_source",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("produced_by_run_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_def_id"],
            ["salary_field_def.id"],
            name="fk_payroll_result_value_field_def_id_salary_field_def",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["produced_by_run_id"],
            ["payroll_calc_run.id"],
            name="fk_payroll_result_value_produced_by_run_id_payroll_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["payroll_result.id"],
            name="fk_payroll_result_value_result_id_payroll_result",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "result_id",
            "field_def_id",
            name="uq_payroll_result_value_result_field",
        ),
    )
    op.create_index(
        "ix_payroll_result_value_field_def_id",
        "payroll_result_value",
        ["field_def_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_result_value_produced_by_run_id",
        "payroll_result_value",
        ["produced_by_run_id"],
        unique=False,
    )
    op.create_table(
        "payroll_month_snapshot",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payroll_month_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_by", sa.UUID(), nullable=False),
        sa.Column(
            "paid_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "version >= 1", name="ck_payroll_month_snapshot_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["payroll_calc_run.id"],
            name="fk_payroll_month_snapshot_calc_run_id_payroll_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["paid_by"],
            ["user.id"],
            name="fk_payroll_month_snapshot_paid_by_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_month_snapshot_payroll_month_id_payroll_month",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payroll_month_id",
            "version",
            name="uq_payroll_month_snapshot_month_version",
        ),
    )
    op.create_table(
        "payroll_month_event",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payroll_month_id", sa.UUID(), nullable=False),
        sa.Column(
            "event",
            sa.Enum(
                "confirmed",
                "unconfirmed",
                "paid",
                "unlocked",
                name="ck_payroll_month_event_event",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
        ),
        sa.Column("calc_run_id", sa.UUID(), nullable=True),
        sa.Column("snapshot_id", sa.UUID(), nullable=True),
        sa.Column(
            "reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("operator_id", sa.UUID(), nullable=True),
        sa.Column(
            "operator_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["payroll_calc_run.id"],
            name="fk_payroll_month_event_calc_run_id_payroll_calc_run",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["user.id"],
            name="fk_payroll_month_event_operator_id_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_month_id"],
            ["payroll_month.id"],
            name="fk_payroll_month_event_payroll_month_id_payroll_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["payroll_month_snapshot.id"],
            name="fk_payroll_month_event_snapshot_id_payroll_month_snapshot",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payroll_month_event_month_created_at",
        "payroll_month_event",
        ["payroll_month_id", sa.literal_column("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payroll_month_event_month_created_at",
        table_name="payroll_month_event",
    )
    op.drop_table("payroll_month_event")
    op.drop_table("payroll_month_snapshot")
    op.drop_index(
        "ix_payroll_result_value_produced_by_run_id",
        table_name="payroll_result_value",
    )
    op.drop_index(
        "ix_payroll_result_value_field_def_id",
        table_name="payroll_result_value",
    )
    op.drop_table("payroll_result_value")
    op.drop_index(
        "ix_payroll_result_month_position_id", table_name="payroll_result"
    )
    op.drop_index("ix_payroll_result_month_dept_id", table_name="payroll_result")
    op.drop_index(
        "ix_payroll_result_month_cost_org_id", table_name="payroll_result"
    )
    op.drop_index(
        "ix_payroll_result_month_cost_org_code", table_name="payroll_result"
    )
    op.drop_index(
        "ix_payroll_result_dept_path_gin",
        table_name="payroll_result",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_payroll_result_cost_org_path_gin",
        table_name="payroll_result",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_payroll_result_company_dept_code", table_name="payroll_result"
    )
    op.drop_index(
        "ix_payroll_result_company_cost_org_code", table_name="payroll_result"
    )
    op.drop_table("payroll_result")
    op.drop_index(
        "ix_payroll_calc_run_status", table_name="payroll_calc_run"
    )
    op.drop_index(
        "ix_payroll_calc_run_month_started_at", table_name="payroll_calc_run"
    )
    op.drop_table("payroll_calc_run")
    op.drop_table("payroll_month")
