"""add event embeddings table

Revision ID: 0145fa643035
Revises: 14bd040e8105
Create Date: 2026-03-25 17:01:14.780351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0145fa643035'
down_revision: Union[str, Sequence[str], None] = '14bd040e8105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'event_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('faiss_index', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for better performance
    op.create_index(
        'ix_event_embeddings_event_id',
        'event_embeddings',
        ['event_id'],
        unique=False
    )

    op.create_index(
        'ix_event_embeddings_faiss_index',
        'event_embeddings',
        ['faiss_index'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_event_embeddings_faiss_index', table_name='event_embeddings')
    op.drop_index('ix_event_embeddings_event_id', table_name='event_embeddings')
    op.drop_table('event_embeddings')