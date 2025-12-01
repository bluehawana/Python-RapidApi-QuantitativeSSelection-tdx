"""Service for managing formulas."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.db_models import Formula
from app.models.schemas import FormulaCreate, FormulaUpdate, FormulaResponse
from app.services.formula_parser import validate_formula
from app.core.exceptions import FormulaNotFoundError, FormulaValidationError


class FormulaService:
    """Service for formula CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, formula_data: FormulaCreate) -> FormulaResponse:
        """Create a new formula."""
        # Validate formula syntax
        is_valid, error, position = validate_formula(formula_data.expression)
        if not is_valid:
            raise FormulaValidationError(error)

        formula = Formula(
            name=formula_data.name,
            description=formula_data.description,
            expression=formula_data.expression,
        )
        self.db.add(formula)
        await self.db.flush()
        await self.db.refresh(formula)

        return FormulaResponse.model_validate(formula)

    async def get_by_id(self, formula_id: UUID) -> FormulaResponse:
        """Get a formula by ID."""
        result = await self.db.execute(
            select(Formula).where(Formula.id == formula_id)
        )
        formula = result.scalar_one_or_none()

        if formula is None:
            raise FormulaNotFoundError(str(formula_id))

        return FormulaResponse.model_validate(formula)

    async def list_all(self) -> List[FormulaResponse]:
        """List all formulas."""
        result = await self.db.execute(
            select(Formula).order_by(Formula.created_at.desc())
        )
        formulas = result.scalars().all()

        return [FormulaResponse.model_validate(f) for f in formulas]

    async def update(
        self, formula_id: UUID, formula_data: FormulaUpdate
    ) -> FormulaResponse:
        """Update a formula."""
        result = await self.db.execute(
            select(Formula).where(Formula.id == formula_id)
        )
        formula = result.scalar_one_or_none()

        if formula is None:
            raise FormulaNotFoundError(str(formula_id))

        # Validate new expression if provided
        if formula_data.expression is not None:
            is_valid, error, position = validate_formula(
                formula_data.expression)
            if not is_valid:
                raise FormulaValidationError(error)
            formula.expression = formula_data.expression

        if formula_data.name is not None:
            formula.name = formula_data.name

        if formula_data.description is not None:
            formula.description = formula_data.description

        formula.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(formula)

        return FormulaResponse.model_validate(formula)

    async def delete(self, formula_id: UUID) -> bool:
        """Delete a formula."""
        result = await self.db.execute(
            select(Formula).where(Formula.id == formula_id)
        )
        formula = result.scalar_one_or_none()

        if formula is None:
            raise FormulaNotFoundError(str(formula_id))

        await self.db.delete(formula)
        return True
