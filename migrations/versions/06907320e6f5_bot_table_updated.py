# """Bot table updated

# Revision ID: 06907320e6f5
# Revises: 0a6fddd12d0b
# Create Date: 2024-09-10 10:49:53.264661

# """
# from alembic import op
# import sqlalchemy as sa
# from sqlalchemy.dialects import postgresql

# # revision identifiers, used by Alembic.
# revision = '06907320e6f5'
# down_revision = '0a6fddd12d0b'
# branch_labels = None
# depends_on = None


# def upgrade():
#     # ### commands auto generated by Alembic - please adjust! ###
#     with op.batch_alter_table('bot', schema=None) as batch_op:
#         batch_op.add_column(sa.Column('alias', sa.String(), nullable=True))
#         batch_op.add_column(sa.Column('icon', sa.String(), nullable=True))
#         batch_op.add_column(sa.Column('background_color', sa.String(), nullable=True))
#         batch_op.alter_column('name',
#                existing_type=sa.VARCHAR(),
#                nullable=True)
#         batch_op.alter_column('dalle_prompt',
#                existing_type=sa.VARCHAR(),
#                nullable=True)
#         batch_op.alter_column('run_frequency',
#                existing_type=sa.INTEGER(),
#                type_=sa.String(),
#                nullable=True)
#         batch_op.alter_column('category_id',
#                existing_type=sa.INTEGER(),
#                nullable=True)
#         batch_op.drop_column('last_run')
#         batch_op.drop_column('url')

#     with op.batch_alter_table('category', schema=None) as batch_op:
#         batch_op.alter_column('name',
#                existing_type=sa.VARCHAR(),
#                nullable=False)
#         batch_op.alter_column('alias',
#                existing_type=sa.VARCHAR(),
#                nullable=False)
#         batch_op.alter_column('updated_at',
#                existing_type=postgresql.TIMESTAMP(),
#                nullable=False)

#     with op.batch_alter_table('used_keywords', schema=None) as batch_op:
#         batch_op.drop_column('updated_at')

#     # ### end Alembic commands ###


# def downgrade():
#     # ### commands auto generated by Alembic - please adjust! ###
#     with op.batch_alter_table('used_keywords', schema=None) as batch_op:
#         batch_op.add_column(sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))

#     with op.batch_alter_table('category', schema=None) as batch_op:
#         batch_op.alter_column('updated_at',
#                existing_type=postgresql.TIMESTAMP(),
#                nullable=True)
#         batch_op.alter_column('alias',
#                existing_type=sa.VARCHAR(),
#                nullable=True)
#         batch_op.alter_column('name',
#                existing_type=sa.VARCHAR(),
#                nullable=True)

#     with op.batch_alter_table('bot', schema=None) as batch_op:
#         batch_op.add_column(sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=False))
#         batch_op.add_column(sa.Column('last_run', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
#         batch_op.alter_column('category_id',
#                existing_type=sa.INTEGER(),
#                nullable=False)
#         batch_op.alter_column('run_frequency',
#                existing_type=sa.String(),
#                type_=sa.INTEGER(),
#                nullable=False)
#         batch_op.alter_column('dalle_prompt',
#                existing_type=sa.VARCHAR(),
#                nullable=False)
#         batch_op.alter_column('name',
#                existing_type=sa.VARCHAR(),
#                nullable=False)
#         batch_op.drop_column('background_color')
#         batch_op.drop_column('icon')
#         batch_op.drop_column('alias')

#     # ### end Alembic commands ###

"""Bot table updated

Revision ID: 06907320e6f5
Revises: 0a6fddd12d0b
Create Date: 2024-09-10 10:49:53.264661

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '06907320e6f5'
down_revision = '0a6fddd12d0b'
branch_labels = None
depends_on = None

def column_exists(table, column):
    conn = op.get_bind()
    result = conn.execute(sa.text(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table}' AND column_name = '{column}'"
    )).fetchone()
    return result is not None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('bot', schema=None) as batch_op:
        if not column_exists('bot', 'alias'):
            batch_op.add_column(sa.Column('alias', sa.String(), nullable=True))
        if not column_exists('bot', 'icon'):
            batch_op.add_column(sa.Column('icon', sa.String(), nullable=True))
        if not column_exists('bot', 'background_color'):
            batch_op.add_column(sa.Column('background_color', sa.String(), nullable=True))
        
        if column_exists('bot', 'name'):
            batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=True)
        if column_exists('bot', 'dalle_prompt'):
            batch_op.alter_column('dalle_prompt', existing_type=sa.VARCHAR(), nullable=True)
        if column_exists('bot', 'run_frequency'):
            batch_op.alter_column('run_frequency', existing_type=sa.INTEGER(), type_=sa.String(), nullable=True)
        if column_exists('bot', 'category_id'):
            batch_op.alter_column('category_id', existing_type=sa.INTEGER(), nullable=True)
        
        if column_exists('bot', 'last_run'):
            batch_op.drop_column('last_run')
        if column_exists('bot', 'url'):
            batch_op.drop_column('url')

    with op.batch_alter_table('category', schema=None) as batch_op:
        if column_exists('category', 'name'):
            batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=False)
        if column_exists('category', 'alias'):
            batch_op.alter_column('alias', existing_type=sa.VARCHAR(), nullable=False)
        if column_exists('category', 'updated_at'):
            batch_op.alter_column('updated_at', existing_type=postgresql.TIMESTAMP(), nullable=False)

    with op.batch_alter_table('used_keywords', schema=None) as batch_op:
        if column_exists('used_keywords', 'updated_at'):
            batch_op.drop_column('updated_at')
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('used_keywords', schema=None) as batch_op:
        if not column_exists('used_keywords', 'updated_at'):
            batch_op.add_column(sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))

    with op.batch_alter_table('category', schema=None) as batch_op:
        if column_exists('category', 'updated_at'):
            batch_op.alter_column('updated_at', existing_type=postgresql.TIMESTAMP(), nullable=True)
        if column_exists('category', 'alias'):
            batch_op.alter_column('alias', existing_type=sa.VARCHAR(), nullable=True)
        if column_exists('category', 'name'):
            batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=True)

    with op.batch_alter_table('bot', schema=None) as batch_op:
        if not column_exists('bot', 'url'):
            batch_op.add_column(sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=False))
        if not column_exists('bot', 'last_run'):
            batch_op.add_column(sa.Column('last_run', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
        
        if column_exists('bot', 'category_id'):
            batch_op.alter_column('category_id', existing_type=sa.INTEGER(), nullable=False)
        if column_exists('bot', 'run_frequency'):
            batch_op.alter_column('run_frequency', existing_type=sa.String(), type_=sa.INTEGER(), nullable=False)
        if column_exists('bot', 'dalle_prompt'):
            batch_op.alter_column('dalle_prompt', existing_type=sa.VARCHAR(), nullable=False)
        if column_exists('bot', 'name'):
            batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=False)
        
        if column_exists('bot', 'background_color'):
            batch_op.drop_column('background_color')
        if column_exists('bot', 'icon'):
            batch_op.drop_column('icon')
        if column_exists('bot', 'alias'):
            batch_op.drop_column('alias')
    # ### end Alembic commands ###