"""Attendance scheduling tables

Revision ID: b8e2d4f6a012
Revises: a7d1c3e5f901
Create Date: 2026-11-14 00:00:00.000000

All columns, constraints, indexes, and foreign-key behaviors follow
docs/specs/attendance-management.md sections 4.10, 4.12, and 12.
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8e2d4f6a012"
down_revision = "a7d1c3e5f901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_plan",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column(
            "plan_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column(
            "scope_type",
            sa.Enum(
                "all",
                "dept",
                "position",
                "employee",
                name="ck_schedule_plan_scope_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "enabled",
                "archived",
                name="ck_schedule_plan_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("copied_from_plan_id", sa.UUID(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_schedule_plan_month_first_day"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_schedule_plan_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_plan_id"],
            ["schedule_plan.id"],
            name="fk_schedule_plan_copied_from_plan_id_schedule_plan",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_plan_company_month_status",
        "schedule_plan",
        ["company_id", "month", "status"],
        unique=False,
    )
    op.create_table(
        "plan_scope",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("scope_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["schedule_plan.id"],
            name="fk_plan_scope_plan_id_schedule_plan",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "scope_id", name="uq_plan_scope_plan_scope_id"),
    )
    op.create_table(
        "plan_day",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "day_of_month BETWEEN 1 AND 31", name="ck_plan_day_day_of_month_range"
        ),
        sa.CheckConstraint("seq >= 0", name="ck_plan_day_seq_non_negative"),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["schedule_plan.id"],
            name="fk_plan_day_plan_id_schedule_plan",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shift.id"],
            name="fk_plan_day_shift_id_shift",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id", "day_of_month", "seq", name="uq_plan_day_plan_day_seq"
        ),
        sa.UniqueConstraint(
            "plan_id", "day_of_month", "shift_id", name="uq_plan_day_plan_day_shift"
        ),
    )
    op.create_table(
        "plan_rule_override",
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("punch_window_min", sa.Integer(), nullable=True),
        sa.Column("late_cap_min", sa.Integer(), nullable=True),
        sa.Column("early_cap_min", sa.Integer(), nullable=True),
        sa.Column("ot_max_min", sa.Integer(), nullable=True),
        sa.Column("late_grace_min", sa.Integer(), nullable=True),
        sa.Column("early_grace_min", sa.Integer(), nullable=True),
        sa.Column("ot_threshold_min", sa.Integer(), nullable=True),
        sa.Column("absent_if_no_punch", sa.Boolean(), nullable=True),
        sa.Column("break_punch_required", sa.Boolean(), nullable=True),
        sa.Column("break_punch_tolerance_min", sa.Integer(), nullable=True),
        sa.Column(
            "absent_deduct_per_day", sa.Numeric(precision=14, scale=2), nullable=True
        ),
        sa.Column(
            "late_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column(
            "early_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column(
            "missing_punch_deduct_per_occurrence",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.CheckConstraint(
            "absent_deduct_per_day IS NULL OR absent_deduct_per_day >= 0",
            name="ck_plan_rule_override_absent_deduct_per_day_non_negative",
        ),
        sa.CheckConstraint(
            "break_punch_tolerance_min IS NULL OR break_punch_tolerance_min >= 0",
            name="ck_plan_rule_override_break_punch_tolerance_min_non_negative",
        ),
        sa.CheckConstraint(
            "early_cap_min IS NULL OR early_cap_min >= 0",
            name="ck_plan_rule_override_early_cap_min_non_negative",
        ),
        sa.CheckConstraint(
            "early_deduct_per_occurrence IS NULL OR early_deduct_per_occurrence >= 0",
            name="ck_plan_rule_override_early_deduct_per_occurrence_non_negative",
        ),
        sa.CheckConstraint(
            "early_grace_min IS NULL OR early_grace_min >= 0",
            name="ck_plan_rule_override_early_grace_min_non_negative",
        ),
        sa.CheckConstraint(
            "late_cap_min IS NULL OR late_cap_min >= 0",
            name="ck_plan_rule_override_late_cap_min_non_negative",
        ),
        sa.CheckConstraint(
            "late_deduct_per_occurrence IS NULL OR late_deduct_per_occurrence >= 0",
            name="ck_plan_rule_override_late_deduct_per_occurrence_non_negative",
        ),
        sa.CheckConstraint(
            "late_grace_min IS NULL OR late_grace_min >= 0",
            name="ck_plan_rule_override_late_grace_min_non_negative",
        ),
        sa.CheckConstraint(
            "missing_punch_deduct_per_occurrence IS NULL OR missing_punch_deduct_per_occurrence >= 0",
            name="ck_plan_rule_override_missing_punch_deduct_per_occ_non_negative",
        ),
        sa.CheckConstraint(
            "ot_max_min IS NULL OR ot_max_min >= 0",
            name="ck_plan_rule_override_ot_max_min_non_negative",
        ),
        sa.CheckConstraint(
            "ot_threshold_min IS NULL OR ot_threshold_min >= 0",
            name="ck_plan_rule_override_ot_threshold_min_non_negative",
        ),
        sa.CheckConstraint(
            "punch_window_min IS NULL OR punch_window_min >= 0",
            name="ck_plan_rule_override_punch_window_min_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["schedule_plan.id"],
            name="fk_plan_rule_override_plan_id_schedule_plan",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("plan_id"),
    )
    op.create_table(
        "roster_entry",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "work",
                "rest",
                name="ck_roster_entry_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "plan",
                "manual",
                name="ck_roster_entry_source",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_roster_entry_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_roster_entry_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["schedule_plan.id"],
            name="fk_roster_entry_plan_id_schedule_plan",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id", "work_date", name="uq_roster_entry_employee_date"
        ),
    )
    op.create_index(
        "ix_roster_entry_company_date",
        "roster_entry",
        ["company_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_roster_entry_employee_date",
        "roster_entry",
        ["employee_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_roster_entry_plan_id", "roster_entry", ["plan_id"], unique=False
    )
    op.create_table(
        "roster_entry_shift",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("roster_entry_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("seq >= 0", name="ck_roster_entry_shift_seq_non_negative"),
        sa.ForeignKeyConstraint(
            ["roster_entry_id"],
            ["roster_entry.id"],
            name="fk_roster_entry_shift_roster_entry_id_roster_entry",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shift.id"],
            name="fk_roster_entry_shift_shift_id_shift",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "roster_entry_id", "seq", name="uq_roster_entry_shift_entry_seq"
        ),
    )


def downgrade() -> None:
    op.drop_table("roster_entry_shift")
    op.drop_table("roster_entry")
    op.drop_table("plan_rule_override")
    op.drop_table("plan_day")
    op.drop_table("plan_scope")
    op.drop_table("schedule_plan")
