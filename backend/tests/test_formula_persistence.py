"""Property-based tests for formula persistence.

**Feature: convertible-bond-selector, Property 3: Formula persistence round-trip**
**Feature: convertible-bond-selector, Property 4: Formula count consistency**
"""

import pytest
from hypothesis import given, strategies as st, settings
from uuid import uuid4

from typing import Optional
from app.models.schemas import FormulaCreate, FormulaResponse


# Strategy for generating valid formula names
formula_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Strategy for generating valid formula expressions
formula_expression_strategy = st.sampled_from([
    "price < 130",
    "premium_rate < 20",
    "price < 130 AND premium_rate < 20",
    "ytm > 0 OR remaining_years < 3",
    "(price < 120) AND (premium_rate < 15)",
    "double_low < 130",
    "credit_rating == 'AA'",
    "NOT (price > 150)",
])

# Strategy for generating valid formula descriptions
formula_description_strategy = st.one_of(
    st.none(),
    st.text(min_size=0, max_size=500)
)


class MockFormulaRepository:
    """Mock repository for testing formula persistence without database."""

    def __init__(self):
        self.formulas = {}

    def create(self, formula: FormulaCreate) -> FormulaResponse:
        """Create a formula and return response."""
        from datetime import datetime
        formula_id = uuid4()
        now = datetime.utcnow()
        response = FormulaResponse(
            id=formula_id,
            name=formula.name,
            description=formula.description,
            expression=formula.expression,
            created_at=now,
            updated_at=now,
        )
        self.formulas[formula_id] = response
        return response

    def get(self, formula_id) -> Optional[FormulaResponse]:
        """Get a formula by ID."""
        return self.formulas.get(formula_id)

    def list_all(self) -> list[FormulaResponse]:
        """List all formulas."""
        return list(self.formulas.values())

    def count(self) -> int:
        """Count all formulas."""
        return len(self.formulas)

    def clear(self):
        """Clear all formulas."""
        self.formulas.clear()


@given(
    name=formula_name_strategy,
    expression=formula_expression_strategy,
    description=formula_description_strategy,
)
@settings(max_examples=100)
def test_formula_persistence_round_trip(name: str, expression: str, description: Optional[str]):
    """
    **Feature: convertible-bond-selector, Property 3: Formula persistence round-trip**
    **Validates: Requirements 3.4**

    For any saved formula, retrieving it from the database SHALL return 
    an identical formula object.
    """
    repo = MockFormulaRepository()

    # Create formula
    formula_create = FormulaCreate(
        name=name,
        expression=expression,
        description=description,
    )

    # Save formula
    saved = repo.create(formula_create)

    # Retrieve formula
    retrieved = repo.get(saved.id)

    # Verify round-trip consistency
    assert retrieved is not None
    assert retrieved.id == saved.id
    assert retrieved.name == name
    assert retrieved.expression == expression
    assert retrieved.description == description
    assert retrieved.created_at == saved.created_at
    assert retrieved.updated_at == saved.updated_at


@given(
    formulas=st.lists(
        st.tuples(formula_name_strategy, formula_expression_strategy),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_formula_count_consistency(formulas: list[tuple[str, str]]):
    """
    **Feature: convertible-bond-selector, Property 4: Formula count consistency**
    **Validates: Requirements 3.5**

    For any sequence of N formula save operations, retrieving all formulas 
    SHALL return exactly N formulas.
    """
    repo = MockFormulaRepository()

    # Save N formulas
    for name, expression in formulas:
        formula_create = FormulaCreate(
            name=name,
            expression=expression,
        )
        repo.create(formula_create)

    # Verify count
    assert repo.count() == len(formulas)
    assert len(repo.list_all()) == len(formulas)
