"""add default categories

Revision ID: 7fef2427edd8
Revises: 4eedc669f0a4
Create Date: 2026-08-29 18:15:26.949052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fef2427edd8'
down_revision: Union[str, Sequence[str], None] = '4eedc669f0a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    categories = sa.table(
        "categories",
        sa.column("name", sa.String()),
        sa.column("category_type", sa.String()),
        sa.column("user_id", sa.Integer()),
    )

    op.bulk_insert(
        categories,
        [
            {'name': 'Awards', 'category_type': 'income', 'user_id': None},
            {'name': 'Coupons', 'category_type': 'income', 'user_id': None},
            {'name': 'Grants', 'category_type': 'income', 'user_id': None},
            {'name': 'Lottery', 'category_type': 'income', 'user_id': None},
            {'name': 'Refunds', 'category_type': 'income', 'user_id': None},
            {'name': 'Rental', 'category_type': 'income', 'user_id': None},
            {'name': 'Salary', 'category_type': 'income', 'user_id': None},
            {'name': 'Sale', 'category_type': 'income', 'user_id': None},
            {'name': 'Bills', 'category_type': 'expense', 'user_id': None},
            {'name': 'Clothing', 'category_type': 'expense', 'user_id': None},
            {'name': 'Education', 'category_type': 'expense', 'user_id': None},
            {'name': 'Electronics', 'category_type': 'expense', 'user_id': None},
            {'name': 'Entertainment', 'category_type': 'expense', 'user_id': None},
            {'name': 'Food', 'category_type': 'expense', 'user_id': None},
            {'name': 'Health', 'category_type': 'expense', 'user_id': None},
            {'name': 'Shopping', 'category_type': 'expense', 'user_id': None},
            {'name': 'Sport', 'category_type': 'expense', 'user_id': None},
            {'name': 'Transportation', 'category_type': 'expense', 'user_id': None}
        ]
    )




def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DELETE FROM categories
        WHERE user_id IS NULL
        """
    )
