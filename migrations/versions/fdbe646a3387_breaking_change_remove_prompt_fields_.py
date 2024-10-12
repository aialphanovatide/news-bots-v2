"""BREAKING CHANGE: remove prompt fields from category schema and added to Bot schema

Revision ID: fdbe646a3387
Revises: 436b0213c8b1
Create Date: 2024-10-11 21:23:42.109747

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fdbe646a3387'
down_revision = '436b0213c8b1'
branch_labels = None
depends_on = None


def upgrade():
    # Remove 'prompt' column from 'category' table
    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.drop_column('prompt')

    # Add 'prompt' column to 'bot' table
    with op.batch_alter_table('bot', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prompt', sa.Text(), nullable=True))


def downgrade():
    # Remove 'prompt' column from 'bot' table
    with op.batch_alter_table('bot', schema=None) as batch_op:
        batch_op.drop_column('prompt')

    # Add 'prompt' column back to 'category' table
    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prompt', sa.String(), nullable=True))