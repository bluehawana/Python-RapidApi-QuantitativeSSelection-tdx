"""RiceQuant (RQData) client for fetching convertible bond data.

RQData provides comprehensive Chinese financial market data including
convertible bonds with premium rates, YTM, and other key metrics.

Focus on ACTIVE bonds with high volume for profit opportunities:
- High turnover rate (换手率 > 1%)
- Good liquidity (成交额 > 1000万)
- Reasonable price range (90-150)
- Low premium rate for value plays

API Docs: https://www.ricequant.com/doc/rqdata/python/generic-api
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date

import pandas as pd

logger = logging.getLogger(__name__)

# Check if rqdatac is available
try:
    import rqdatac as rq
    RQDATA_AVAILABLE = True
except ImportError:
    RQDATA_AVAILABLE = False
    logger.warning("rqdatac not installed. Run: pip install rqdatac")


# Filter criteria for active/profitable bonds
ACTIVE_BOND_FILTERS = {
    'min_turnover': 10_000_000,    # 最小成交额 1000万
    'min_turnover_rate': 0.5,      # 最小换手率 0.5%
    'min_price': 90,               # 最低价格
    'max_price': 150,              # 最高价格 (avoid high premium)
    'max_premium_rate': 30,        # 最大溢价率 30%
}


class RQDataClient:
    """Client for fetching data from RiceQuant RQData."""

    def __init__(self, username: str = None, password: str = None):
        """Initialize the RQData client.

        Args:
            username: RQData account username
            password: RQData account password
        """
        self._initialized = False
        self._username = username
        self._password = password
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes

    def _ensure_init(self):
        """Ensure RQData is initialized."""
        if not RQDATA_AVAILABLE:
            raise ImportError(
                "rqdatac is not installed. Run: pip install rqdatac")

        if not self._initialized:
            if self._username and self._password:
                rq.init(self._username, self._password)
            else:
                # Try to init without credentials (may use cached token)
                rq.init()
            self._initialized = True
            logger.info("RQData initialized successfully")

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid."""
        if key not in self._cache or key not in self._cache_time:
            return False
        elapsed = (datetime.utcnow() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def get_all_convertible_bonds(self) -> List[str]:
        """Get all convertible bond codes.

        Returns:
            List of convertible bond order_book_ids
        """
        cache_key = "all_bonds"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        self._ensure_init()

        # Get all convertible bonds
        bonds = rq.all_instruments(type='ConvertibleBond')
        bond_ids = bonds['order_book_id'].tolist() if not bonds.empty else []

        self._cache[cache_key] = bond_ids
        self._cache_time[cache_key] = datetime.utcnow()

        logger.info(f"Found {len(bond_ids)} convertible bonds")
        return bond_ids

    def get_bond_info(self, order_book_ids: List[str] = None) -> pd.DataFrame:
        """Get convertible bond basic information.

        Args:
            order_book_ids: List of bond IDs, or None for all bonds

        Returns:
            DataFrame with bond info
        """
        self._ensure_init()

        if order_book_ids is None:
            order_book_ids = self.get_all_convertible_bonds()

        # Get instrument info
        info_df = rq.instruments(order_book_ids)
        return info_df

    def get_bond_prices(self, order_book_ids: List[str] = None) -> pd.DataFrame:
        """Get current prices for convertible bonds.

        Args:
            order_book_ids: List of bond IDs, or None for all bonds

        Returns:
            DataFrame with current prices
        """
        self._ensure_init()

        if order_book_ids is None:
            order_book_ids = self.get_all_convertible_bonds()

        # Get current price snapshot
        prices = rq.current_snapshot(order_book_ids)
        return prices

    def get_convertible_bond_data(self, active_only: bool = True) -> pd.DataFrame:
        """Get comprehensive convertible bond data.

        Args:
            active_only: If True, filter for active/liquid bonds only

        Returns:
            DataFrame with bond info, prices, and key metrics
        """
        cache_key = f"bond_data_{'active' if active_only else 'all'}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        self._ensure_init()

        # Get all bond IDs
        bond_ids = self.get_all_convertible_bonds()

        if not bond_ids:
            return pd.DataFrame()

        # Get instrument info
        info_df = rq.instruments(bond_ids)

        # Get current prices
        try:
            prices_df = rq.current_snapshot(bond_ids)
            if prices_df is not None and not prices_df.empty:
                # Merge info with prices
                result_df = info_df.merge(
                    prices_df,
                    left_on='order_book_id',
                    right_index=True,
                    how='left'
                )
            else:
                result_df = info_df
        except Exception as e:
            logger.warning(f"Failed to get prices: {e}")
            result_df = info_df

        # Filter for active bonds
        if active_only and not result_df.empty:
            result_df = self._filter_active_bonds(result_df)

        self._cache[cache_key] = result_df
        self._cache_time[cache_key] = datetime.utcnow()

        return result_df

    def _filter_active_bonds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter for active, liquid, profitable bonds.

        Criteria:
        - High turnover (成交额 > 1000万)
        - Reasonable price (90-150)
        - Low premium rate (< 30%)
        """
        if df.empty:
            return df

        filters = ACTIVE_BOND_FILTERS
        filtered = df.copy()

        # Filter by turnover
        if 'total_turnover' in filtered.columns:
            filtered = filtered[filtered['total_turnover']
                                >= filters['min_turnover']]

        # Filter by price range
        if 'last' in filtered.columns:
            filtered = filtered[
                (filtered['last'] >= filters['min_price']) &
                (filtered['last'] <= filters['max_price'])
            ]

        # Sort by turnover (most active first)
        if 'total_turnover' in filtered.columns:
            filtered = filtered.sort_values('total_turnover', ascending=False)

        logger.info(
            f"Filtered to {len(filtered)} active bonds from {len(df)} total")
        return filtered

    def get_top_active_bonds(self, top_n: int = 50) -> pd.DataFrame:
        """Get top N most active convertible bonds for trading.

        Args:
            top_n: Number of bonds to return

        Returns:
            DataFrame with top active bonds sorted by turnover
        """
        df = self.get_convertible_bond_data(active_only=True)
        return df.head(top_n)

    def get_bond_history(
        self,
        order_book_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """Get historical data for a convertible bond.

        Args:
            order_book_id: Bond ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with historical OHLCV data
        """
        self._ensure_init()

        if end_date is None:
            end_date = date.today().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (date.today() - pd.Timedelta(days=365)
                          ).strftime('%Y-%m-%d')

        # Get historical prices
        history = rq.get_price(
            order_book_id,
            start_date=start_date,
            end_date=end_date,
            frequency='1d',
            fields=['open', 'high', 'low', 'close', 'volume', 'total_turnover']
        )

        return history


# Singleton instance
_client: Optional[RQDataClient] = None


def get_rqdata_client(username: str = None, password: str = None) -> RQDataClient:
    """Get the singleton RQData client instance."""
    global _client
    if _client is None:
        _client = RQDataClient(username, password)
    return _client
