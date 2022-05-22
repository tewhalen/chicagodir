"""empty message

Revision ID: 4ae2f5a7cfc1
Revises: 85ff8aa6633e
Create Date: 2022-05-18 14:43:51.747328

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision = "4ae2f5a7cfc1"
down_revision = "85ff8aa6633e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "stored_map",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                srid=3435, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_stored_map_year"), "stored_map", ["year"], unique=False)

    op.add_column(
        "streets",
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                srid=3435, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_column("streets", "geom")

    op.drop_index(op.f("ix_stored_map_year"), table_name="stored_map")

    op.drop_table("stored_map")
    # ### end Alembic commands ###
