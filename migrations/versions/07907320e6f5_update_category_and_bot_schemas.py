"""Update Category and Bot schemas

Revision ID: 07907320e6f5
Revises: 06907320e6f5
Create Date: 2024-09-24 02:52:53.264661

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '07907320e6f5'
down_revision = '06907320e6f5'
branch_labels = None
depends_on = None

def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns(table)]
    return column in columns

def upgrade():
    # Update Category table
    with op.batch_alter_table('category', schema=None) as batch_op:
        if not column_exists('category', 'is_active'):
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=True))
        else:
            batch_op.alter_column('is_active',
                                  existing_type=sa.Boolean(),
                                  server_default=sa.text('false'),
                                  existing_nullable=True)

    # Update Bot table
    with op.batch_alter_table('bot', schema=None) as batch_op:
        if not column_exists('bot', 'alias'):
            batch_op.add_column(sa.Column('alias', sa.String(), nullable=True))
        if not column_exists('bot', 'icon'):
            batch_op.add_column(sa.Column('icon', sa.String(), nullable=True))
        if not column_exists('bot', 'background_color'):
            batch_op.add_column(sa.Column('background_color', sa.String(), nullable=True))
        if not column_exists('bot', 'run_frequency'):
            batch_op.add_column(sa.Column('run_frequency', sa.String(), server_default='20', nullable=True))
        if not column_exists('bot', 'is_active'):
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=True))

def downgrade():
    # Revert changes to Bot table
    with op.batch_alter_table('bot', schema=None) as batch_op:
        if column_exists('bot', 'is_active'):
            batch_op.drop_column('is_active')
        if column_exists('bot', 'run_frequency'):
            batch_op.drop_column('run_frequency')
        if column_exists('bot', 'background_color'):
            batch_op.drop_column('background_color')
        if column_exists('bot', 'icon'):
            batch_op.drop_column('icon')
        if column_exists('bot', 'alias'):
            batch_op.drop_column('alias')

    # Revert changes to Category table
    with op.batch_alter_table('category', schema=None) as batch_op:
        if column_exists('category', 'is_active'):
            batch_op.alter_column('is_active',
                                  existing_type=sa.Boolean(),
                                  server_default=sa.text('true'),
                                  existing_nullable=True)