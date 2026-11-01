"""Create basic management tables

Revision ID: cb05be899084
Revises: fe56fa70289e
Create Date: 2026-11-01 23:05:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cb05be899084"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("company_code", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_code", name="uq_company_company_code"),
    )

    op.create_table(
        "department",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("dept_code", sa.String(length=32), nullable=False),
        sa.Column("dept_name", sa.String(length=100), nullable=False),
        sa.Column("company_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_department_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["department.id"],
            name="fk_department_parent_id_department",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "dept_code", name="uq_department_company_dept_code"
        ),
    )
    op.create_index(
        "ix_department_company_id", "department", ["company_id"], unique=False
    )
    op.create_index(
        "ix_department_parent_id", "department", ["parent_id"], unique=False
    )
    op.create_index(
        "ix_department_manager_id", "department", ["manager_id"], unique=False
    )

    op.create_table(
        "position",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("position_code", sa.String(length=32), nullable=False),
        sa.Column("position_name", sa.String(length=100), nullable=False),
        sa.Column("company_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("dept_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_position_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"],
            ["department.id"],
            name="fk_position_dept_id_department",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "position_code",
            name="uq_position_company_position_code",
        ),
    )
    op.create_index(
        "ix_position_company_id", "position", ["company_id"], unique=False
    )
    op.create_index(
        "ix_position_dept_id", "position", ["dept_id"], unique=False
    )

    op.create_table(
        "cost_center",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_org_code", sa.String(length=32), nullable=False),
        sa.Column("cost_org_name", sa.String(length=100), nullable=False),
        sa.Column("company_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("budget", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("warn_pct", sa.Integer(), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "budget >= 0", name="ck_cost_center_budget_non_negative"
        ),
        sa.CheckConstraint(
            "warn_pct BETWEEN 1 AND 100", name="ck_cost_center_warn_pct_range"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_cost_center_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["cost_center.id"],
            name="fk_cost_center_parent_id_cost_center",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "cost_org_code",
            name="uq_cost_center_company_cost_org_code",
        ),
    )
    op.create_index(
        "ix_cost_center_company_id", "cost_center", ["company_id"], unique=False
    )
    op.create_index(
        "ix_cost_center_parent_id", "cost_center", ["parent_id"], unique=False
    )
    op.create_index(
        "ix_cost_center_manager_id", "cost_center", ["manager_id"], unique=False
    )

    op.create_table(
        "employee",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_no", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "gender",
            sa.Enum(
                "male",
                "female",
                "unknown",
                name="ck_employee_gender",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("dept_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_org_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "probation",
                "resigned",
                name="ck_employee_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("resign_date", sa.Date(), nullable=True),
        sa.Column(
            "contract_type",
            sa.Enum(
                "full_time",
                "part_time",
                "intern",
                "labor",
                name="ck_employee_contract_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("daily_hours", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("monthly_rest", sa.Integer(), nullable=True),
        sa.Column("confidentiality_level", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "daily_hours IS NULL OR (daily_hours > 0 AND daily_hours <= 24)",
            name="ck_employee_daily_hours_range",
        ),
        sa.CheckConstraint(
            "monthly_rest IS NULL OR monthly_rest >= 0",
            name="ck_employee_monthly_rest_non_negative",
        ),
        sa.CheckConstraint(
            "confidentiality_level IS NULL "
            "OR confidentiality_level BETWEEN 1 AND 5",
            name="ck_employee_confidentiality_level_range",
        ),
        sa.CheckConstraint(
            "resign_date IS NULL OR resign_date >= hire_date",
            name="ck_employee_resign_date_after_hire",
        ),
        sa.CheckConstraint(
            "(status = 'resigned') = (resign_date IS NOT NULL)",
            name="ck_employee_resigned_date_required",
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"],
            ["department.id"],
            name="fk_employee_dept_id_department",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["position.id"],
            name="fk_employee_position_id_position",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cost_org_id"],
            ["cost_center.id"],
            name="fk_employee_cost_org_id_cost_center",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_no", name="uq_employee_employee_no"),
    )
    op.create_index(
        "ix_employee_dept_id", "employee", ["dept_id"], unique=False
    )
    op.create_index(
        "ix_employee_position_id", "employee", ["position_id"], unique=False
    )
    op.create_index(
        "ix_employee_cost_org_id", "employee", ["cost_org_id"], unique=False
    )
    op.create_index(
        "ix_employee_manager_id", "employee", ["manager_id"], unique=False
    )
    op.create_index("ix_employee_status", "employee", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_employee_status", table_name="employee")
    op.drop_index("ix_employee_manager_id", table_name="employee")
    op.drop_index("ix_employee_cost_org_id", table_name="employee")
    op.drop_index("ix_employee_position_id", table_name="employee")
    op.drop_index("ix_employee_dept_id", table_name="employee")
    op.drop_table("employee")

    op.drop_index("ix_cost_center_manager_id", table_name="cost_center")
    op.drop_index("ix_cost_center_parent_id", table_name="cost_center")
    op.drop_index("ix_cost_center_company_id", table_name="cost_center")
    op.drop_table("cost_center")

    op.drop_index("ix_position_dept_id", table_name="position")
    op.drop_index("ix_position_company_id", table_name="position")
    op.drop_table("position")

    op.drop_index("ix_department_manager_id", table_name="department")
    op.drop_index("ix_department_parent_id", table_name="department")
    op.drop_index("ix_department_company_id", table_name="department")
    op.drop_table("department")

    op.drop_table("company")
