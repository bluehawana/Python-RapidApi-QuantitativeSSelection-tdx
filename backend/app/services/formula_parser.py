"""Formula parser for convertible bond screening expressions.

Supports expressions like:
- price < 130
- premium_rate < 20 AND ytm > 0
- (price < 120) OR (premium_rate < 15)
- NOT (price > 150)
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any, Union


class TokenType(Enum):
    """Token types for formula lexer."""
    FIELD = auto()       # Bond field names
    NUMBER = auto()      # Numeric values
    STRING = auto()      # String values (quoted)
    OPERATOR = auto()    # Comparison operators
    LOGICAL = auto()     # AND, OR
    NOT = auto()         # NOT
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    EOF = auto()         # End of input


@dataclass
class Token:
    """Token representation."""
    type: TokenType
    value: Any
    position: int


# Valid bond fields for screening
VALID_FIELDS = {
    'price', 'premium_rate', 'ytm', 'remaining_years', 'credit_rating',
    'stock_price', 'conversion_price', 'conversion_value', 'double_low',
    'code', 'name', 'stock_code', 'stock_name',
}

# Comparison operators
COMPARISON_OPERATORS = {'>', '<', '>=', '<=', '==', '!='}

# Logical operators
LOGICAL_OPERATORS = {'AND', 'OR'}


class Lexer:
    """Tokenizer for formula expressions."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.current_char = text[0] if text else None

    def error(self, message: str):
        """Raise a lexer error."""
        from app.core.exceptions import FormulaParseError
        raise FormulaParseError(message, position=self.pos)

    def advance(self):
        """Move to the next character."""
        self.pos += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def read_number(self) -> Token:
        """Read a numeric value."""
        start_pos = self.pos
        result = ''

        # Handle negative numbers
        if self.current_char == '-':
            result += self.current_char
            self.advance()

        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):
            result += self.current_char
            self.advance()

        try:
            value = float(result)
            return Token(TokenType.NUMBER, value, start_pos)
        except ValueError:
            self.error(f"Invalid number: {result}")

    def read_string(self) -> Token:
        """Read a quoted string value."""
        start_pos = self.pos
        quote_char = self.current_char
        self.advance()  # Skip opening quote

        result = ''
        while self.current_char is not None and self.current_char != quote_char:
            result += self.current_char
            self.advance()

        if self.current_char != quote_char:
            self.error("Unterminated string")

        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, result, start_pos)

    def read_identifier(self) -> Token:
        """Read an identifier (field name or keyword)."""
        start_pos = self.pos
        result = ''

        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()

        # Check if it's a keyword
        upper_result = result.upper()
        if upper_result in LOGICAL_OPERATORS:
            return Token(TokenType.LOGICAL, upper_result, start_pos)
        elif upper_result == 'NOT':
            return Token(TokenType.NOT, 'NOT', start_pos)
        elif result.lower() in VALID_FIELDS:
            return Token(TokenType.FIELD, result.lower(), start_pos)
        else:
            self.error(f"Unknown field: {result}")

    def read_operator(self) -> Token:
        """Read a comparison operator."""
        start_pos = self.pos
        result = self.current_char
        self.advance()

        # Check for two-character operators
        if self.current_char == '=' and result in ('>', '<', '=', '!'):
            result += self.current_char
            self.advance()

        if result in COMPARISON_OPERATORS:
            return Token(TokenType.OPERATOR, result, start_pos)
        else:
            self.error(f"Unknown operator: {result}")

    def get_next_token(self) -> Token:
        """Get the next token from the input."""
        while self.current_char is not None:
            # Skip whitespace
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            # Numbers (including negative)
            if self.current_char.isdigit() or (self.current_char == '-' and self.peek_next().isdigit()):
                return self.read_number()

            # Strings
            if self.current_char in ('"', "'"):
                return self.read_string()

            # Identifiers (fields and keywords)
            if self.current_char.isalpha() or self.current_char == '_':
                return self.read_identifier()

            # Operators
            if self.current_char in ('>', '<', '=', '!'):
                return self.read_operator()

            # Parentheses
            if self.current_char == '(':
                token = Token(TokenType.LPAREN, '(', self.pos)
                self.advance()
                return token

            if self.current_char == ')':
                token = Token(TokenType.RPAREN, ')', self.pos)
                self.advance()
                return token

            self.error(f"Unexpected character: {self.current_char}")

        return Token(TokenType.EOF, None, self.pos)

    def peek_next(self) -> str:
        """Peek at the next character without advancing."""
        peek_pos = self.pos + 1
        if peek_pos < len(self.text):
            return self.text[peek_pos]
        return ''

    def tokenize(self) -> List[Token]:
        """Tokenize the entire input."""
        tokens = []
        while True:
            token = self.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


