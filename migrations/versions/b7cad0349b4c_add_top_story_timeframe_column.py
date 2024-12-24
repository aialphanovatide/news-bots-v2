"""Add top story timeframe column

Revision ID: b7cad0349b4c
Revises: fdbe646a3387
Create Date: 2024-12-19 17:39:02.708255

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7cad0349b4c'
down_revision = 'fdbe646a3387'
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type if it doesn't exist
    top_story_timeframe_enum = sa.Enum('1D', '1W', '1M', name='top_story_timeframe')
    
    # Create enum type if it doesn't exist
    top_story_timeframe_enum.create(op.get_bind(), checkfirst=True)
    
    # Check if column exists before adding it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('article')]
    
    if 'top_story_timeframe' not in columns:
        with op.batch_alter_table('article', schema=None) as batch_op:
            batch_op.add_column(sa.Column('top_story_timeframe', 
                                        top_story_timeframe_enum,
                                        nullable=True))


def downgrade():
    # Drop the column
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.drop_column('top_story_timeframe')
    
    # Drop the enum type
    top_story_timeframe_enum = sa.Enum(name='top_story_timeframe')
    top_story_timeframe_enum.drop(op.get_bind(), checkfirst=True)