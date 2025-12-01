"""Initial tables for convertible bond selector.

Revision ID: 001
Revises: 
Create Date: 2024-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create formulas table
    op.create_table(
        'formulas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_formulas_name', 'formulas', ['name'])
    op.create_index('ix_formulas_created_at', 'formulas', ['created_at'])

    # Create screening_results table
    op.create_table(
        'screening_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('formula_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False, default=0),
        sa.Column('result_data', postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ['formula_id'], ['formulas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screening_results_formula_id',
                    'screening_results', ['formula_id'])
    op.create_index('ix_screening_results_executed_at',
                    'screening_results', ['executed_at'])

    # Create bond_cache table
    op.create_table(
        'bond_cache',
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('code')
    )
    op.create_index('ix_bond_cache_updated_at', 'bond_cache', ['updated_at'])


def downgrade() -> None:
    op.drop_table('bond_cache')
    op.drop_table('screening_results')
    op.drop_table('formulas')
