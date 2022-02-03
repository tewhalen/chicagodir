"""empty message

Revision ID: 63c099968697
Revises: d658858966d7
Create Date: 2022-01-29 16:43:23.878082

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63c099968697'
down_revision = 'd658858966d7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('street_lists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_street_lists_date'), 'street_lists', ['date'], unique=False)
    op.create_table('street_list_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('list_id', sa.Integer(), nullable=False),
    sa.Column('street_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['list_id'], ['street_lists.id'], ),
    sa.ForeignKeyConstraint(['street_id'], ['streets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('streets', sa.Column('vacated', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('streets', 'vacated')
    op.drop_table('street_list_entries')
    op.drop_index(op.f('ix_street_lists_date'), table_name='street_lists')
    op.drop_table('street_lists')
    # ### end Alembic commands ###
