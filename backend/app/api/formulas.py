"""Formula CRUD endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import (
    FormulaCreate,
    FormulaUpdate,
    FormulaResponse,
    FormulaValidateRequest,
    FormulaValidateResponse,
)
from app.services.formula_service import FormulaService
from app.services.formula_parser import validate_formula

router = APIRouter()


@router.get("/", response_model=List[FormulaResponse])
async def list_formulas(db: AsyncSession = Depends(get_db)):
    """List all formulas."""
    service = FormulaService(db)
    return await service.list_all()


@router.post("/", response_model=FormulaResponse, status_code=201)
async def create_formula(
    formula_data: FormulaCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new formula."""
    service = FormulaService(db)
    return await service.create(formula_data)


@router.get("/{formula_id}", response_model=FormulaResponse)
async def get_formula(formula_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a formula by ID."""
    service = FormulaService(db)
    return await service.get_by_id(formula_id)


@router.put("/{formula_id}", response_model=FormulaResponse)
async def update_formula(
    formula_id: UUID,
    formula_data: FormulaUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a formula."""
    service = FormulaService(db)
    return await service.update(formula_id, formula_data)


@router.delete("/{formula_id}", status_code=204)
async def delete_formula(formula_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a formula."""
    service = FormulaService(db)
    await service.delete(formula_id)
    return None


@router.post("/validate", response_model=FormulaValidateResponse)
async def validate_formula_endpoint(request: FormulaValidateRequest):
    """Validate formula syntax."""
    is_valid, error, position = validate_formula(request.expression)
    return FormulaValidateResponse(valid=is_valid, error=error, position=position)