# AST Node types
@dataclass
class ASTNode:
    """Base class for AST nodes."""
    pass


@dataclass
class ComparisonNode(ASTNode):
    """Comparison expression node (e.g., price < 130)."""
    field: str
    operator: str
    value: Union[float, str]


@dataclass
class LogicalNode(ASTNode):
    """Logical expression node (AND, OR)."""
    operator: str  # 'AND' or 'OR'
    left: ASTNode
    right: ASTNode


@dataclass
class NotNode(ASTNode):
    """NOT expression node."""
    operand: ASTNode


class Parser:
    """Recursive descent parser for formula expressions.

    Grammar:
        expression := or_expr
        or_expr    := and_expr (OR and_expr)*
        and_expr   := not_expr (AND not_expr)*
        not_expr   := NOT not_expr | primary
        primary    := comparison | LPAREN expression RPAREN
        comparison := FIELD OPERATOR value
        value      := NUMBER | STRING
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = tokens[0] if tokens else None

    def error(self, message: str):
        """Raise a parser error."""
        from app.core.exceptions import FormulaParseError
        position = self.current_token.position if self.current_token else 0
        raise FormulaParseError(message, position=position)

    def advance(self):
        """Move to the next token."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type."""
        if self.current_token is None or self.current_token.type != token_type:
            self.error(
                f"Expected {token_type.name}, got {self.current_token.type.name if self.current_token else 'EOF'}")
        token = self.current_token
        self.advance()
        return token

    def parse(self) -> ASTNode:
        """Parse the token stream into an AST."""
        if not self.tokens or self.tokens[0].type == TokenType.EOF:
            self.error("Empty expression")

        result = self.parse_or_expr()

        if self.current_token and self.current_token.type != TokenType.EOF:
            self.error(f"Unexpected token: {self.current_token.value}")

        return result

    def parse_or_expr(self) -> ASTNode:
        """Parse OR expressions."""
        left = self.parse_and_expr()

        while self.current_token and self.current_token.type == TokenType.LOGICAL and self.current_token.value == 'OR':
            self.advance()
            right = self.parse_and_expr()
            left = LogicalNode(operator='OR', left=left, right=right)

        return left

    def parse_and_expr(self) -> ASTNode:
        """Parse AND expressions."""
        left = self.parse_not_expr()

        while self.current_token and self.current_token.type == TokenType.LOGICAL and self.current_token.value == 'AND':
            self.advance()
            right = self.parse_not_expr()
            left = LogicalNode(operator='AND', left=left, right=right)

        return left

    def parse_not_expr(self) -> ASTNode:
        """Parse NOT expressions."""
        if self.current_token and self.current_token.type == TokenType.NOT:
            self.advance()
            operand = self.parse_not_expr()
            return NotNode(operand=operand)

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        """Parse primary expressions (comparisons or parenthesized expressions)."""
        if self.current_token is None:
            self.error("Unexpected end of expression")

        # Parenthesized expression
        if self.current_token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_or_expr()
            self.expect(TokenType.RPAREN)
            return expr

        # Comparison
        if self.current_token.type == TokenType.FIELD:
            return self.parse_comparison()

        self.error(f"Unexpected token: {self.current_token.value}")

    def parse_comparison(self) -> ComparisonNode:
        """Parse a comparison expression."""
        field_token = self.expect(TokenType.FIELD)
        operator_token = self.expect(TokenType.OPERATOR)

        if self.current_token is None:
            self.error("Expected value after operator")

        if self.current_token.type == TokenType.NUMBER:
            value = self.current_token.value
            self.advance()
        elif self.current_token.type == TokenType.STRING:
            value = self.current_token.value
            self.advance()
        else:
            self.error(
                f"Expected number or string, got {self.current_token.type.name}")

        return ComparisonNode(
            field=field_token.value,
            operator=operator_token.value,
            value=value
        )


