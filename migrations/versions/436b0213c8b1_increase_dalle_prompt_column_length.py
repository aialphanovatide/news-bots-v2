"""Increase dalle_prompt column length and remove time_interval from category

Revision ID: 436b0213c8b1
Revises: ac9ea16e4a5e
Create Date: 2024-10-10 21:15:50.600913

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '436b0213c8b1'
down_revision = 'ac9ea16e4a5e'
branch_labels = None
depends_on = None

def column_exists(table, column):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)

def get_column_type(table, column):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = inspector.get_columns(table)
    for c in columns:
        if c["name"] == column:
            return c["type"]
    return None

def upgrade():
    # Remove time_interval from category table if it exists
    with op.batch_alter_table('category', schema=None) as batch_op:
        if column_exists('category', 'time_interval'):
            batch_op.drop_column('time_interval')

    # Increase dalle_prompt column length in bot table if necessary
    with op.batch_alter_table('bot', schema=None) as batch_op:
        if column_exists('bot', 'dalle_prompt'):
            current_type = get_column_type('bot', 'dalle_prompt')
            if isinstance(current_type, sa.VARCHAR) and current_type.length < 1024:
                batch_op.alter_column('dalle_prompt',
                    existing_type=current_type,
                    type_=sa.String(length=1024),
                    existing_nullable=True)

def downgrade():
    # Revert dalle_prompt column length in bot table
    with op.batch_alter_table('bot', schema=None) as batch_op:
        if column_exists('bot', 'dalle_prompt'):
            current_type = get_column_type('bot', 'dalle_prompt')
            if isinstance(current_type, sa.String) and current_type.length == 1024:
                batch_op.alter_column('dalle_prompt',
                    existing_type=current_type,
                    type_=sa.VARCHAR(length=256),
                    existing_nullable=True)

    # Add time_interval back to category table
    with op.batch_alter_table('category', schema=None) as batch_op:
        if not column_exists('category', 'time_interval'):
            batch_op.add_column(sa.Column('time_interval', sa.INTEGER(), autoincrement=False, nullable=True))