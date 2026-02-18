"""add DELIVERED and CANCELLED to statusenum

Revision ID: e8f9a1b2c3d4
Revises: 7fd028bd60c4
Create Date: 2026-05-24 09:10:14.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e8f9a1b2c3d4'
down_revision = '7fd028bd60c4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE statusenum ADD VALUE IF NOT EXISTS 'DELIVERED'")
            op.execute("ALTER TYPE statusenum ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade():
    pass
