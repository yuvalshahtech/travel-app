"""add engagement tracking columns to user_activity

Revision ID: 0002_engagement
Revises: de80a0d590de
Create Date: 2026-02-28

Adds session_id, page, hotel_id, event_type, duration_seconds, metadata
columns to the user_activity table. Does NOT delete any existing records.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '0002_engagement'
down_revision: Union[str, None] = 'de80a0d590de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns — all nullable so existing rows are preserved
    op.add_column('user_activity', sa.Column('session_id', sa.String(36), nullable=True))
    op.add_column('user_activity', sa.Column('page', sa.String(100), nullable=True))
    op.add_column('user_activity', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.add_column('user_activity', sa.Column('event_type', sa.String(50), nullable=True))
    op.add_column('user_activity', sa.Column('duration_seconds', sa.Integer(), nullable=True))
    op.add_column('user_activity', sa.Column('event_metadata', JSONB(), nullable=True))

    # Indexes for the new columns
    op.create_index('idx_user_activity_session_id', 'user_activity', ['session_id'])
    op.create_index('idx_user_activity_event_type', 'user_activity', ['event_type'])
    op.create_index('idx_user_activity_session_event', 'user_activity', ['session_id', 'event_type'])
    op.create_index('idx_user_activity_hotel_id', 'user_activity', ['hotel_id'])


def downgrade() -> None:
    op.drop_index('idx_user_activity_hotel_id', table_name='user_activity')
    op.drop_index('idx_user_activity_session_event', table_name='user_activity')
    op.drop_index('idx_user_activity_event_type', table_name='user_activity')
    op.drop_index('idx_user_activity_session_id', table_name='user_activity')

    op.drop_column('user_activity', 'event_metadata')
    op.drop_column('user_activity', 'duration_seconds')
    op.drop_column('user_activity', 'event_type')
    op.drop_column('user_activity', 'hotel_id')
    op.drop_column('user_activity', 'page')
    op.drop_column('user_activity', 'session_id')
