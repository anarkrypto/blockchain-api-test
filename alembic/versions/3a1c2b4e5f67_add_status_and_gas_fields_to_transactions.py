"""
add status and gas fields to transactions
"""
import sqlalchemy as sa

from alembic import op

# Revisão Alembic
revision = '3a1c2b4e5f67'
down_revision = '2d1dd9b77b17'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('transactions', sa.Column('status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('transactions', sa.Column('gas_used', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('gas_price', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('fee', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('transactions', 'fee')
    op.drop_column('transactions', 'gas_price')
    op.drop_column('transactions', 'gas_used')
    op.drop_column('transactions', 'status') 