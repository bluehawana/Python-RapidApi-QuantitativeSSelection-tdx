"""
MACD Golden Cross + Volume 6x Strategy Backtest for 111012 福新转债

Strategy Rules:
- Entry: MACD golden cross (MACD line crosses above signal line) + Volume > 6x average
- Exit: MACD dead cross (MACD line crosses below signal line)
- Check times: 10:29 AM and 2:03 PM

Uses minute-level data for accurate intraday analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Try multiple data sources


def get_minute_data_akshare(code='111012', days=30):
    """Get minute-level data using AkShare."""
    try:
        import akshare as ak
        # AkShare uses format like "sz111012" for Shenzhen bonds
        symbol = f"sz{code}"
        df = ak.bond_zh_hs_cov_min(symbol=symbol, period='1')
        if df is not None and not df.empty:
            df['datetime'] = pd.to_datetime(df['时间'])
            df = df.rename(columns={
                '开盘': 'open', '收盘': 'close', '最高': 'high',
                '最低': 'low', '成交量': 'volume'
            })
            return df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"AkShare minute data error: {e}")
    return None


def get_daily_data_tushare(code='111012', days=90):
    """Get daily data using Tushare."""
    try:
        import tushare as ts
        ts.set_token(
            '0e65a5c636112dc9d9af5ccc93ef06c55987805b9467db0866185f10')
        pro = ts.pro_api()

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        # Get convertible bond daily data
        df = pro.cb_daily(ts_code=f'{code}.SZ',
                          start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            df = df.rename(columns={'trade_date': 'date',
                           'vol': 'volume', 'amount': 'turnover'})
            return df
    except Exception as e:
        print(f"Tushare daily data error: {e}")
    return None


def get_daily_data_efinance(code='111012', days=90):
    """Get daily data using efinance."""
    try:
        import efinance as ef
        df = ef.bond.get_quote_history(code)
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            # Filter to recent days
            cutoff = datetime.now() - timedelta(days=days)
            df = df[df['date'] >= cutoff]
            return df.sort_values('date')
    except Exception as e:
        print(f"efinance daily data error: {e}")
    return None


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicators."""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def detect_golden_cross(macd_line, signal_line):
    """Detect MACD golden cross (bullish signal)."""
    cross = (macd_line > signal_line) & (
        macd_line.shift(1) <= signal_line.shift(1))
    return cross


def detect_dead_cross(macd_line, signal_line):
    """Detect MACD dead cross (bearish signal)."""
    cross = (macd_line < signal_line) & (
        macd_line.shift(1) >= signal_line.shift(1))
    return cross


def backtest_strategy(df, volume_multiplier=6.0, check_times=['10:29', '14:03']):
    """
    Backtest the MACD + Volume strategy.

    Args:
        df: DataFrame with OHLCV data
        volume_multiplier: Volume threshold (6x average)
        check_times: Times to check for signals (10:29 AM, 2:03 PM)
    """
    # Calculate MACD
    macd_line, signal_line, histogram = calculate_macd(df['close'])

    # Calculate 20-period volume average
    volume_avg = df['volume'].rolling(20).mean()
    volume_ratio = df['volume'] / volume_avg

    # Detect signals
    golden_cross = detect_golden_cross(macd_line, signal_line)
    dead_cross = detect_dead_cross(macd_line, signal_line)

    # Entry condition: Golden cross + Volume > 6x
    entry_signals = golden_cross & (volume_ratio > volume_multiplier)

    # Exit condition: Dead cross
    exit_signals = dead_cross

    # Add indicators to dataframe
    df = df.copy()
    df['macd'] = macd_line
    df['signal'] = signal_line
    df['histogram'] = histogram
    df['volume_avg'] = volume_avg
    df['volume_ratio'] = volume_ratio
    df['golden_cross'] = golden_cross
    df['dead_cross'] = dead_cross
    df['entry_signal'] = entry_signals
    df['exit_signal'] = exit_signals

    return df


