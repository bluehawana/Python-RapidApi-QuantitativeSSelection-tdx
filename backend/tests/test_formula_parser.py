"""Property-based tests for formula parser.

**Feature: convertible-bond-selector, Property 2: Formula parsing round-trip**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.services.formula_parser import (
    parse_formula, serialize_ast, normalize_formula, validate_formula,
    VALID_FIELDS, NUMERIC_FIELDS, STRING_FIELDS, COMPARISON_OPERATORS,
    ComparisonNode, LogicalNode, NotNode,
)


# Strategy for generating valid numeric field names
numeric_field_strategy = st.sampled_from(list(NUMERIC_FIELDS))

# Strategy for generating valid string field names
string_field_strategy = st.sampled_from(list(STRING_FIELDS))

# Strategy for generating numeric comparison operators
numeric_operator_strategy = st.sampled_from(['>', '<', '>=', '<=', '==', '!='])

# Strategy for generating string comparison operators
string_operator_strategy = st.sampled_from(['==', '!='])

# Strategy for generating numeric values
numeric_value_strategy = st.floats(
    min_value=-1000, max_value=1000,
    allow_nan=False, allow_infinity=False
).map(lambda x: round(x, 2))

# Strategy for generating string values (simple alphanumeric)
string_value_strategy = st.text(
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
    min_size=1, max_size=10
)


# Strategy for generating simple comparison expressions
@st.composite
def simple_comparison_strategy(draw):
    """Generate a simple comparison expression."""
    use_numeric = draw(st.booleans())

    if use_numeric:
        field = draw(numeric_field_strategy)
        operator = draw(numeric_operator_strategy)
        value = draw(numeric_value_strategy)
        return f"{field} {operator} {value}"
    else:
        field = draw(string_field_strategy)
        operator = draw(string_operator_strategy)
        value = draw(string_value_strategy)
        return f"{field} {operator} '{value}'"


# Strategy for generating compound expressions
@st.composite
def compound_expression_strategy(draw, max_depth=2):
    """Generate a compound expression with AND/OR."""
    if max_depth <= 0 or draw(st.booleans()):
        return draw(simple_comparison_strategy())

    left = draw(compound_expression_strategy(max_depth=max_depth-1))
    right = draw(compound_expression_strategy(max_depth=max_depth-1))
    operator = draw(st.sampled_from(['AND', 'OR']))

    # Optionally add parentheses
    if draw(st.booleans()):
        left = f"({left})"
    if draw(st.booleans()):
        right = f"({right})"

    return f"{left} {operator} {right}"


@given(expression=simple_comparison_strategy())
@settings(max_examples=100)
def test_simple_formula_parsing_round_trip(expression: str):
    """
    **Feature: convertible-bond-selector, Property 2: Formula parsing round-trip**
    **Validates: Requirements 3.3**

    For any valid simple formula expression, parsing then serializing back 
    to string SHALL produce a semantically equivalent expression.
    """
    # Parse the expression
    ast = parse_formula(expression)

    # Serialize back to string
    serialized = serialize_ast(ast)

    # Parse the serialized string
    ast2 = parse_formula(serialized)

    # Serialize again
    serialized2 = serialize_ast(ast2)

    # The two serializations should be identical (normalized form)
    assert serialized == serialized2


@given(expression=compound_expression_strategy(max_depth=2))
@settings(max_examples=100)
def test_compound_formula_parsing_round_trip(expression: str):
    """
    **Feature: convertible-bond-selector, Property 2: Formula parsing round-trip**
    **Validates: Requirements 3.3**

    For any valid compound formula expression, parsing then serializing back 
    to string SHALL produce a semantically equivalent expression.
    """
    # Parse the expression
    ast = parse_formula(expression)

    # Serialize back to string
    serialized = serialize_ast(ast)

    # Parse the serialized string
    ast2 = parse_formula(serialized)

    # Serialize again
    serialized2 = serialize_ast(ast2)

    # The two serializations should be identical (normalized form)
    assert serialized == serialized2


def test_parse_simple_comparison():
    """Test parsing a simple comparison."""
    ast = parse_formula("price < 130")
    assert isinstance(ast, ComparisonNode)
    assert ast.field == "price"
    assert ast.operator == "<"
    assert ast.value == 130.0


def test_parse_and_expression():
    """Test parsing an AND expression."""
    ast = parse_formula("price < 130 AND premium_rate < 20")
    assert isinstance(ast, LogicalNode)
    assert ast.operator == "AND"
    assert isinstance(ast.left, ComparisonNode)
    assert isinstance(ast.right, ComparisonNode)


def test_parse_or_expression():
    """Test parsing an OR expression."""
    ast = parse_formula("ytm > 0 OR remaining_years < 3")
    assert isinstance(ast, LogicalNode)
    assert ast.operator == "OR"


def test_parse_not_expression():
    """Test parsing a NOT expression."""
    ast = parse_formula("NOT price > 150")
    assert isinstance(ast, NotNode)
    assert isinstance(ast.operand, ComparisonNode)


def test_parse_parenthesized_expression():
    """Test parsing a parenthesized expression."""
    ast = parse_formula("(price < 120) AND (premium_rate < 15)")
    assert isinstance(ast, LogicalNode)


def test_parse_string_comparison():
    """Test parsing a string comparison."""
    ast = parse_formula("credit_rating == 'AA'")
    assert isinstance(ast, ComparisonNode)
    assert ast.field == "credit_rating"
    assert ast.value == "AA"


def test_validate_valid_formula():
    """Test validation of a valid formula."""
    is_valid, error, position = validate_formula(
        "price < 130 AND premium_rate < 20")
    assert is_valid is True
    assert error is None


def test_validate_invalid_field():
    """Test validation of formula with invalid field."""
    is_valid, error, position = validate_formula("invalid_field < 130")
    assert is_valid is False
    assert "Unknown field" in error


def test_validate_type_mismatch():
    """Test validation of formula with type mismatch."""
    is_valid, error, position = validate_formula("price == 'string'")
    assert is_valid is False
    assert "numeric value" in error


def test_serialize_simple():
    """Test serialization of simple comparison."""
    ast = ComparisonNode(field="price", operator="<", value=130.0)
    result = serialize_ast(ast)
    assert result == "price < 130.0"


def test_serialize_string_value():
    """Test serialization with string value."""
    ast = ComparisonNode(field="credit_rating", operator="==", value="AA")
    result = serialize_ast(ast)
    assert result == "credit_rating == 'AA'"
