"""Add AI learning tables

Revision ID: add_learning_tables
Revises: 6e3e30004520
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_learning_tables'
down_revision = '6e3e30004520'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to predictions table
    op.add_column('predictions', sa.Column('prop_type', sa.String(), nullable=True))
    op.add_column('predictions', sa.Column('bet_category', sa.String(), nullable=True))
    op.add_column('predictions', sa.Column('line_used', sa.Float(), nullable=True))
    op.add_column('predictions', sa.Column('was_accurate', sa.Boolean(), nullable=True))
    op.add_column('predictions', sa.Column('hit_over', sa.Boolean(), nullable=True))
    op.add_column('predictions', sa.Column('season', sa.Integer(), nullable=True, default=2025))
    op.add_column('predictions', sa.Column('week', sa.Integer(), nullable=True))
    
    # Create bet_type_accuracy table
    op.create_table(
        'bet_type_accuracy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bet_category', sa.String(), nullable=False),
        sa.Column('prop_type', sa.String(), nullable=True),
        sa.Column('position', sa.String(), nullable=True),
        sa.Column('total_predictions', sa.Integer(), default=0),
        sa.Column('accurate_predictions', sa.Integer(), default=0),
        sa.Column('total_hit_over', sa.Integer(), default=0),
        sa.Column('accuracy_pct', sa.Float(), default=50.0),
        sa.Column('hit_rate', sa.Float(), default=50.0),
        sa.Column('avg_error', sa.Float(), default=0.0),
        sa.Column('confidence_adjustment', sa.Float(), default=0.0),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('season', sa.Integer(), default=2025),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create player_hit_rates table
    op.create_table(
        'player_hit_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('prop_type', sa.String(), nullable=False),
        sa.Column('total_games', sa.Integer(), default=0),
        sa.Column('times_hit_over', sa.Integer(), default=0),
        sa.Column('hit_rate', sa.Float(), default=50.0),
        sa.Column('avg_variance', sa.Float(), default=0.0),
        sa.Column('confidence_adjustment', sa.Float(), default=0.0),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('season', sa.Integer(), default=2025),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('player_hit_rates')
    op.drop_table('bet_type_accuracy')
    op.drop_column('predictions', 'week')
    op.drop_column('predictions', 'season')
    op.drop_column('predictions', 'hit_over')
    op.drop_column('predictions', 'was_accurate')
    op.drop_column('predictions', 'line_used')
    op.drop_column('predictions', 'bet_category')
    op.drop_column('predictions', 'prop_type')

