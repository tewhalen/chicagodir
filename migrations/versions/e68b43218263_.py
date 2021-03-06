"""empty message

Revision ID: e68b43218263
Revises: 63c099968697
Create Date: 2022-01-30 20:49:38.481285

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e68b43218263'
down_revision = '63c099968697'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('streets', sa.Column('start_data_circa', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('streets', sa.Column('end_date_circa', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('streets', 'end_date_circa')
    op.drop_column('streets', 'start_data_circa')
    # ### end Alembic commands ###
