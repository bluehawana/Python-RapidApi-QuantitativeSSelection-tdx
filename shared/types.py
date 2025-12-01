"""
Shared type definitions for the Convertible Bond Selection System.
These types are used by both frontend (via generated TypeScript) and backend.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class ConvertibleBond(BaseModel):
    """Convertible bond data model with all screening metrics."""
    code: str                    # 债券代码
    name: str                    # 债券名称
    price: float                 # 现价
    premium_rate: float          # 转股溢价率
    ytm: float                   # 到期收益率
    remaining_years: float       # 剩余年限
    credit_rating: str           # 信用评级
    stock_code: str              # 正股代码
    stock_name: str              # 正股名称
    stock_price: float           # 正股价格
    conversion_price: float      # 转股价
    conversion_value: float      # 转股价值
    double_low: float            # 双低值 (price + premium_rate)


class Formula(BaseModel):
    """Selection formula model."""
    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    expression: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScreeningResult(BaseModel):
    """Screening result snapshot."""
    id: Optional[UUID] = None
    formula_id: UUID
    executed_at: datetime
    result_count: int
    bonds: List[ConvertibleBond]
