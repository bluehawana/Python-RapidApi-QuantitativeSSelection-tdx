"""BaoStock client for fetching convertible bond data.

BaoStock provides reliable access to Chinese stock market data including
convertible bonds, with better stability than East Money APIs.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
import baostock as bs

logger = logging.getLogger(__name__)


class BaoStockClient:
    """Client for fetching stock and bond data from BaoStock."""

    def __init__(self):
        """Initialize the BaoStock client."""
        self._logged_in = False
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes

    def _ensure_login(self):
        """Ensure we're logged into BaoStock."""
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != '0':
                raise Exception(f"BaoStock login failed: {lg.error_msg}")
            self._logged_in = True
            logger.info("Successfully logged into BaoStock")

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid."""
        if key not in self._cache or key not in self._cache_time:
            return False
        elapsed = (datetime.utcnow() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def __del__(self):
        """Logout when client is destroyed."""
        if self._logged_in:
            try:
                bs.logout()
            except Exception:
                pass

    def get_stock_basic(self) -> pd.DataFrame:
        """Get basic information of all stocks and bonds."""
        cache_key = "stock_basic"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        self._ensure_login()
        rs = bs.query_stock_basic()
        if rs.error_code != '0':
            raise Exception(f"Failed to get stock basic info: {rs.error_msg}")

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields)
        self._cache[cache_key] = df
        self._cache_time[cache_key] = datetime.utcnow()
        return df

    def get_convertible_bonds(self) -> pd.DataFrame:
        """Get all convertible bonds basic info.

        Convertible bonds have codes:
        - Shanghai: 11xxxx (sh.11xxxx)
        - Shenzhen: 12xxxx (sz.12xxxx)
        """
        cache_key = "convertible_bonds"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        stock_df = self.get_stock_basic()

        # Filter convertible bonds by code pattern
        bond_mask = (
            stock_df['code'].str.contains(r'^sh\.11\d{4}$', na=False, regex=True) |
            stock_df['code'].str.contains(
                r'^sz\.12\d{4}$', na=False, regex=True)
        )
        bonds_df = stock_df[bond_mask].copy()

        self._cache[cache_key] = bonds_df
        self._cache_time[cache_key] = datetime.utcnow()
        logger.info(f"Found {len(bonds_df)} convertible bonds")
        return bonds_df

    def get_k_data(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        frequency: str = "d"
    ) -> pd.DataFrame:
        """Get historical K-line data for a stock/bond.

        Args:
            code: Stock/bond code (e.g., 'sh.110001')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            frequency: Data frequency ('d', 'w', 'm', '5', '15', '30', '60')
        """
        self._ensure_login()

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)
                          ).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            code,
            "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag="3"  # No adjustment
        )

        if rs.error_code != '0':
            logger.error(f"Failed to get K-data for {code}: {rs.error_msg}")
            return pd.DataFrame()

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return pd.DataFrame()

        df = pd.DataFrame(data_list, columns=rs.fields)

        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close',
                        'preclose', 'volume', 'amount', 'turn', 'pctChg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['date'] = pd.to_datetime(df['date'])
        return df

    def get_realtime_data(self, codes: List[str]) -> pd.DataFrame:
        """Get latest data for given codes."""
        self._ensure_login()

        all_data = []
        for code in codes:
            try:
                # Get last 5 days of data and take the latest
                rs = bs.query_history_k_data_plus(
                    code,
                    "date,code,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=(datetime.now() - timedelta(days=10)
                                ).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency="d"
                )
                if rs.error_code == '0':
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                    if data_list:
                        df = pd.DataFrame(data_list, columns=rs.fields)
                        latest = df.iloc[-1].to_dict()
                        all_data.append(latest)
            except Exception as e:
                logger.warning(f"Failed to get data for {code}: {e}")

        if all_data:
            result_df = pd.DataFrame(all_data)
            numeric_cols = ['open', 'high', 'low', 'close',
                            'volume', 'amount', 'turn', 'pctChg']
            for col in numeric_cols:
                if col in result_df.columns:
                    result_df[col] = pd.to_numeric(
                        result_df[col], errors='coerce')
            return result_df
        return pd.DataFrame()

    def get_convertible_bonds_with_data(self) -> pd.DataFrame:
        """Get convertible bonds with latest market data."""
        bonds_df = self.get_convertible_bonds()
        if bonds_df.empty:
            return pd.DataFrame()

        codes = bonds_df['code'].tolist()

        # Process in batches
        batch_size = 50
        all_market_data = []

        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            batch_data = self.get_realtime_data(batch_codes)
            if not batch_data.empty:
                all_market_data.append(batch_data)

        if not all_market_data:
            return bonds_df

        market_df = pd.concat(all_market_data, ignore_index=True)
        result_df = bonds_df.merge(market_df, on='code', how='left')
        return result_df


# Singleton instance
_client: Optional[BaoStockClient] = None


def get_baostock_client() -> BaoStockClient:
    """Get the singleton BaoStock client instance."""
    global _client
    if _client is None:
        _client = BaoStockClient()
    return _client
