"""QStock client for fetching convertible bond data from East Money.

This module provides a standalone implementation based on qstock library
to fetch convertible bond market data without requiring the full qstock package.
"""

import json
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests
import pandas as pd
from jsonpath import jsonpath

logger = logging.getLogger(__name__)

# Request headers for East Money API
REQUEST_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2'
}

# Market number mapping
MARKET_NUM_DICT = {
    '0': '深A',
    '1': '沪A',
    '105': '美股',
    '106': '美股',
    '107': '美股',
    '116': '港股',
    '128': '港股',
    '90': '板块'
}

# Trade detail field mapping
TRADE_DETAIL_DICT = {
    'f12': '代码',
    'f14': '名称',
    'f3': '涨幅',
    'f2': '最新',
    'f15': '最高',
    'f16': '最低',
    'f17': '今开',
    'f8': '换手率',
    'f10': '量比',
    'f9': '市盈率',
    'f5': '成交量',
    'f6': '成交额',
    'f18': '昨收',
    'f20': '总市值',
    'f21': '流通市值',
    'f13': '编号',
    'f124': '更新时间戳',
}


# Bond info field mapping
BOND_INFO_FIELD = {
    'SECURITY_CODE': '债券代码',
    'SECURITY_NAME_ABBR': '债券名称',
    'CONVERT_STOCK_CODE': '正股代码',
    'SECURITY_SHORT_NAME': '正股名称',
    'RATING': '债券评级',
    'PUBLIC_START_DATE': '申购日期',
    'ACTUAL_ISSUE_SCALE': '发行规模(亿)',
    'ONLINE_GENERAL_LWR': '网上发行中签率(%)',
    'LISTING_DATE': '上市日期',
    'EXPIRE_DATE': '到期日期',
    'BOND_EXPIRE': '期限(年)',
    'INTEREST_RATE_EXPLAIN': '利率说明'
}


