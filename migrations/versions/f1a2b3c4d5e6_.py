"""add notes to orders and order_status_history table

Revision ID: f1a2b3c4d5e6
Revises: e8f9a1b2c3d4
Create Date: 2026-03-13 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'e8f9a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))

    statusenum = sa.Enum(
        'PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED',
        name='statusenum',
        create_type=False,
    )
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('from_status', statusenum, nullable=True),
        sa.Column('to_status', statusenum, nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('order_status_history')
    op.drop_column('orders', 'notes')
