"""AkShare client wrapper for fetching convertible bond data."""

import logging
from typing import List, Optional
from datetime import datetime
import time

import pandas as pd

logger = logging.getLogger(__name__)


class AkShareClient:
    """Client for fetching convertible bond data from AkShare."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the AkShare client.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._last_request_time = 0.0
        self._min_request_interval = 0.5  # Rate limiting: 500ms between requests

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _retry_request(self, func, *args, **kwargs):
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function

        Raises:
            Exception: If all retries fail
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        raise last_error

    def fetch_convertible_bonds(self) -> pd.DataFrame:
        """Fetch all convertible bond data from AkShare.

        Returns:
            DataFrame with convertible bond data

        Raises:
            Exception: If data fetch fails after retries
        """
        try:
            import akshare as ak

            # Fetch convertible bond data
            df = self._retry_request(ak.bond_cb_jsl)

            logger.info(f"Fetched {len(df)} convertible bonds from AkShare")
            return df

        except ImportError:
            logger.error(
                "AkShare is not installed. Please install it with: pip install akshare")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch convertible bond data: {e}")
            raise

    def fetch_bond_detail(self, bond_code: str) -> Optional[dict]:
        """Fetch detailed information for a specific bond.

        Args:
            bond_code: The bond code

        Returns:
            Dictionary with bond details or None if not found
        """
        try:
            import akshare as ak

            # This is a placeholder - actual implementation depends on AkShare API
            # For now, we'll get the bond from the full list
            df = self.fetch_convertible_bonds()
            bond_row = df[df['债券代码'] == bond_code]

            if bond_row.empty:
                return None

            return bond_row.iloc[0].to_dict()

        except Exception as e:
            logger.error(f"Failed to fetch bond detail for {bond_code}: {e}")
            return None


# Singleton instance
_client: Optional[AkShareClient] = None


def get_akshare_client() -> AkShareClient:
    """Get the singleton AkShare client instance."""
    global _client
    if _client is None:
        _client = AkShareClient()
    return _client
