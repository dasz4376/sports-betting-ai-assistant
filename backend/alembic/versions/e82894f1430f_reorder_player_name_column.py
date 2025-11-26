"""reorder player_name column

Revision ID: e82894f1430f
Revises: d8f0253c7110
Create Date: 2025-11-25 05:35:49.788651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e82894f1430f'
down_revision: Union[str, None] = 'd8f0253c7110'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate table with player_name as second column (after player_id)
    op.execute("""
        CREATE TABLE player_stats_new (
            id SERIAL PRIMARY KEY,
            player_id INTEGER NOT NULL REFERENCES players(id),
            player_name VARCHAR,
            game_id INTEGER NOT NULL REFERENCES games(id),
            passing_yards FLOAT DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            passing_touchdowns INTEGER DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            rushing_yards FLOAT DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            rushing_touchdowns INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            receiving_yards FLOAT DEFAULT 0,
            receiving_targets INTEGER DEFAULT 0,
            receiving_touchdowns INTEGER DEFAULT 0,
            fumbles INTEGER DEFAULT 0,
            fumbles_lost INTEGER DEFAULT 0,
            snaps INTEGER,
            routes_run INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Copy all data from old table
    op.execute("""
        INSERT INTO player_stats_new (
            id, player_id, player_name, game_id,
            passing_yards, passing_completions, passing_attempts, passing_touchdowns, interceptions,
            rushing_yards, rushing_attempts, rushing_touchdowns,
            receptions, receiving_yards, receiving_targets, receiving_touchdowns,
            fumbles, fumbles_lost, snaps, routes_run, created_at
        )
        SELECT 
            id, player_id, player_name, game_id,
            passing_yards, passing_completions, passing_attempts, passing_touchdowns, interceptions,
            rushing_yards, rushing_attempts, rushing_touchdowns,
            receptions, receiving_yards, receiving_targets, receiving_touchdowns,
            fumbles, fumbles_lost, snaps, routes_run, created_at
        FROM player_stats
    """)
    
    # Update sequence to continue from current max
    op.execute("""
        SELECT setval('player_stats_new_id_seq', (SELECT MAX(id) FROM player_stats_new))
    """)
    
    # Drop old table
    op.execute("DROP TABLE player_stats")
    
    # Rename new table
    op.execute("ALTER TABLE player_stats_new RENAME TO player_stats")
    
    # Rename sequence
    op.execute("ALTER SEQUENCE player_stats_new_id_seq RENAME TO player_stats_id_seq")


def downgrade() -> None:
    # Recreate table with player_name at the end (original order)
    op.execute("""
        CREATE TABLE player_stats_old (
            id SERIAL PRIMARY KEY,
            player_id INTEGER NOT NULL REFERENCES players(id),
            game_id INTEGER NOT NULL REFERENCES games(id),
            passing_yards FLOAT DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            passing_touchdowns INTEGER DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            rushing_yards FLOAT DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            rushing_touchdowns INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            receiving_yards FLOAT DEFAULT 0,
            receiving_targets INTEGER DEFAULT 0,
            receiving_touchdowns INTEGER DEFAULT 0,
            fumbles INTEGER DEFAULT 0,
            fumbles_lost INTEGER DEFAULT 0,
            snaps INTEGER,
            routes_run INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            player_name VARCHAR
        )
    """)
    
    # Copy data back
    op.execute("""
        INSERT INTO player_stats_old (
            id, player_id, game_id,
            passing_yards, passing_completions, passing_attempts, passing_touchdowns, interceptions,
            rushing_yards, rushing_attempts, rushing_touchdowns,
            receptions, receiving_yards, receiving_targets, receiving_touchdowns,
            fumbles, fumbles_lost, snaps, routes_run, created_at, player_name
        )
        SELECT 
            id, player_id, game_id,
            passing_yards, passing_completions, passing_attempts, passing_touchdowns, interceptions,
            rushing_yards, rushing_attempts, rushing_touchdowns,
            receptions, receiving_yards, receiving_targets, receiving_touchdowns,
            fumbles, fumbles_lost, snaps, routes_run, created_at, player_name
        FROM player_stats
    """)
    
    op.execute("SELECT setval('player_stats_old_id_seq', (SELECT MAX(id) FROM player_stats_old))")
    op.execute("DROP TABLE player_stats")
    op.execute("ALTER TABLE player_stats_old RENAME TO player_stats")
    op.execute("ALTER SEQUENCE player_stats_old_id_seq RENAME TO player_stats_id_seq")
