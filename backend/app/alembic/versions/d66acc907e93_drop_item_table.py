"""Drop item table

Revision ID: d66acc907e93
Revises: 685e4091a8e5
Create Date: 2026-11-01 23:07:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d66acc907e93"
down_revision = "685e4091a8e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("item")


def downgrade() -> None:
    # The Items demo was removed in the previous release. Downgrade only
    # restores an empty table; dropped item data is not recoverable.
    op.create_table(
        "item",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("owner_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user.id"],
            name="item_owner_id_fkey",
            ondelete="CASCADE",
        ),
    )
