"""Custom exceptions for the application."""

from typing import Optional


class BondSelectorException(Exception):
    """Base exception for the bond selector application."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


class DataFetchError(BondSelectorException):
    """Exception raised when data fetching fails."""

    def __init__(self, message: str, source: str = "unknown"):
        super().__init__(message, code="data_fetch_error")
        self.source = source


class FormulaParseError(BondSelectorException):
    """Exception raised when formula parsing fails."""

    def __init__(self, message: str, position: Optional[int] = None):
        super().__init__(message, code="formula_parse_error")
        self.position = position


class FormulaValidationError(BondSelectorException):
    """Exception raised when formula validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code="formula_validation_error")
        self.field = field


class FormulaNotFoundError(BondSelectorException):
    """Exception raised when a formula is not found."""

    def __init__(self, formula_id: str):
        super().__init__(
            f"Formula not found: {formula_id}", code="formula_not_found")
        self.formula_id = formula_id


class ScreeningResultNotFoundError(BondSelectorException):
    """Exception raised when a screening result is not found."""

    def __init__(self, result_id: str):
        super().__init__(
            f"Screening result not found: {result_id}", code="result_not_found")
        self.result_id = result_id


class DatabaseError(BondSelectorException):
    """Exception raised when a database operation fails."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message, code="database_error")
        self.operation = operation
