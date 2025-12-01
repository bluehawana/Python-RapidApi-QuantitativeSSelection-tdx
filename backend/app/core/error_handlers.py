"""Error handlers for FastAPI application."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    BondSelectorException,
    DataFetchError,
    FormulaParseError,
    FormulaValidationError,
    FormulaNotFoundError,
    ScreeningResultNotFoundError,
    DatabaseError,
)

logger = logging.getLogger(__name__)


async def bond_selector_exception_handler(
    request: Request, exc: BondSelectorException
) -> JSONResponse:
    """Handle BondSelectorException and its subclasses."""
    logger.error(f"BondSelectorException: {exc.code} - {exc.message}")

    status_code = 500

    if isinstance(exc, (FormulaNotFoundError, ScreeningResultNotFoundError)):
        status_code = 404
    elif isinstance(exc, (FormulaParseError, FormulaValidationError)):
        status_code = 400
    elif isinstance(exc, DataFetchError):
        status_code = 502
    elif isinstance(exc, DatabaseError):
        status_code = 500

    response_data = {
        "error": exc.code,
        "message": exc.message,
    }

    # Add extra fields for specific exceptions
    if isinstance(exc, FormulaParseError) and exc.position is not None:
        response_data["position"] = exc.position
    elif isinstance(exc, FormulaValidationError) and exc.field is not None:
        response_data["field"] = exc.field
    elif isinstance(exc, DataFetchError):
        response_data["source"] = exc.source

    return JSONResponse(status_code=status_code, content=response_data)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )


def register_exception_handlers(app):
    """Register exception handlers with the FastAPI app."""
    app.add_exception_handler(BondSelectorException,
                              bond_selector_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
