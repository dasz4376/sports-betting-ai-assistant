"""reorder_injury_player_name

Revision ID: 2821b8d805ba
Revises: 2a51173fa744
Create Date: 2025-11-25 05:50:52.142136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2821b8d805ba'
down_revision: Union[str, None] = '2a51173fa744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL doesn't support column reordering directly
    # We need to recreate the table with the correct column order
    
    # Create new table with correct column order
    op.execute("""
        CREATE TABLE injuries_new (
            id SERIAL PRIMARY KEY,
            player_id INTEGER NOT NULL REFERENCES players(id),
            player_name VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            injury_type VARCHAR,
            description TEXT,
            date_reported TIMESTAMP WITH TIME ZONE,
            date_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO injuries_new (
            id, player_id, player_name, status, injury_type, 
            description, date_reported, date_updated, is_active
        )
        SELECT 
            id, player_id, player_name, status, injury_type,
            description, date_reported, date_updated, is_active
        FROM injuries
    """)
    
    # Update the sequence to continue from the max id
    op.execute("""
        SELECT setval('injuries_new_id_seq', (SELECT MAX(id) FROM injuries_new))
    """)
    
    # Drop old table and rename new one
    op.drop_table('injuries')
    op.rename_table('injuries_new', 'injuries')
    
    # Rename the sequence
    op.execute("ALTER SEQUENCE injuries_new_id_seq RENAME TO injuries_id_seq")


def downgrade() -> None:
    # Reverse operation: recreate with original column order
    op.execute("""
        CREATE TABLE injuries_old (
            id SERIAL PRIMARY KEY,
            player_id INTEGER NOT NULL REFERENCES players(id),
            status VARCHAR NOT NULL,
            injury_type VARCHAR,
            description TEXT,
            date_reported TIMESTAMP WITH TIME ZONE,
            date_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            player_name VARCHAR NOT NULL
        )
    """)
    
    op.execute("""
        INSERT INTO injuries_old (
            id, player_id, status, injury_type, description,
            date_reported, date_updated, is_active, player_name
        )
        SELECT 
            id, player_id, status, injury_type, description,
            date_reported, date_updated, is_active, player_name
        FROM injuries
    """)
    
    op.execute("""
        SELECT setval('injuries_old_id_seq', (SELECT MAX(id) FROM injuries_old))
    """)
    
    op.drop_table('injuries')
    op.rename_table('injuries_old', 'injuries')
    op.execute("ALTER SEQUENCE injuries_old_id_seq RENAME TO injuries_id_seq")
