"""Payroll configuration tables

Revision ID: e1f2a3b4c5d6
Revises: d0a4f6b8c234
Create Date: 2026-11-28 00:00:00.000000

Nine configuration tables. All columns, constraints, indexes, and foreign-key
behaviors follow docs/specs/payroll-management.md sections 4.2-4.9, 4.22, and
16. The migration inserts no rows.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "d0a4f6b8c234"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "salary_field_def",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "field_key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "earning",
                "addon",
                "deduction",
                "total",
                "reference",
                name="ck_salary_field_def_category",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "calc_mode",
            sa.Enum(
                "plan",
                "import",
                "formula",
                "fixed",
                name="ck_salary_field_def_calc_mode",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "source_key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column("fixed_value", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("default_formula", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "field_key ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="ck_salary_field_def_field_key_pattern",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_key", name="uq_salary_field_def_field_key"),
        sa.UniqueConstraint("label", name="uq_salary_field_def_label"),
    )
    op.create_index(
        "ix_salary_field_def_category_display_order",
        "salary_field_def",
        ["category", "display_order"],
        unique=False,
    )
    op.create_index(
        "uq_salary_field_def_source_key",
        "salary_field_def",
        ["source_key"],
        unique=True,
        postgresql_where=sa.text("source_key IS NOT NULL"),
    )
    op.create_table(
        "compensation_composition",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "comp_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "comp_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "comp_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_compensation_composition_comp_code_pattern",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_compensation_composition_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "comp_code",
            name="uq_compensation_composition_company_comp_code",
        ),
    )
    op.create_index(
        "ix_compensation_composition_company_active",
        "compensation_composition",
        ["company_id", "is_active"],
        unique=False,
    )
    op.create_table(
        "compensation_composition_version",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("comp_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("base_salary", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("hightemp_subsidy", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "performance_salary", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("overtime_pay", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "confidentiality_allowance",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column("social_subsidy", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "noncompete_subsidy", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("total_package", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "change_note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "base_salary >= 0", name="ck_comp_ver_base_salary_non_negative"
        ),
        sa.CheckConstraint(
            "confidentiality_allowance >= 0",
            name="ck_comp_ver_confidentiality_allowance_non_negative",
        ),
        sa.CheckConstraint(
            "hightemp_subsidy >= 0",
            name="ck_comp_ver_hightemp_subsidy_non_negative",
        ),
        sa.CheckConstraint(
            "noncompete_subsidy >= 0",
            name="ck_comp_ver_noncompete_subsidy_non_negative",
        ),
        sa.CheckConstraint(
            "overtime_pay >= 0", name="ck_comp_ver_overtime_pay_non_negative"
        ),
        sa.CheckConstraint(
            "performance_salary >= 0",
            name="ck_comp_ver_performance_salary_non_negative",
        ),
        sa.CheckConstraint(
            "social_subsidy >= 0", name="ck_comp_ver_social_subsidy_non_negative"
        ),
        sa.CheckConstraint(
            "total_package = base_salary + hightemp_subsidy + performance_salary "
            "+ overtime_pay + confidentiality_allowance + social_subsidy "
            "+ noncompete_subsidy",
            name="ck_comp_ver_total_package_sum",
        ),
        sa.CheckConstraint("version_no >= 1", name="ck_comp_ver_version_positive"),
        sa.ForeignKeyConstraint(
            ["comp_id"],
            ["compensation_composition.id"],
            name="fk_comp_version_comp_id_compensation_composition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_compensation_composition_version_created_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comp_id",
            "version_no",
            name="uq_compensation_composition_version_comp_version",
        ),
    )
    op.create_table(
        "calc_scheme",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "calc_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "calc_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "calc_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_calc_scheme_calc_code_pattern",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_calc_scheme_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "calc_code", name="uq_calc_scheme_company_calc_code"
        ),
    )
    op.create_table(
        "calc_scheme_formula",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("calc_scheme_id", sa.UUID(), nullable=False),
        sa.Column("field_def_id", sa.UUID(), nullable=False),
        sa.Column("formula_expr", sa.Text(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calc_scheme_id"],
            ["calc_scheme.id"],
            name="fk_calc_scheme_formula_calc_scheme_id_calc_scheme",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["field_def_id"],
            ["salary_field_def.id"],
            name="fk_calc_scheme_formula_field_def_id_salary_field_def",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "calc_scheme_id",
            "field_def_id",
            name="uq_calc_scheme_formula_scheme_field",
        ),
    )
    op.create_index(
        "ix_calc_scheme_formula_field_def_id",
        "calc_scheme_formula",
        ["field_def_id"],
        unique=False,
    )
    op.create_table(
        "workday_param",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column(
            "workday_code", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "workday_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("avg_pay_days", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("work_hours", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("ot_mult_weekday", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("ot_mult_weekend", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("ot_mult_holiday", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("min_wage", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "min_wage_note",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "workday_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_workday_param_workday_code_pattern",
        ),
        sa.CheckConstraint(
            "avg_pay_days > 0", name="ck_workday_param_avg_pay_days_positive"
        ),
        sa.CheckConstraint("min_wage >= 0", name="ck_workday_param_min_wage_non_negative"),
        sa.CheckConstraint(
            "ot_mult_holiday >= 1", name="ck_workday_param_ot_mult_holiday_min"
        ),
        sa.CheckConstraint(
            "ot_mult_weekday >= 1", name="ck_workday_param_ot_mult_weekday_min"
        ),
        sa.CheckConstraint(
            "ot_mult_weekend >= 1", name="ck_workday_param_ot_mult_weekend_min"
        ),
        sa.CheckConstraint(
            "work_hours > 0", name="ck_workday_param_work_hours_positive"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_workday_param_company_id_company",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "workday_code",
            name="uq_workday_param_company_workday_code",
        ),
    )
    op.create_table(
        "position_payroll_config",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("position_id", sa.UUID(), nullable=False),
        sa.Column("comp_id", sa.UUID(), nullable=False),
        sa.Column("calc_scheme_id", sa.UUID(), nullable=False),
        sa.Column("workday_param_id", sa.UUID(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calc_scheme_id"],
            ["calc_scheme.id"],
            name="fk_position_payroll_config_calc_scheme_id_calc_scheme",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["comp_id"],
            ["compensation_composition.id"],
            name="fk_position_payroll_config_comp_id_compensation_composition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["position.id"],
            name="fk_position_payroll_config_position_id_position",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workday_param_id"],
            ["workday_param.id"],
            name="fk_position_payroll_config_workday_param_id_workday_param",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "position_id", name="uq_position_payroll_config_position_id"
        ),
    )
    op.create_index(
        "ix_position_payroll_config_calc_scheme_id",
        "position_payroll_config",
        ["calc_scheme_id"],
        unique=False,
    )
    op.create_index(
        "ix_position_payroll_config_comp_id",
        "position_payroll_config",
        ["comp_id"],
        unique=False,
    )
    op.create_index(
        "ix_position_payroll_config_workday_param_id",
        "position_payroll_config",
        ["workday_param_id"],
        unique=False,
    )
    op.create_table(
        "payroll_global_param",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "category", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False
        ),
        sa.Column(
            "value_type",
            sa.Enum(
                "number",
                "json",
                name="ck_payroll_global_param_value_type",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("numeric_value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column(
            "json_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(value_type = 'number' AND numeric_value IS NOT NULL "
            "AND json_value IS NULL) "
            "OR (value_type = 'json' AND numeric_value IS NULL "
            "AND json_value IS NOT NULL)",
            name="ck_payroll_global_param_value_exclusive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_payroll_global_param_key"),
    )
    op.create_table(
        "payroll_config_revision",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "compensation_composition",
                "calc_scheme",
                "workday_param",
                "salary_field_def",
                "payroll_global_param",
                "position_payroll_config",
                name="ck_payroll_config_revision_entity_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "change_note", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("changed_by", sa.UUID(), nullable=True),
        sa.Column(
            "changed_by_name",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "version_no >= 1",
            name="ck_payroll_config_revision_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["user.id"],
            name="fk_payroll_config_revision_changed_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "version_no",
            name="uq_payroll_config_revision_entity_version",
        ),
    )
    op.create_index(
        "ix_payroll_config_revision_entity",
        "payroll_config_revision",
        ["entity_type", "entity_id", sa.literal_column("changed_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payroll_config_revision_entity",
        table_name="payroll_config_revision",
    )
    op.drop_table("payroll_config_revision")
    op.drop_table("payroll_global_param")
    op.drop_index(
        "ix_position_payroll_config_workday_param_id",
        table_name="position_payroll_config",
    )
    op.drop_index(
        "ix_position_payroll_config_comp_id",
        table_name="position_payroll_config",
    )
    op.drop_index(
        "ix_position_payroll_config_calc_scheme_id",
        table_name="position_payroll_config",
    )
    op.drop_table("position_payroll_config")
    op.drop_table("workday_param")
    op.drop_index(
        "ix_calc_scheme_formula_field_def_id",
        table_name="calc_scheme_formula",
    )
    op.drop_table("calc_scheme_formula")
    op.drop_table("calc_scheme")
    op.drop_table("compensation_composition_version")
    op.drop_index(
        "ix_compensation_composition_company_active",
        table_name="compensation_composition",
    )
    op.drop_table("compensation_composition")
    op.drop_index(
        "uq_salary_field_def_source_key",
        table_name="salary_field_def",
        postgresql_where=sa.text("source_key IS NOT NULL"),
    )
    op.drop_index(
        "ix_salary_field_def_category_display_order",
        table_name="salary_field_def",
    )
    op.drop_table("salary_field_def")
