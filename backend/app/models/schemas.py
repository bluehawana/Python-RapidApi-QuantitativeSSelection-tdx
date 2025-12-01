"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# Convertible Bond schemas
class ConvertibleBond(BaseModel):
    """Convertible bond data model with all screening metrics."""
    code: str = Field(..., description="债券代码")
    name: str = Field(..., description="债券名称")
    price: float = Field(..., description="现价")
    premium_rate: float = Field(default=0.0, description="转股溢价率")
    ytm: float = Field(default=0.0, description="到期收益率")
    remaining_years: float = Field(default=0.0, description="剩余年限")
    credit_rating: str = Field(default="N/A", description="信用评级")
    stock_code: str = Field(default="", description="正股代码")
    stock_name: str = Field(default="", description="正股名称")
    stock_price: float = Field(default=0.0, description="正股价格")
    conversion_price: float = Field(default=0.0, description="转股价")
    conversion_value: float = Field(default=0.0, description="转股价值")
    double_low: float = Field(default=0.0, description="双低值")
    # Additional fields from QStock
    change_pct: float = Field(default=0.0, description="涨跌幅%")
    turnover_rate: float = Field(default=0.0, description="换手率%")
    volume: float = Field(default=0.0, description="成交量")
    turnover: float = Field(default=0.0, description="成交额")


# Formula schemas
class FormulaBase(BaseModel):
    """Base formula schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    expression: str = Field(..., min_length=1)


class FormulaCreate(FormulaBase):
    """Schema for creating a formula."""
    pass


class FormulaUpdate(BaseModel):
    """Schema for updating a formula."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    expression: Optional[str] = Field(None, min_length=1)


class FormulaResponse(FormulaBase):
    """Schema for formula response."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FormulaValidateRequest(BaseModel):
    """Schema for formula validation request."""
    expression: str


class FormulaValidateResponse(BaseModel):
    """Schema for formula validation response."""
    valid: bool
    error: Optional[str] = None
    position: Optional[int] = None


# Screening schemas
class ScreeningExecuteRequest(BaseModel):
    """Schema for screening execution request."""
    formula_id: Optional[UUID] = None
    expression: Optional[str] = None
    sort_by: str = "double_low"
    sort_order: str = "asc"
    page: int = 1
    page_size: int = 50


class ScreeningResultResponse(BaseModel):
    """Schema for screening result response."""
    id: Optional[UUID] = None
    formula_id: Optional[UUID] = None
    executed_at: datetime
    result_count: int
    total_count: int
    page: int
    page_size: int
    bonds: List[ConvertibleBond]


class ScreeningResultSaveRequest(BaseModel):
    """Schema for saving screening results."""
    formula_id: UUID
    bonds: List[ConvertibleBond]


# History schemas
class HistoryEntry(BaseModel):
    """Schema for history entry."""
    id: UUID
    formula_id: UUID
    formula_name: str
    executed_at: datetime
    result_count: int

    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    """Schema for comparing two result sets."""
    result_id_1: UUID
    result_id_2: UUID


class CompareResponse(BaseModel):
    """Schema for comparison response."""
    added: List[ConvertibleBond]
    removed: List[ConvertibleBond]
    unchanged: List[ConvertibleBond]


# Export schemas
class ExportRequest(BaseModel):
    """Schema for export request."""
    result_id: UUID
    format: str = "csv"  # csv or excel
