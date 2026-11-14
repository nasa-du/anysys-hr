"""Attendance results tables

Revision ID: d0a4f6b8c234
Revises: c9f3e5a7b123
Create Date: 2026-11-14 00:00:00.000000

All columns, constraints, indexes, and foreign-key behaviors follow
docs/specs/attendance-management.md sections 4.10, 4.12, and 12.
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d0a4f6b8c234"
down_revision = "c9f3e5a7b123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_day_result",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("attendance_month_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column(
            "day_type",
            sa.Enum(
                "workday",
                "weekend",
                "holiday",
                name="ck_attendance_day_result_day_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "roster_state",
            sa.Enum(
                "work",
                "rest",
                "unscheduled",
                name="ck_attendance_day_result_roster_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "day_status",
            sa.Enum(
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
                name="ck_attendance_day_result_day_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("day_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "attendance_fraction", sa.Numeric(precision=3, scale=1), nullable=False
        ),
        sa.Column("scheduled_minutes", sa.Integer(), nullable=False),
        sa.Column("worked_minutes", sa.Integer(), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("early_minutes", sa.Integer(), nullable=False),
        sa.Column("late_count", sa.Integer(), nullable=False),
        sa.Column("early_count", sa.Integer(), nullable=False),
        sa.Column("missing_punch_count", sa.Integer(), nullable=False),
        sa.Column(
            "leave_kind",
            sa.Enum(
                "paid",
                "unpaid",
                "comp",
                name="ck_attendance_day_result_leave_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("leave_days", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("paid_leave_days", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column(
            "unpaid_leave_days", sa.Numeric(precision=3, scale=1), nullable=False
        ),
        sa.Column("comp_leave_days", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column(
            "trip_kind",
            sa.Enum(
                "out",
                "business",
                name="ck_attendance_day_result_trip_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("trip_fraction", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("ot_weekday_minutes", sa.Integer(), nullable=False),
        sa.Column("ot_weekend_minutes", sa.Integer(), nullable=False),
        sa.Column("ot_holiday_minutes", sa.Integer(), nullable=False),
        sa.Column("comp_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("comp_offset_unused_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "absent_deduct_amount", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column(
            "late_deduct_amount", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column(
            "early_deduct_amount", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column(
            "missing_punch_deduct_amount",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column("deduction_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("is_adjusted", sa.Boolean(), nullable=False),
        sa.Column("adjustment_id", sa.UUID(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_month_id"],
            ["attendance_month.id"],
            name="fk_attendance_day_result_attendance_month_id_attendance_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["calc_run.id"],
            name="fk_attendance_day_result_calc_run_id_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_day_result_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_attendance_day_result_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attendance_month_id",
            "employee_id",
            "work_date",
            name="uq_attendance_day_result_month_employee_date",
        ),
    )
    op.create_index(
        "ix_attendance_day_result_calc_run",
        "attendance_day_result",
        ["calc_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_day_result_company_date",
        "attendance_day_result",
        ["company_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_day_result_employee_date",
        "attendance_day_result",
        ["employee_id", "work_date"],
        unique=False,
    )
    op.create_table(
        "attendance_day_shift_result",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("day_result_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
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
        sa.Column(
            "shift_status",
            sa.Enum(
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
                name="ck_attendance_day_shift_result_shift_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "shift_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("punch_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("punch_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_minutes", sa.Integer(), nullable=False),
        sa.Column("worked_minutes", sa.Integer(), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("early_minutes", sa.Integer(), nullable=False),
        sa.Column("missing_punch_count", sa.Integer(), nullable=False),
        sa.Column("ot_minutes", sa.Integer(), nullable=False),
        sa.Column("comp_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("leave_days", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["calc_run.id"],
            name="fk_attendance_day_shift_result_calc_run_id_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_day_shift_result_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["day_result_id"],
            ["attendance_day_result.id"],
            name="fk_attendance_day_shift_result_day_id_attendance_day_result",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_attendance_day_shift_result_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "day_result_id", "seq", name="uq_attendance_day_shift_result_day_seq"
        ),
    )
    op.create_index(
        "ix_attendance_day_shift_result_calc_run",
        "attendance_day_shift_result",
        ["calc_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_day_shift_result_employee_date",
        "attendance_day_shift_result",
        ["employee_id", "work_date"],
        unique=False,
    )
    op.create_table(
        "attendance_month_summary",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("attendance_month_id", sa.UUID(), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("weekday_full", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("weekend_full", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("weekday_attended", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("weekend_attended", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("paid_leave_days", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column(
            "unpaid_leave_days", sa.Numeric(precision=5, scale=1), nullable=False
        ),
        sa.Column("comp_leave_days", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("trip_days", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("ot_weekday_minutes", sa.Integer(), nullable=False),
        sa.Column("ot_weekend_minutes", sa.Integer(), nullable=False),
        sa.Column("ot_holiday_minutes", sa.Integer(), nullable=False),
        sa.Column("ot_weekday_hours", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("ot_weekend_hours", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("ot_holiday_hours", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column(
            "comp_leave_used_hours", sa.Numeric(precision=7, scale=2), nullable=False
        ),
        sa.Column("comp_offset_unused_minutes", sa.Integer(), nullable=False),
        sa.Column("late_count", sa.Integer(), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("early_count", sa.Integer(), nullable=False),
        sa.Column("early_minutes", sa.Integer(), nullable=False),
        sa.Column("missing_punch_count", sa.Integer(), nullable=False),
        sa.Column("absent_days", sa.Integer(), nullable=False),
        sa.Column("worked_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "attendance_deduct", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("is_adjusted", sa.Boolean(), nullable=False),
        sa.Column(
            "calc_version", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "rules_version", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_month_id"],
            ["attendance_month.id"],
            name="fk_attendance_month_summary_month_id_attendance_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["calc_run.id"],
            name="fk_attendance_month_summary_calc_run_id_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_month_summary_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_attendance_month_summary_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attendance_month_id",
            "employee_id",
            name="uq_attendance_month_summary_month_employee",
        ),
    )
    op.create_index(
        "ix_attendance_month_summary_calc_run",
        "attendance_month_summary",
        ["calc_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_month_summary_company_employee",
        "attendance_month_summary",
        ["company_id", "employee_id"],
        unique=False,
    )
    op.create_table(
        "attendance_result_adjustment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("attendance_month_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "superseded",
                "orphaned",
                name="ck_attendance_result_adjustment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "original_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "adjusted_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False
        ),
        sa.Column("adjusted_by", sa.UUID(), nullable=False),
        sa.Column("adjusted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calc_run_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["adjusted_by"],
            ["user.id"],
            name="fk_attendance_result_adjustment_adjusted_by_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_month_id"],
            ["attendance_month.id"],
            name="fk_attendance_result_adjustment_month_id_attendance_month",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calc_run_id"],
            ["calc_run.id"],
            name="fk_attendance_result_adjustment_calc_run_id_calc_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_attendance_result_adjustment_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name="fk_attendance_result_adjustment_employee_id_employee",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_attendance_result_adjustment_month_employee_date_active",
        "attendance_result_adjustment",
        ["attendance_month_id", "employee_id", "work_date"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("attendance_result_adjustment")
    op.drop_table("attendance_month_summary")
    op.drop_table("attendance_day_shift_result")
    op.drop_table("attendance_day_result")
