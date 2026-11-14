"""Attendance core tables

Revision ID: a7d1c3e5f901
Revises: d66acc907e93
Create Date: 2026-11-14 00:00:00.000000

All columns, constraints, indexes, and foreign-key behaviors follow
docs/specs/attendance-management.md sections 4.10, 4.12, and 12.
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a7d1c3e5f901"
down_revision = "d66acc907e93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shift",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "shift_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "shift_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("cross_day", sa.Boolean(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("rest_minutes", sa.Integer(), nullable=False),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(break_start IS NULL) = (break_end IS NULL)", name="ck_shift_break_pair"
        ),
        sa.CheckConstraint(
            "(cross_day AND end_time <= start_time) OR (NOT cross_day AND end_time > start_time)",
            name="ck_shift_cross_day",
        ),
        sa.CheckConstraint("rest_minutes >= 0", name="ck_shift_rest_minutes"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_shift_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "shift_code", name="uq_shift_company_shift_code"
        ),
    )
    op.create_table(
        "holiday",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "day_type",
            sa.Enum(
                "holiday",
                "adjusted_workday",
                name="ck_holiday_day_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_holiday_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "date", name="uq_holiday_company_date"),
    )
    op.create_index(
        "ix_holiday_company_date", "holiday", ["company_id", "date"], unique=False
    )
    op.create_table(
        "attendance_rule",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("punch_window_min", sa.Integer(), nullable=False),
        sa.Column("late_cap_min", sa.Integer(), nullable=False),
        sa.Column("early_cap_min", sa.Integer(), nullable=False),
        sa.Column("ot_max_min", sa.Integer(), nullable=False),
        sa.Column("late_grace_min", sa.Integer(), nullable=False),
        sa.Column("early_grace_min", sa.Integer(), nullable=False),
        sa.Column("ot_threshold_min", sa.Integer(), nullable=False),
        sa.Column("absent_if_no_punch", sa.Boolean(), nullable=False),
        sa.Column("break_punch_required", sa.Boolean(), nullable=False),
        sa.Column("break_punch_tolerance_min", sa.Integer(), nullable=False),
        sa.Column(
            "absent_deduct_per_day", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column(
            "late_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            "early_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            "missing_punch_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "absent_deduct_per_day >= 0",
            name="ck_attendance_rule_absent_deduct_per_day_non_negative",
        ),
        sa.CheckConstraint(
            "break_punch_tolerance_min >= 0",
            name="ck_attendance_rule_break_punch_tolerance_min_non_negative",
        ),
        sa.CheckConstraint(
            "early_cap_min >= 0", name="ck_attendance_rule_early_cap_min_non_negative"
        ),
        sa.CheckConstraint(
            "early_deduct_per_occurrence >= 0",
            name="ck_attendance_rule_early_deduct_per_occurrence_non_negative",
        ),
        sa.CheckConstraint(
            "early_grace_min >= 0",
            name="ck_attendance_rule_early_grace_min_non_negative",
        ),
        sa.CheckConstraint(
            "late_cap_min >= 0", name="ck_attendance_rule_late_cap_min_non_negative"
        ),
        sa.CheckConstraint(
            "late_deduct_per_occurrence >= 0",
            name="ck_attendance_rule_late_deduct_per_occurrence_non_negative",
        ),
        sa.CheckConstraint(
            "late_grace_min >= 0", name="ck_attendance_rule_late_grace_min_non_negative"
        ),
        sa.CheckConstraint(
            "missing_punch_deduct_per_occurrence >= 0",
            name="ck_attendance_rule_missing_punch_deduct_per_occ_non_negative",
        ),
        sa.CheckConstraint(
            "ot_max_min >= 0", name="ck_attendance_rule_ot_max_min_non_negative"
        ),
        sa.CheckConstraint(
            "ot_threshold_min >= 0",
            name="ck_attendance_rule_ot_threshold_min_non_negative",
        ),
        sa.CheckConstraint(
            "punch_window_min >= 0",
            name="ck_attendance_rule_punch_window_min_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_rule_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_attendance_rule_company"),
    )
    op.create_table(
        "attendance_month",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "calculated",
                "confirmed",
                "locked",
                name="ck_attendance_month_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unlock_reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_month_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "month", name="uq_attendance_month_company_month"
        ),
    )
    op.create_index(
        "ix_attendance_month_company_status",
        "attendance_month",
        ["company_id", "status"],
        unique=False,
    )
    op.create_table(
        "calc_run",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attendance_month_id", sa.UUID(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "initial",
                "manual",
                "reimport",
                "roster_change",
                "rule_change",
                "holiday_change",
                name="ck_calc_run_trigger",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "success",
                "failed",
                name="ck_calc_run_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "calc_version", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "rules_version", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column(
            "roster_version",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "rules_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "input_batches", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "error_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.Column(
            "error_message", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_month_id"],
            ["attendance_month.id"],
            name="fk_calc_run_attendance_month_id_attendance_month",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calc_run_month_started",
        "calc_run",
        ["attendance_month_id", "started_at"],
        unique=False,
    )
    op.create_table(
        "attendance_month_snapshot",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attendance_month_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_month_id"],
            ["attendance_month.id"],
            name="fk_attendance_month_snapshot_month_id_attendance_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["calc_run.id"],
            name="fk_attendance_month_snapshot_calc_run_id_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["locked_by"],
            ["user.id"],
            name="fk_attendance_month_snapshot_locked_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attendance_month_id",
            "version",
            name="uq_attendance_month_snapshot_month_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("attendance_month_snapshot")
    op.drop_table("calc_run")
    op.drop_table("attendance_month")
    op.drop_table("attendance_rule")
    op.drop_table("holiday")
    op.drop_table("shift")
