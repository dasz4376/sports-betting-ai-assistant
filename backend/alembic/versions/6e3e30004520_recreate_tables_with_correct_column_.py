"""recreate_tables_with_correct_column_order

Revision ID: 6e3e30004520
Revises: d824255d4d9a
Create Date: 2025-11-25 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6e3e30004520'
down_revision: Union[str, None] = 'd824255d4d9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables (this will delete all data - we'll backfill after)
    op.drop_table('player_stats')
    op.drop_table('stats_features')
    
    # Recreate player_stats with correct column order
    op.create_table(
        'player_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(), nullable=True),
        sa.Column('player_position', sa.String(), nullable=True),
        sa.Column('game_id', sa.Integer(), nullable=False),
        
        # Offensive Stats
        sa.Column('passing_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('passing_completions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('passing_attempts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('passing_touchdowns', sa.Integer(), server_default='0', nullable=True),
        sa.Column('interceptions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('sacks_taken', sa.Float(), server_default='0', nullable=True),
        
        sa.Column('rushing_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('rushing_attempts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('rushing_touchdowns', sa.Integer(), server_default='0', nullable=True),
        
        sa.Column('receptions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('receiving_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('receiving_targets', sa.Integer(), server_default='0', nullable=True),
        sa.Column('receiving_touchdowns', sa.Integer(), server_default='0', nullable=True),
        
        # Defensive Stats
        sa.Column('tackles_total', sa.Integer(), server_default='0', nullable=True),
        sa.Column('tackles_solo', sa.Integer(), server_default='0', nullable=True),
        sa.Column('tackles_for_loss', sa.Integer(), server_default='0', nullable=True),
        sa.Column('sacks', sa.Float(), server_default='0', nullable=True),
        sa.Column('qb_hits', sa.Integer(), server_default='0', nullable=True),
        sa.Column('interceptions_def', sa.Integer(), server_default='0', nullable=True),
        sa.Column('pass_deflections', sa.Integer(), server_default='0', nullable=True),
        sa.Column('forced_fumbles', sa.Integer(), server_default='0', nullable=True),
        sa.Column('fumble_recoveries', sa.Integer(), server_default='0', nullable=True),
        sa.Column('defensive_tds', sa.Integer(), server_default='0', nullable=True),
        sa.Column('safeties', sa.Integer(), server_default='0', nullable=True),
        
        # Additional Stats
        sa.Column('fumbles', sa.Integer(), server_default='0', nullable=True),
        sa.Column('fumbles_lost', sa.Integer(), server_default='0', nullable=True),
        sa.Column('snaps', sa.Integer(), nullable=True),
        sa.Column('routes_run', sa.Integer(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], )
    )
    op.create_index(op.f('ix_player_stats_id'), 'player_stats', ['id'], unique=False)
    
    # Recreate stats_features with correct column order
    op.create_table(
        'stats_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(), nullable=False),
        sa.Column('player_position', sa.String(), nullable=True),
        sa.Column('season', sa.Integer(), server_default='2025', nullable=False),
        sa.Column('games_played', sa.Integer(), server_default='0', nullable=True),
        
        # Offensive Averages
        sa.Column('avg_passing_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_passing_tds', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_interceptions', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_sacks_taken', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_rushing_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_rushing_tds', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_receiving_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_receiving_tds', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_receptions', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_targets', sa.Float(), server_default='0', nullable=True),
        
        # Totals
        sa.Column('total_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('total_tds', sa.Float(), server_default='0', nullable=True),
        sa.Column('total_interceptions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_sacks_taken', sa.Float(), server_default='0', nullable=True),
        
        # Recent Form
        sa.Column('last_3_avg_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('last_3_avg_tds', sa.Float(), server_default='0', nullable=True),
        
        # Consistency
        sa.Column('consistency_score', sa.Float(), server_default='0', nullable=True),
        
        # Home/Away
        sa.Column('home_avg_yards', sa.Float(), server_default='0', nullable=True),
        sa.Column('away_avg_yards', sa.Float(), server_default='0', nullable=True),
        
        # Usage
        sa.Column('avg_target_share', sa.Float(), server_default='0', nullable=True),
        
        # Defensive Stats
        sa.Column('avg_tackles', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_sacks_def', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_interceptions_def', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_pass_deflections', sa.Float(), server_default='0', nullable=True),
        sa.Column('avg_tackles_for_loss', sa.Float(), server_default='0', nullable=True),
        sa.Column('total_tackles', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_sacks_def', sa.Float(), server_default='0', nullable=True),
        sa.Column('total_interceptions_def', sa.Integer(), server_default='0', nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.UniqueConstraint('player_id')
    )
    op.create_index(op.f('ix_stats_features_id'), 'stats_features', ['id'], unique=False)


def downgrade() -> None:
    # Can't easily downgrade this - would need full backfill
    pass
