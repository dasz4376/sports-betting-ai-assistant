"""reorder_games_columns

Revision ID: a1aedd3558f3
Revises: 0d7fa65faeff
Create Date: 2025-11-25 06:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1aedd3558f3'
down_revision: Union[str, None] = '0d7fa65faeff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraints from dependent tables
    op.drop_constraint('player_stats_new_game_id_fkey', 'player_stats', type_='foreignkey')
    op.drop_constraint('matchups_game_id_fkey', 'matchups', type_='foreignkey')
    op.drop_constraint('odds_game_id_fkey', 'odds', type_='foreignkey')
    op.drop_constraint('predictions_game_id_fkey', 'predictions', type_='foreignkey')
    
    # Recreate games table with columns in desired order
    op.execute("""
        CREATE TABLE games_new (
            id SERIAL PRIMARY KEY,
            espn_game_id VARCHAR UNIQUE NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            game_date TIMESTAMP WITH TIME ZONE NOT NULL,
            
            -- Team Information (moved up)
            home_team_id INTEGER REFERENCES teams(id),
            home_team_name VARCHAR,
            away_team_id INTEGER REFERENCES teams(id),
            away_team_name VARCHAR,
            
            -- Game Results
            home_score INTEGER,
            away_score INTEGER,
            winner_team_id INTEGER REFERENCES teams(id),
            winner_team_name VARCHAR,
            
            status VARCHAR,
            venue VARCHAR,
            weather JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO games_new (
            id, espn_game_id, season, week, game_date,
            home_team_id, home_team_name, away_team_id, away_team_name,
            home_score, away_score, winner_team_id, winner_team_name,
            status, venue, weather, created_at, updated_at
        )
        SELECT 
            id, espn_game_id, season, week, game_date,
            home_team_id, home_team_name, away_team_id, away_team_name,
            home_score, away_score, winner_team_id, winner_team_name,
            status, venue, weather, created_at, updated_at
        FROM games
    """)
    
    # Update sequence
    op.execute("""
        SELECT setval('games_new_id_seq', (SELECT MAX(id) FROM games_new))
    """)
    
    # Drop old table
    op.drop_table('games')
    
    # Rename new table
    op.rename_table('games_new', 'games')
    
    # Rename sequence
    op.execute("ALTER SEQUENCE games_new_id_seq RENAME TO games_id_seq")
    
    # Recreate indexes
    op.create_index('ix_games_espn_game_id', 'games', ['espn_game_id'], unique=True)
    
    # Recreate foreign key constraints
    op.create_foreign_key('player_stats_game_id_fkey', 'player_stats', 'games', ['game_id'], ['id'])
    op.create_foreign_key('matchups_game_id_fkey', 'matchups', 'games', ['game_id'], ['id'])
    op.create_foreign_key('odds_game_id_fkey', 'odds', 'games', ['game_id'], ['id'])
    op.create_foreign_key('predictions_game_id_fkey', 'predictions', 'games', ['game_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key constraints from dependent tables
    op.drop_constraint('player_stats_game_id_fkey', 'player_stats', type_='foreignkey')
    op.drop_constraint('matchups_game_id_fkey', 'matchups', type_='foreignkey')
    op.drop_constraint('odds_game_id_fkey', 'odds', type_='foreignkey')
    op.drop_constraint('predictions_game_id_fkey', 'predictions', type_='foreignkey')
    
    # Recreate original table structure
    op.execute("""
        CREATE TABLE games_new (
            id SERIAL PRIMARY KEY,
            espn_game_id VARCHAR UNIQUE NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            game_date TIMESTAMP WITH TIME ZONE NOT NULL,
            home_team_id INTEGER REFERENCES teams(id),
            away_team_id INTEGER REFERENCES teams(id),
            home_score INTEGER,
            away_score INTEGER,
            status VARCHAR,
            venue VARCHAR,
            weather JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE,
            home_team_name VARCHAR,
            away_team_name VARCHAR,
            winner_team_id INTEGER REFERENCES teams(id),
            winner_team_name VARCHAR
        )
    """)
    
    op.execute("""
        INSERT INTO games_new (
            id, espn_game_id, season, week, game_date,
            home_team_id, away_team_id,
            home_score, away_score,
            status, venue, weather, created_at, updated_at,
            home_team_name, away_team_name, winner_team_id, winner_team_name
        )
        SELECT 
            id, espn_game_id, season, week, game_date,
            home_team_id, away_team_id,
            home_score, away_score,
            status, venue, weather, created_at, updated_at,
            home_team_name, away_team_name, winner_team_id, winner_team_name
        FROM games
    """)
    
    op.execute("""
        SELECT setval('games_new_id_seq', (SELECT MAX(id) FROM games_new))
    """)
    
    op.drop_table('games')
    op.rename_table('games_new', 'games')
    op.execute("ALTER SEQUENCE games_new_id_seq RENAME TO games_id_seq")
    op.create_index('ix_games_espn_game_id', 'games', ['espn_game_id'], unique=True)
    
    # Recreate foreign key constraints with original names
    op.create_foreign_key('player_stats_new_game_id_fkey', 'player_stats', 'games', ['game_id'], ['id'])
    op.create_foreign_key('matchups_game_id_fkey', 'matchups', 'games', ['game_id'], ['id'])
    op.create_foreign_key('odds_game_id_fkey', 'odds', 'games', ['game_id'], ['id'])
    op.create_foreign_key('predictions_game_id_fkey', 'predictions', 'games', ['game_id'], ['id'])
