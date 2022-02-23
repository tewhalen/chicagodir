"""empty message

Revision ID: 3df429698f31
Revises: 884fbf8b24ed
Create Date: 2022-02-13 19:02:31.782705

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3df429698f31'
down_revision = '884fbf8b24ed'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('directories', 'streetlist_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('directories', 'streetlist_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
