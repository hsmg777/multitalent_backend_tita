"""merge heads before skills

Revision ID: 3d888c5f713f
Revises: 2c1d64c8fb61, b8a9c5c8cabd
Create Date: 2025-09-15 00:07:14.400910

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d888c5f713f'
down_revision = ('2c1d64c8fb61', 'b8a9c5c8cabd')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