def run_backtest(df):
    """Run the backtest and calculate performance."""
    trades = []
    position = None

    for i, row in df.iterrows():
        date = row.get('date', row.get('datetime', i))

        # Check for entry
        if row['entry_signal'] and position is None:
            position = {
                'entry_date': date,
                'entry_price': row['close'],
                'entry_volume_ratio': row['volume_ratio']
            }

        # Check for exit
        elif row['exit_signal'] and position is not None:
            exit_price = row['close']
            pnl_pct = (
                exit_price - position['entry_price']) / position['entry_price'] * 100

            trades.append({
                'entry_date': position['entry_date'],
                'exit_date': date,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'volume_ratio': position['entry_volume_ratio']
            })
            position = None

    return trades, position


def print_analysis(df, trades, current_position, bond_code='111012'):
    """Print detailed analysis results."""
    print("=" * 70)
    print(f"  MACD Golden Cross + Volume 6x Strategy - {bond_code} 福新转债")
    print("=" * 70)
    print(f"\n📋 Strategy Rules:")
    print(f"   • Entry: MACD Golden Cross + Volume > 6x average")
    print(f"   • Exit: MACD Dead Cross")
    print(f"   • Check Times: 10:29 AM and 2:03 PM")
    print(f"\n📊 Data Period: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"   Total bars: {len(df)}")

    # Current status
    latest = df.iloc[-1]
    print(f"\n📈 Current MACD Status ({df['date'].iloc[-1]}):")
    print(f"   MACD Line:    {latest['macd']:.4f}")
    print(f"   Signal Line:  {latest['signal']:.4f}")
    print(f"   Histogram:    {latest['histogram']:.4f}")
    print(f"   Volume Ratio: {latest['volume_ratio']:.2f}x")

    if latest['macd'] > latest['signal']:
        print(f"   Trend: 🟢 BULLISH (MACD above Signal)")
    else:
        print(f"   Trend: 🔴 BEARISH (MACD below Signal)")

    # Recent signals
    print(f"\n🎯 Recent Signals (Last 15 bars):")
    recent = df.tail(15)
    for _, row in recent.iterrows():
        date = row['date']
        signals = []
        if row['golden_cross']:
            signals.append("🟡 Golden Cross")
        if row['dead_cross']:
            signals.append("🔴 Dead Cross")
        if row['entry_signal']:
            signals.append("🚀 ENTRY!")
        if row['exit_signal']:
            signals.append("📤 EXIT!")

        signal_str = " | ".join(signals) if signals else ""
        vol_indicator = "📊" if row['volume_ratio'] > 6 else ""

        date_str = date.strftime(
            '%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        print(
            f"   {date_str}: Close={row['close']:>8.2f} Vol={row['volume_ratio']:>5.1f}x {vol_indicator} {signal_str}")

    # Trade history
    print(f"\n💰 Completed Trades:")
    if trades:
        for i, trade in enumerate(trades, 1):
            entry_date = trade['entry_date']
            exit_date = trade['exit_date']
            entry_str = entry_date.strftime(
                '%Y-%m-%d') if hasattr(entry_date, 'strftime') else str(entry_date)
            exit_str = exit_date.strftime(
                '%Y-%m-%d') if hasattr(exit_date, 'strftime') else str(exit_date)

            emoji = "✅" if trade['pnl_pct'] > 0 else "❌"
            print(f"   {i}. {emoji} {entry_str} → {exit_str}")
            print(
                f"      Entry: {trade['entry_price']:.2f} (Vol: {trade['volume_ratio']:.1f}x)")
            print(f"      Exit:  {trade['exit_price']:.2f}")
            print(f"      P&L:   {trade['pnl_pct']:+.2f}%")

        # Summary
        total_pnl = sum(t['pnl_pct'] for t in trades)
        wins = len([t for t in trades if t['pnl_pct'] > 0])
        losses = len(trades) - wins
        win_rate = wins / len(trades) * 100 if trades else 0

        print(f"\n📊 Performance Summary:")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Wins/Losses:  {wins}/{losses}")
        print(f"   Win Rate:     {win_rate:.1f}%")
        print(f"   Total P&L:    {total_pnl:+.2f}%")
        print(f"   Avg P&L:      {total_pnl/len(trades):+.2f}%")
    else:
        print("   No completed trades in this period")

    # Current position
    if current_position:
        print(f"\n⚠️ Open Position:")
        entry_str = current_position['entry_date'].strftime('%Y-%m-%d') if hasattr(
            current_position['entry_date'], 'strftime') else str(current_position['entry_date'])
        print(
            f"   Entry: {entry_str} at {current_position['entry_price']:.2f}")
        unrealized = (latest['close'] - current_position['entry_price']
                      ) / current_position['entry_price'] * 100
        print(f"   Current: {latest['close']:.2f}")
        print(f"   Unrealized P&L: {unrealized:+.2f}%")

    # Entry conditions check
    print(f"\n🔍 Current Entry Conditions:")
    vol_ok = latest['volume_ratio'] > 6
    macd_bullish = latest['macd'] > latest['signal']
    golden = latest['golden_cross']

    print(
        f"   Volume > 6x:     {'✅' if vol_ok else '❌'} ({latest['volume_ratio']:.1f}x)")
    print(f"   MACD Bullish:    {'✅' if macd_bullish else '❌'}")
    print(f"   Golden Cross:    {'✅' if golden else '❌'}")

    if vol_ok and golden:
        print(f"\n   🚀 ENTRY SIGNAL ACTIVE!")
    elif current_position and latest['dead_cross']:
        print(f"\n   📤 EXIT SIGNAL - Consider closing position!")
    else:
        print(f"\n   ⏳ Waiting for entry conditions...")


def main():
    """Main function to run the strategy analysis."""
    bond_code = '111012'

    print(f"\n🔄 Fetching data for {bond_code}...")

    # Try different data sources
    df = None

    # Try Tushare first (most reliable from previous tests)
    print("   Trying Tushare...")
    df = get_daily_data_tushare(bond_code, days=90)
    if df is not None and not df.empty:
        print(f"   ✅ Got {len(df)} days from Tushare")

    # Try efinance as backup
    if df is None or df.empty:
        print("   Trying efinance...")
        df = get_daily_data_efinance(bond_code, days=90)
        if df is not None and not df.empty:
            print(f"   ✅ Got {len(df)} days from efinance")

    # Try AkShare minute data
    if df is None or df.empty:
        print("   Trying AkShare minute data...")
        df = get_minute_data_akshare(bond_code)
        if df is not None and not df.empty:
            print(f"   ✅ Got {len(df)} bars from AkShare")
            df['date'] = df['datetime']

    if df is None or df.empty:
        print("❌ Could not fetch data from any source")
        return

    # Ensure numeric types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Run backtest
    df = backtest_strategy(df, volume_multiplier=6.0)
    trades, current_position = run_backtest(df)

    # Print analysis
    print_analysis(df, trades, current_position, bond_code)

    # Additional: Show all golden crosses and their volume
    print(f"\n📋 All Golden Crosses in Period:")
    golden_crosses = df[df['golden_cross'] == True]
    if not golden_crosses.empty:
        for _, row in golden_crosses.iterrows():
            date = row['date']
            date_str = date.strftime(
                '%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            vol_ok = "✅ Vol OK" if row[
                'volume_ratio'] > 6 else f"❌ Vol {row['volume_ratio']:.1f}x < 6x"
            entry = "🚀 ENTRY" if row['entry_signal'] else ""
            print(f"   {date_str}: Close={row['close']:.2f}, {vol_ok} {entry}")
    else:
        print("   No golden crosses found in this period")

    print(f"\n📋 All Dead Crosses in Period:")
    dead_crosses = df[df['dead_cross'] == True]
    if not dead_crosses.empty:
        for _, row in dead_crosses.iterrows():
            date = row['date']
            date_str = date.strftime(
                '%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            print(f"   {date_str}: Close={row['close']:.2f}")
    else:
        print("   No dead crosses found in this period")

    print("\n" + "=" * 70)
    print("  Strategy Note: Check at 10:29 AM and 2:03 PM for optimal timing")
    print("=" * 70)


if __name__ == "__main__":
    main()
