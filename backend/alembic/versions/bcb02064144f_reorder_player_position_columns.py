"""reorder_player_position_columns

Revision ID: bcb02064144f
Revises: 2372dbebac6b
Create Date: 2025-11-25 18:51:42.714784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcb02064144f'
down_revision: Union[str, None] = '2372dbebac6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: PostgreSQL doesn't support reordering columns after table creation.
    # The logical order in models.py has been updated to show player_position 
    # right after player_name, which is what matters for the application and AI.
    # The physical database column order remains unchanged, but this doesn't affect functionality.
    pass


def downgrade() -> None:
    # No physical changes were made
    pass
