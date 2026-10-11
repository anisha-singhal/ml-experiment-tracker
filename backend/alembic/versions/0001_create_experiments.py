"""create experiments table

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model_type", sa.String(length=60), nullable=False),
        sa.Column("dataset", sa.String(length=120), nullable=False),
        sa.Column("learning_rate", sa.Float(), nullable=False, server_default="0.001"),
        sa.Column("epochs", sa.Integer(), nullable=False, server_default="10"),
        # nullable: a queued run has no result yet, which is different from 0.0
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Both columns the UI filters and sorts on.
    op.create_index("ix_experiments_name", "experiments", ["name"])
    op.create_index("ix_experiments_status", "experiments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_experiments_status", table_name="experiments")
    op.drop_index("ix_experiments_name", table_name="experiments")
    op.drop_table("experiments")
