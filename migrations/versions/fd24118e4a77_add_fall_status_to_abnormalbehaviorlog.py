"""Add fall_status to AbnormalBehaviorLog

Revision ID: fd24118e4a77
Revises: 14dfb040f92f
Create Date: 2025-01-02 15:11:05.040651

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd24118e4a77'
down_revision = '14dfb040f92f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('abnormal_behavior_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fall_status', sa.String(length=50), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('abnormal_behavior_logs', schema=None) as batch_op:
        batch_op.drop_column('fall_status')

    # ### end Alembic commands ###
