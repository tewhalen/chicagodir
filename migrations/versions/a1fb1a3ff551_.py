"""empty message

Revision ID: a1fb1a3ff551
Revises: 054be0852f9f
Create Date: 2022-03-09 23:57:04.469263

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1fb1a3ff551'
down_revision = '054be0852f9f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_streetchange_from_id'), 'streetchange', ['from_id'], unique=False)
    op.create_index(op.f('ix_streetchange_to_id'), 'streetchange', ['to_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_streetchange_to_id'), table_name='streetchange')
    op.drop_index(op.f('ix_streetchange_from_id'), table_name='streetchange')
    # ### end Alembic commands ###