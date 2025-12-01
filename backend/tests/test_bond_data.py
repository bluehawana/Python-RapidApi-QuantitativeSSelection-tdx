"""Property-based tests for bond data structure.

**Feature: convertible-bond-selector, Property 1: Bond data structure completeness**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import pandas as pd

from app.models.schemas import ConvertibleBond
from app.services.bond_data_service import transform_bond_data, _safe_float


# Strategy for generating valid bond data rows
bond_row_strategy = st.fixed_dictionaries({
    '债券代码': st.text(min_size=6, max_size=6, alphabet='0123456789'),
    '债券简称': st.text(min_size=1, max_size=20),
    '现价': st.floats(min_value=50, max_value=500, allow_nan=False),
    '转股溢价率': st.floats(min_value=-50, max_value=200, allow_nan=False),
    '到期收益率': st.floats(min_value=-20, max_value=50, allow_nan=False),
    '剩余年限': st.floats(min_value=0, max_value=10, allow_nan=False),
    '债券评级': st.sampled_from(['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'BBB']),
    '正股代码': st.text(min_size=6, max_size=6, alphabet='0123456789'),
    '正股简称': st.text(min_size=1, max_size=20),
    '正股价': st.floats(min_value=1, max_value=500, allow_nan=False),
    '转股价': st.floats(min_value=1, max_value=500, allow_nan=False),
    '转股价值': st.floats(min_value=50, max_value=500, allow_nan=False),
})


@given(bond_rows=st.lists(bond_row_strategy, min_size=1, max_size=5))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_bond_data_structure_completeness(bond_rows):
    """
    **Feature: convertible-bond-selector, Property 1: Bond data structure completeness**
    **Validates: Requirements 2.2, 2.3, 2.4**

    For any valid API response from AkShare, the parsed ConvertibleBond object 
    SHALL contain all required fields (code, name, price, premium_rate, ytm, 
    remaining_years, credit_rating).
    """
    # Create DataFrame from generated rows
    df = pd.DataFrame(bond_rows)

    # Transform to ConvertibleBond objects
    bonds = transform_bond_data(df)

    # Verify all bonds have required fields
    assert len(bonds) == len(bond_rows)

    for bond in bonds:
        # Check all required fields are present and have correct types
        assert isinstance(bond.code, str)
        assert len(bond.code) > 0

        assert isinstance(bond.name, str)
        assert len(bond.name) > 0

        assert isinstance(bond.price, float)
        assert bond.price >= 0

        assert isinstance(bond.premium_rate, float)

        assert isinstance(bond.ytm, float)

        assert isinstance(bond.remaining_years, float)
        assert bond.remaining_years >= 0

        assert isinstance(bond.credit_rating, str)

        assert isinstance(bond.stock_code, str)
        assert isinstance(bond.stock_name, str)
        assert isinstance(bond.stock_price, float)
        assert isinstance(bond.conversion_price, float)
        assert isinstance(bond.conversion_value, float)

        # Verify double_low is calculated correctly
        assert isinstance(bond.double_low, float)
        assert abs(bond.double_low - (bond.price + bond.premium_rate)) < 0.001


@given(value=st.one_of(
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(),
    st.none(),
    st.integers(),
))
@settings(max_examples=100)
def test_safe_float_handles_all_inputs(value):
    """Test that _safe_float handles all input types without raising."""
    result = _safe_float(value, default=0.0)

    # Result should always be a float
    assert isinstance(result, float)

    # Result should never be NaN or infinity
    import math
    assert not math.isnan(result)
    assert not math.isinf(result)


def test_transform_empty_dataframe():
    """Test that transform handles empty DataFrame."""
    df = pd.DataFrame()
    bonds = transform_bond_data(df)
    assert bonds == []


def test_transform_partial_data():
    """Test that transform handles partial data gracefully."""
    df = pd.DataFrame([{
        '债券代码': '123456',
        '债券简称': 'Test Bond',
        '现价': 100.0,
        # Missing other fields
    }])

    bonds = transform_bond_data(df)

    # Should still create a bond with defaults for missing fields
    assert len(bonds) == 1
    assert bonds[0].code == '123456'
    assert bonds[0].name == 'Test Bond'
    assert bonds[0].price == 100.0
