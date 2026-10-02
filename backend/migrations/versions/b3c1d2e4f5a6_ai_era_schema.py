"""ai era schema: user preferences, transaction provenance, indexes

Revision ID: b3c1d2e4f5a6
Revises: 7fef2427edd8
Create Date: 2026-10-03 00:30:00.000000

Additive and backwards-compatible: every new column is nullable or has a server
default, so code from before this migration keeps working against the new schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c1d2e4f5a6"
down_revision: str | Sequence[str] | None = "7fef2427edd8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transaction_source = sa.Enum("manual", "chat", "import", "schedule", name="transaction_source")


def upgrade() -> None:
    """Upgrade schema."""
    # --- users: preferences ---
    op.add_column(
        "users",
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
    )

    # --- transactions: updated_at (backfilled from created_at, then NOT NULL) ---
    op.add_column(
        "transactions",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.execute("UPDATE transactions SET updated_at = created_at")
    op.alter_column("transactions", "updated_at", nullable=False)

    # --- transactions: provenance ---
    # add_column doesn't emit CREATE TYPE, so create the PG enum explicitly
    transaction_source.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "transactions",
        sa.Column("source", transaction_source, server_default="manual", nullable=False),
    )
    op.add_column("transactions", sa.Column("import_batch_id", sa.Integer(), nullable=True))

    # --- transactions: indexes for per-user date / category queries ---
    op.create_index("ix_transactions_user_id_date", "transactions", ["user_id", "date"])
    op.create_index(
        "ix_transactions_user_id_category_id", "transactions", ["user_id", "category_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_user_id_category_id", table_name="transactions")
    op.drop_index("ix_transactions_user_id_date", table_name="transactions")
    op.drop_column("transactions", "import_batch_id")
    op.drop_column("transactions", "source")
    transaction_source.drop(op.get_bind(), checkfirst=True)
    op.drop_column("transactions", "updated_at")
    op.drop_column("users", "timezone")
    op.drop_column("users", "currency")
