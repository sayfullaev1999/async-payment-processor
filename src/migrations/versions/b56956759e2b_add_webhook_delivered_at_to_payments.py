"""add webhook_delivered_at to payments

Revision ID: b56956759e2b
Revises: d9ad3ded5fb8
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b56956759e2b'
down_revision: Union[str, Sequence[str], None] = 'd9ad3ded5fb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'payments',
        sa.Column('webhook_delivered_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('payments', 'webhook_delivered_at')
