"""Add manager foreign keys

Revision ID: 685e4091a8e5
Revises: cb05be899084
Create Date: 2026-11-01 23:06:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "685e4091a8e5"
down_revision = "cb05be899084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The manager columns and the employee table are created in separate
    # migrations because department/cost_center reference employee while
    # employee references department/cost_center. Splitting the manager keys
    # avoids circular foreign keys inside a single CREATE TABLE statement.
    op.create_foreign_key(
        "fk_department_manager_id_employee",
        "department",
        "employee",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_cost_center_manager_id_employee",
        "cost_center",
        "employee",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_employee_manager_id_employee",
        "employee",
        "employee",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_employee_manager_id_employee", "employee", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_cost_center_manager_id_employee", "cost_center", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_department_manager_id_employee", "department", type_="foreignkey"
    )
