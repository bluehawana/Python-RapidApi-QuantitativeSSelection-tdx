"""Service for fetching and transforming convertible bond data."""

import logging
from typing import List, Optional
from datetime import datetime

import pandas as pd

from app.models.schemas import ConvertibleBond
from app.services.qstock_client import get_qstock_client

logger = logging.getLogger(__name__)


# Column mapping from QStock to our schema
# QStock uses East Money data with Chinese column names
COLUMN_MAPPING = {
    # From realtime_data
    '代码': 'code',
    '名称': 'name',
    '最新': 'price',
    '涨幅': 'change_pct',
    '换手率': 'turnover_rate',
    '成交量': 'volume',
    '成交额': 'turnover',
    '昨收': 'prev_close',
    '今开': 'open_price',
    '最高': 'high',
    '最低': 'low',
    # From bond_info
    '债券代码': 'bond_code',
    '债券名称': 'bond_name',
    '正股代码': 'stock_code',
    '正股名称': 'stock_name',
    '债券评级': 'credit_rating',
    '发行规模(亿)': 'issue_size',
    '上市日期': 'listing_date',
    '到期日期': 'expire_date',
    '期限(年)': 'term_years',
}


def transform_bond_data(df: pd.DataFrame) -> List[ConvertibleBond]:
    """Transform raw QStock data to ConvertibleBond models.

    Args:
        df: Raw DataFrame from QStock (East Money)

    Returns:
        List of ConvertibleBond objects
    """
    bonds = []

    for _, row in df.iterrows():
        try:
            # Extract values with fallbacks - QStock uses '最新' for current price
            price = _safe_float(row.get('最新', row.get('价格', 0)))

            # QStock doesn't provide premium_rate directly, set to 0 for now
            # This can be calculated later if we have conversion price and stock price
            premium_rate = _safe_float(row.get('转股溢价率', 0))

            # Get remaining years from bond info
            remaining_years = _safe_float(row.get('期限(年)', 0))

            # Calculate double_low (price + premium_rate)
            double_low = price + premium_rate

            bond = ConvertibleBond(
                code=str(row.get('代码', row.get('债券代码', ''))),
                name=str(row.get('名称', row.get('债券名称', ''))),
                price=price,
                premium_rate=premium_rate,
                ytm=_safe_float(row.get('到期收益率', 0)),
                remaining_years=remaining_years,
                credit_rating=str(row.get('债券评级', 'N/A')),
                stock_code=str(row.get('正股代码', '')),
                stock_name=str(row.get('正股名称', '')),
                stock_price=_safe_float(row.get('正股价', 0)),
                conversion_price=_safe_float(row.get('转股价', 0)),
                conversion_value=_safe_float(row.get('转股价值', 0)),
                double_low=double_low,
                # Additional fields from QStock
                change_pct=_safe_float(row.get('涨幅', 0)),
                turnover_rate=_safe_float(row.get('换手率', 0)),
                volume=_safe_float(row.get('成交量', 0)),
                turnover=_safe_float(row.get('成交额', 0)),
            )
            bonds.append(bond)
        except Exception as e:
            logger.warning(f"Failed to transform bond row: {e}")
            continue

    logger.info(f"Transformed {len(bonds)} bonds from {len(df)} rows")
    return bonds


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value (never NaN or infinity)
    """
    import math

    if value is None:
        return default

    # Handle pandas NA
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    # Handle infinity
    if isinstance(value, float) and math.isinf(value):
        return default

    try:
        # Handle percentage strings like "12.5%"
        if isinstance(value, str):
            value = value.strip().rstrip('%')
        result = float(value)
        # Ensure result is not NaN or infinity
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class BondDataService:
    """Service for managing convertible bond data."""

    def __init__(self):
        """Initialize the bond data service."""
        self._cache: Optional[List[ConvertibleBond]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def get_all_bonds(self, force_refresh: bool = False) -> List[ConvertibleBond]:
        """Get all convertible bonds.

        Args:
            force_refresh: Force refresh from data source

        Returns:
            List of ConvertibleBond objects
        """
        if not force_refresh and self._is_cache_valid():
            logger.debug("Returning cached bond data")
            return self._cache

        return self.refresh_data()

    def refresh_data(self) -> List[ConvertibleBond]:
        """Refresh bond data from QStock (East Money).

        Returns:
            List of ConvertibleBond objects
        """
        client = get_qstock_client()
        df = client.get_convertible_bonds_full()

        bonds = transform_bond_data(df)

        # Update cache
        self._cache = bonds
        self._cache_time = datetime.utcnow()

        return bonds

    def get_bond_by_code(self, code: str) -> Optional[ConvertibleBond]:
        """Get a specific bond by code.

        Args:
            code: Bond code

        Returns:
            ConvertibleBond or None if not found
        """
        bonds = self.get_all_bonds()
        for bond in bonds:
            if bond.code == code:
                return bond
        return None

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid.

        Returns:
            True if cache is valid, False otherwise
        """
        if self._cache is None or self._cache_time is None:
            return False

        elapsed = (datetime.utcnow() - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds


# Singleton instance
_service: Optional[BondDataService] = None


def get_bond_data_service() -> BondDataService:
    """Get the singleton bond data service instance."""
    global _service
    if _service is None:
        _service = BondDataService()
    return _service