class QStockClient:
    """Client for fetching stock and bond data from East Money."""

    def __init__(self):
        """Initialize the QStock client."""
        self.session = requests.Session()
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid."""
        if key not in self._cache or key not in self._cache_time:
            return False
        elapsed = (datetime.utcnow() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def _trans_num(self, df: pd.DataFrame, ignore_cols: List[str]) -> pd.DataFrame:
        """Convert columns to numeric, ignoring specified columns."""
        trans_cols = list(set(df.columns) - set(ignore_cols))
        df[trans_cols] = df[trans_cols].apply(
            lambda s: pd.to_numeric(s, errors='coerce')
        )
        return df

    def get_code_id(self, code: str) -> Optional[str]:
        """Get East Money code ID for a given stock/bond code."""
        code_id_dict = {
            '上证综指': '1.000001', 'sh': '1.000001', '上证指数': '1.000001',
            '深证综指': '0.399106', 'sz': '0.399106', '深证指数': '0.399106',
            '创业板指': '0.399006', 'cyb': '0.399006',
            '沪深300': '1.000300', 'hs300': '1.000300',
        }

        if code in code_id_dict:
            return code_id_dict[code]

        url = 'https://searchapi.eastmoney.com/api/suggest/get'
        params = {'input': code, 'type': '14',
                  'token': 'D43BF722C8E33BDC906FB84D85E326E8'}

        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            code_dict = data.get('QuotationCodeTable', {}).get('Data', [])
            if code_dict:
                return code_dict[0].get('QuoteID')
        except Exception as e:
            logger.warning(f"Failed to get code ID for {code}: {e}")
        return None

    def realtime_data(self, market: str = '可转债') -> pd.DataFrame:
        """Get realtime market data for convertible bonds."""
        cache_key = f"realtime_{market}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        market_dict = {
            '沪深A': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
            '可转债': 'b:MK0354',
            'bond': 'b:MK0354',
            '债券': 'b:MK0354',
            'ETF': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
        }

        fs = market_dict.get(market, market_dict['可转债'])
        fields = ",".join(TRADE_DETAIL_DICT.keys())

        df_total = pd.DataFrame()
        page_number = 1
        page_size = 200

        max_retries = 3
        while True:
            params = {
                'pn': str(page_number), 'pz': str(page_size), 'po': '1',
                'np': '1', 'fltt': '2', 'invt': '2', 'fid': 'f3',
                'fs': fs, 'fields': fields
            }
            url = 'http://push2.eastmoney.com/api/qt/clist/get'

            success = False
            for retry in range(max_retries):
                try:
                    time.sleep(0.5 + retry * 0.3)
                    response = self.session.get(
                        url, headers=REQUEST_HEADER, params=params, timeout=15)
                    json_response = response.json()

                    if not json_response.get('data', {}).get('diff'):
                        break

                    df_current = pd.DataFrame(json_response['data']['diff'])
                    df_total = pd.concat(
                        [df_total, df_current], ignore_index=True)
                    page_number += 1
                    success = True
                    break
                except Exception as e:
                    logger.warning(
                        f"Error fetching page {page_number} (retry {retry+1}): {e}")
                    self.session = requests.Session()

            if not success:
                break

        if df_total.empty:
            return pd.DataFrame(columns=TRADE_DETAIL_DICT.values())

        df_total = df_total.rename(columns=TRADE_DETAIL_DICT)
        df_total = df_total[list(TRADE_DETAIL_DICT.values())]

        df_total['市场'] = df_total['编号'].astype(str).apply(
            lambda x: MARKET_NUM_DICT.get(x, '未知'))
        df_total['时间'] = df_total['更新时间戳'].apply(
            lambda x: str(datetime.fromtimestamp(x)) if x else '')

        del df_total['更新时间戳']
        del df_total['编号']

        ignore_cols = ['代码', '名称', '时间', '市场']
        df_total = self._trans_num(df_total, ignore_cols)

        self._cache[cache_key] = df_total
        self._cache_time[cache_key] = datetime.utcnow()

        return df_total

    def realtime_data(self, market: str = '可转债') -> pd.DataFrame:
        """Get realtime market data for convertible bonds.

        Args:
            market: Market type, default '可转债' (convertible bonds)

        Returns:
            DataFrame with realtime bond data
        """
        cache_key = f"realtime_{market}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Market code mapping
        market_dict = {
            '沪深A': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
            '可转债': 'b:MK0354',
            'bond': 'b:MK0354',
            '债券': 'b:MK0354',
            'ETF': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
        }

        fs = market_dict.get(market, market_dict['可转债'])
        fields = ",".join(TRADE_DETAIL_DICT.keys())

        df_total = pd.DataFrame()
        page_number = 1
        page_size = 200

        while True:
            params = {
                'pn': str(page_number),
                'pz': str(page_size),
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': fs,
                'fields': fields
            }

            url = 'http://push2.eastmoney.com/api/qt/clist/get'

            try:
                time.sleep(0.3)
                response = self.session.get(
                    url, headers=REQUEST_HEADER, params=params, timeout=15)
                json_response = response.json()

                if not json_response.get('data', {}).get('diff'):
                    break

                df_current = pd.DataFrame(json_response['data']['diff'])
                df_total = pd.concat([df_total, df_current], ignore_index=True)
                page_number += 1

            except Exception as e:
                logger.warning(f"Error fetching page {page_number}: {e}")
                break

        if df_total.empty:
            return pd.DataFrame(columns=TRADE_DETAIL_DICT.values())

        df_total = df_total.rename(columns=TRADE_DETAIL_DICT)
        df_total = df_total[list(TRADE_DETAIL_DICT.values())]

        df_total['市场'] = df_total['编号'].astype(str).apply(
            lambda x: MARKET_NUM_DICT.get(x, '未知'))
        df_total['时间'] = df_total['更新时间戳'].apply(
            lambda x: str(datetime.fromtimestamp(x)) if x else '')

        del df_total['更新时间戳']
        del df_total['编号']

        ignore_cols = ['代码', '名称', '时间', '市场']
        df_total = self._trans_num(df_total, ignore_cols)

        self._cache[cache_key] = df_total
        self._cache_time[cache_key] = datetime.utcnow()

        return df_total

    def bond_info_all(self) -> pd.DataFrame:
        """Get all convertible bond basic information."""
        cache_key = "bond_info_all"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        page = 1
        dfs = []

        while True:
            params = {
                'sortColumns': 'PUBLIC_START_DATE',
                'sortTypes': '-1',
                'pageSize': '500',
                'pageNumber': str(page),
                'reportName': 'RPT_BOND_CB_LIST',
                'columns': 'ALL',
                'source': 'WEB',
                'client': 'WEB',
            }

            url = 'http://datacenter-web.eastmoney.com/api/data/v1/get'

            try:
                response = self.session.get(
                    url, headers=REQUEST_HEADER, params=params, timeout=15)
                json_response = response.json()

                if json_response.get('result') is None:
                    break

                data = json_response['result']['data']
                df = pd.DataFrame(data).rename(columns=BOND_INFO_FIELD)
                df = df[list(BOND_INFO_FIELD.values())]
                dfs.append(df)
                page += 1

            except Exception as e:
                logger.warning(f"Error fetching bond info page {page}: {e}")
                break

        if not dfs:
            return pd.DataFrame(columns=BOND_INFO_FIELD.values())

        df = pd.concat(dfs, ignore_index=True)
        self._cache[cache_key] = df
        self._cache_time[cache_key] = datetime.utcnow()

        return df

    def get_data(self, code: str, start: str = '19000101', end: Optional[str] = None,
                 freq: str = 'd', fqt: int = 1) -> pd.DataFrame:
        """Get historical K-line data for a stock/bond."""
        if end is None:
            end = datetime.now().strftime('%Y%m%d')

        start = start.replace('-', '')
        end = end.replace('-', '')

        freq_map = {'d': 101, 'w': 102, 'm': 103}
        if isinstance(freq, str):
            freq = freq_map.get(freq.lower(), 101)

        kline_field = {
            'f51': '日期', 'f52': '开盘', 'f53': '收盘', 'f54': '最高',
            'f55': '最低', 'f56': '成交量', 'f57': '成交额', 'f58': '振幅',
            'f59': '涨跌幅', 'f60': '涨跌额', 'f61': '换手率'
        }

        fields2 = ",".join(kline_field.keys())
        code_id = self.get_code_id(code)
        if not code_id:
            return pd.DataFrame()

        params = {
            'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
            'fields2': fields2,
            'beg': start, 'end': end, 'rtntype': '6',
            'secid': code_id, 'klt': str(freq), 'fqt': str(fqt),
        }

        url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'

        try:
            response = self.session.get(
                url, headers=REQUEST_HEADER, params=params, timeout=15)
            json_response = response.json()

            klines = jsonpath(json_response, '$..klines[:]')
            if not klines:
                return pd.DataFrame()

            rows = [k.split(',') for k in klines]
            name = json_response['data']['name']
            code_str = code_id.split('.')[-1]

            df = pd.DataFrame(rows, columns=list(kline_field.values()))
            df.insert(0, '代码', code_str)
            df.insert(0, '名称', name)

            cols_cn = ['日期', '名称', '代码', '开盘', '最高',
                       '最低', '收盘', '成交量', '成交额', '换手率']
            cols_en = ['date', 'name', 'code', 'open', 'high',
                       'low', 'close', 'volume', 'turnover', 'turnover_rate']
            df = df.rename(columns=dict(zip(cols_cn, cols_en)))
            df.index = pd.to_datetime(df['date'])
            df = df[cols_en[1:]]
            df = self._trans_num(df, ['name', 'code'])

            return df
        except Exception as e:
            logger.error(f"Error fetching data for {code}: {e}")
            return pd.DataFrame()

    def intraday_data(self, code: str) -> pd.DataFrame:
        """Get intraday trading data for a stock/bond."""
        code_id = self.get_code_id(code)
        if not code_id:
            return pd.DataFrame()

        columns = ['名称', '代码', '时间', '昨收', '成交价', '成交量', '单数']
        params = {
            'secid': code_id,
            'fields1': 'f1,f2,f3,f4,f5',
            'fields2': 'f51,f52,f53,f54,f55',
            'pos': '-10000000'
        }

        url = 'https://push2.eastmoney.com/api/qt/stock/details/get'

        try:
            response = self.session.get(url, params=params, timeout=15)
            res = response.json()

            texts = res.get('data', {}).get('details', [])
            if not texts:
                return pd.DataFrame(columns=columns)

            rows = [txt.split(',')[:4] for txt in texts]
            df = pd.DataFrame(columns=columns, index=range(len(rows)))
            df.loc[:, '代码'] = code_id.split('.')[1]
            df.loc[:, '名称'] = res['data'].get('name', code)

            detail_df = pd.DataFrame(rows, columns=['时间', '成交价', '成交量', '单数'])
            detail_df.insert(1, '昨收', res['data'].get('prePrice', 0))
            df.loc[:, detail_df.columns] = detail_df.values

            return self._trans_num(df, ['名称', '代码', '时间'])
        except Exception as e:
            logger.error(f"Error fetching intraday data for {code}: {e}")
            return pd.DataFrame(columns=columns)

    def hist_money(self, code: str) -> pd.DataFrame:
        """Get historical money flow data for a stock/bond."""
        history_money_dict = {
            'f51': '日期', 'f52': '主力净流入', 'f53': '小单净流入', 'f54': '中单净流入',
            'f55': '大单净流入', 'f56': '超大单净流入', 'f57': '主力净流入占比',
            'f58': '小单流入净占比', 'f59': '中单流入净占比', 'f60': '大单流入净占比',
            'f61': '超大单流入净占比', 'f62': '收盘价', 'f63': '涨跌幅'
        }

        code_id = self.get_code_id(code)
        if not code_id:
            return pd.DataFrame()

        params = {
            'lmt': '100000', 'klt': '101', 'secid': code_id,
            'fields1': 'f1,f2,f3,f7',
            'fields2': ",".join(history_money_dict.keys()),
        }

        url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'

        try:
            response = self.session.get(
                url, headers=REQUEST_HEADER, params=params, timeout=15)
            res = response.json()

            data = jsonpath(res, '$..klines[:]')
            if not data:
                return pd.DataFrame()

            rows = [d.split(',') for d in data]
            name = jsonpath(res, '$..name')[0]

            df = pd.DataFrame(rows, columns=list(history_money_dict.values()))
            df.insert(0, '代码', code_id.split('.')[-1])
            df.insert(0, '名称', name)

            return self._trans_num(df, ['代码', '名称', '日期'])
        except Exception as e:
            logger.error(f"Error fetching money flow for {code}: {e}")
            return pd.DataFrame()

    def get_convertible_bonds_full(self) -> pd.DataFrame:
        """Get comprehensive convertible bond data combining realtime and basic info."""
        realtime_df = self.realtime_data('可转债')
        info_df = self.bond_info_all()

        if realtime_df.empty:
            return pd.DataFrame()

        if not info_df.empty:
            merged_df = realtime_df.merge(
                info_df, left_on='代码', right_on='债券代码', how='left')
        else:
            merged_df = realtime_df

        return merged_df


# Singleton instance
_client: Optional[QStockClient] = None


def get_qstock_client() -> QStockClient:
    """Get the singleton QStock client instance."""
    global _client
    if _client is None:
        _client = QStockClient()
    return _client
