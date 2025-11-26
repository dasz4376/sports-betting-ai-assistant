"""add_sacks_taken_and_offensive_negatives

Revision ID: d824255d4d9a
Revises: bcb02064144f
Create Date: 2025-11-25 19:25:03.415940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd824255d4d9a'
down_revision: Union[str, None] = 'bcb02064144f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sacks_taken to player_stats (offensive negative stat)
    op.add_column('player_stats', sa.Column('sacks_taken', sa.Float(), nullable=True, server_default='0'))
    
    # Rename defensive stat columns FIRST to avoid conflicts (add _def suffix)
    op.alter_column('stats_features', 'avg_sacks', new_column_name='avg_sacks_def')
    op.alter_column('stats_features', 'avg_interceptions', new_column_name='avg_interceptions_def')
    op.alter_column('stats_features', 'total_sacks', new_column_name='total_sacks_def')
    op.alter_column('stats_features', 'total_interceptions', new_column_name='total_interceptions_def')
    
    # Now add offensive negative stats to stats_features (using the original names for offense)
    op.add_column('stats_features', sa.Column('avg_interceptions', sa.Float(), nullable=True, server_default='0'))
    op.add_column('stats_features', sa.Column('avg_sacks_taken', sa.Float(), nullable=True, server_default='0'))
    op.add_column('stats_features', sa.Column('total_interceptions', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('stats_features', sa.Column('total_sacks_taken', sa.Float(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Drop offensive negative stats FIRST
    op.drop_column('stats_features', 'total_sacks_taken')
    op.drop_column('stats_features', 'total_interceptions')
    op.drop_column('stats_features', 'avg_sacks_taken')
    op.drop_column('stats_features', 'avg_interceptions')
    
    # Reverse column renames (defensive stats back to original names)
    op.alter_column('stats_features', 'total_interceptions_def', new_column_name='total_interceptions')
    op.alter_column('stats_features', 'total_sacks_def', new_column_name='total_sacks')
    op.alter_column('stats_features', 'avg_interceptions_def', new_column_name='avg_interceptions')
    op.alter_column('stats_features', 'avg_sacks_def', new_column_name='avg_sacks')
    
    # Drop sacks_taken from player_stats
    op.drop_column('player_stats', 'sacks_taken')