def parse_formula(expression: str) -> ASTNode:
    """Parse a formula expression string into an AST.

    Args:
        expression: Formula expression string

    Returns:
        AST root node

    Raises:
        FormulaParseError: If parsing fails
    """
    lexer = Lexer(expression)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


# Field type definitions for validation
NUMERIC_FIELDS = {
    'price', 'premium_rate', 'ytm', 'remaining_years',
    'stock_price', 'conversion_price', 'conversion_value', 'double_low',
}

STRING_FIELDS = {
    'code', 'name', 'stock_code', 'stock_name', 'credit_rating',
}


class FormulaValidator:
    """Validator for formula AST nodes."""

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, node: ASTNode) -> bool:
        """Validate an AST node and its children.

        Args:
            node: AST node to validate

        Returns:
            True if valid, False otherwise
        """
        self.errors = []
        self._validate_node(node)
        return len(self.errors) == 0

    def _validate_node(self, node: ASTNode):
        """Recursively validate an AST node."""
        if isinstance(node, ComparisonNode):
            self._validate_comparison(node)
        elif isinstance(node, LogicalNode):
            self._validate_node(node.left)
            self._validate_node(node.right)
        elif isinstance(node, NotNode):
            self._validate_node(node.operand)

    def _validate_comparison(self, node: ComparisonNode):
        """Validate a comparison node."""
        # Check field exists
        if node.field not in VALID_FIELDS:
            self.errors.append(f"Unknown field: {node.field}")
            return

        # Check operator compatibility with field type
        if node.field in NUMERIC_FIELDS:
            if not isinstance(node.value, (int, float)):
                self.errors.append(
                    f"Field '{node.field}' requires numeric value, got string"
                )
            if node.operator not in ('>', '<', '>=', '<=', '==', '!='):
                self.errors.append(
                    f"Invalid operator '{node.operator}' for numeric field"
                )
        elif node.field in STRING_FIELDS:
            if not isinstance(node.value, str):
                self.errors.append(
                    f"Field '{node.field}' requires string value, got number"
                )
            if node.operator not in ('==', '!='):
                self.errors.append(
                    f"String field '{node.field}' only supports == and != operators"
                )


def validate_formula(expression: str) -> tuple:
    """Validate a formula expression.

    Args:
        expression: Formula expression string

    Returns:
        Tuple of (is_valid, error_message, position)
    """
    try:
        ast = parse_formula(expression)
        validator = FormulaValidator()
        is_valid = validator.validate(ast)

        if is_valid:
            return (True, None, None)
        else:
            return (False, "; ".join(validator.errors), None)

    except Exception as e:
        from app.core.exceptions import FormulaParseError
        if isinstance(e, FormulaParseError):
            return (False, e.message, e.position)
        return (False, str(e), None)


def serialize_ast(node: ASTNode) -> str:
    """Serialize an AST node back to a formula string.

    Args:
        node: AST node to serialize

    Returns:
        Formula expression string
    """
    if isinstance(node, ComparisonNode):
        if isinstance(node.value, str):
            return f"{node.field} {node.operator} '{node.value}'"
        else:
            return f"{node.field} {node.operator} {node.value}"

    elif isinstance(node, LogicalNode):
        left_str = serialize_ast(node.left)
        right_str = serialize_ast(node.right)

        # Add parentheses for clarity
        if isinstance(node.left, LogicalNode) and node.left.operator != node.operator:
            left_str = f"({left_str})"
        if isinstance(node.right, LogicalNode) and node.right.operator != node.operator:
            right_str = f"({right_str})"

        return f"{left_str} {node.operator} {right_str}"

    elif isinstance(node, NotNode):
        operand_str = serialize_ast(node.operand)
        if isinstance(node.operand, (LogicalNode, NotNode)):
            return f"NOT ({operand_str})"
        return f"NOT {operand_str}"

    raise ValueError(f"Unknown node type: {type(node)}")


def normalize_formula(expression: str) -> str:
    """Parse and re-serialize a formula to normalize its format.

    Args:
        expression: Formula expression string

    Returns:
        Normalized formula string
    """
    ast = parse_formula(expression)
    return serialize_ast(ast)
