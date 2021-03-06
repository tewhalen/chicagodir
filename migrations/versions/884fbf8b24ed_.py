"""empty message

Revision ID: 884fbf8b24ed
Revises: 84b5ddd15854
Create Date: 2022-02-13 16:31:44.422780

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '884fbf8b24ed'
down_revision = '84b5ddd15854'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('directories', sa.Column('streetlist_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'directories', 'street_lists', ['streetlist_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'directories', type_='foreignkey')
    op.drop_column('directories', 'streetlist_id')
    # ### end Alembic commands ###
