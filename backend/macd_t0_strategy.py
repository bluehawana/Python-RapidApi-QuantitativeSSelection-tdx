"""
T+0 Intraday MACD Strategy for 111012 福新转债

Strategy Rules (Same Day Trading):
- Entry: MACD golden cross (1-min) + Volume > 6x average at 10:29 AM or 2:03 PM
- Exit: MACD dead cross (same day)
- All trades closed by end of day

Uses 1-minute K-line data for intraday analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def get_minute_data_efinance(code='111012'):
    """Get minute-level intraday data using efinance."""
    try:
        import efinance as ef
        # Get 1-minute K-line data
        df = ef.bond.get_quote_history(code, klt=1)
        if df is not None and not df.empty:
            df['datetime'] = pd.to_datetime(
                df['日期'] + ' ' + df['时间'] if '时间' in df.columns else df['日期'])
            df = df.rename(columns={
                '开盘': 'open', '收盘': 'close', '最高': 'high',
                '最低': 'low', '成交量': 'volume', '成交额': 'amount'
            })
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except Exception as e:
        print(f"efinance minute data error: {e}")
    return None


def get_minute_data_akshare(code='111012'):
    """Get minute-level data using AkShare."""
    try:
        import akshare as ak
        symbol = f"sz{code}"
        df = ak.bond_zh_hs_cov_min(symbol=symbol, period='1')
        if df is not None and not df.empty:
            df['datetime'] = pd.to_datetime(df['时间'])
            df = df.rename(columns={
                '开盘': 'open', '收盘': 'close', '最高': 'high',
                '最低': 'low', '成交量': 'volume'
            })
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except Exception as e:
        print(f"AkShare minute data error: {e}")
    return None


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD on minute data."""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def detect_golden_cross(macd_line, signal_line):
    """MACD golden cross - bullish."""
    return (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))


def detect_dead_cross(macd_line, signal_line):
    """MACD dead cross - bearish."""
    return (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))


def backtest_intraday(df, target_times=['10:29', '14:03'], volume_multiplier=6.0):
    """
    T+0 Intraday backtest - entry at target times, exit on dead cross same day.

    Args:
        df: Minute-level DataFrame
        target_times: Times to check for entry (10:29 AM, 2:03 PM)
        volume_multiplier: Volume threshold (6x average)
    """
    # Calculate MACD on minute data
    macd_line, signal_line, histogram = calculate_macd(df['close'])

    # 20-bar volume average (20 minutes)
    volume_avg = df['volume'].rolling(20).mean()
    volume_ratio = df['volume'] / volume_avg

    # Signals
    golden_cross = detect_golden_cross(macd_line, signal_line)
    dead_cross = detect_dead_cross(macd_line, signal_line)

    df = df.copy()
    df['macd'] = macd_line
    df['signal'] = signal_line
    df['histogram'] = histogram
    df['volume_avg'] = volume_avg
    df['volume_ratio'] = volume_ratio
    df['golden_cross'] = golden_cross
    df['dead_cross'] = dead_cross
    df['time'] = df['datetime'].dt.strftime('%H:%M')
    df['date'] = df['datetime'].dt.date

    return df


def run_t0_backtest(df, target_times=['10:29', '14:03'], volume_multiplier=6.0):
    """
    Run T+0 backtest across multiple days.

    Strategy:
    - At 10:29 or 14:03, check if golden cross occurred AND volume > 6x
    - If entry, hold until dead cross OR end of day
    """
    trades = []

    # Group by date for daily analysis
    for date, day_data in df.groupby('date'):
        day_data = day_data.sort_values('datetime')
        position = None

        for idx, row in day_data.iterrows():
            current_time = row['time']

            # Check for entry at target times
            if position is None:
                # Check if we're at or near target time (within 1 minute)
                for target in target_times:
                    if current_time == target or (
                        abs(int(current_time.replace(':', '')) -
                            int(target.replace(':', ''))) <= 1
                    ):
                        # Check entry conditions: recent golden cross + volume > 6x
                        # Look back 5 minutes for golden cross
                        lookback_start = max(
                            0, day_data.index.get_loc(idx) - 5)
                        lookback_data = day_data.iloc[lookback_start:day_data.index.get_loc(
                            idx)+1]

                        recent_golden = lookback_data['golden_cross'].any()
                        vol_ok = row['volume_ratio'] > volume_multiplier
                        macd_bullish = row['macd'] > row['signal']

                        if recent_golden and vol_ok and macd_bullish:
                            position = {
                                'entry_time': row['datetime'],
                                'entry_price': row['close'],
                                'entry_volume_ratio': row['volume_ratio'],
                                'trigger_time': target
                            }
                        elif macd_bullish and vol_ok:
                            # Also enter if MACD bullish + volume spike even without fresh golden cross
                            position = {
                                'entry_time': row['datetime'],
                                'entry_price': row['close'],
                                'entry_volume_ratio': row['volume_ratio'],
                                'trigger_time': target,
                                'note': 'MACD bullish + volume'
                            }

            # Check for exit: dead cross
            elif position is not None:
                if row['dead_cross']:
                    pnl = (row['close'] - position['entry_price']) / \
                        position['entry_price'] * 100
                    trades.append({
                        'date': date,
                        'entry_time': position['entry_time'],
                        'exit_time': row['datetime'],
                        'entry_price': position['entry_price'],
                        'exit_price': row['close'],
                        'pnl_pct': pnl,
                        'exit_reason': 'Dead Cross',
                        'trigger': position['trigger_time']
                    })
                    position = None

        # Force close at end of day if still holding
        if position is not None:
            last_row = day_data.iloc[-1]
            pnl = (last_row['close'] - position['entry_price']
                   ) / position['entry_price'] * 100
            trades.append({
                'date': date,
                'entry_time': position['entry_time'],
                'exit_time': last_row['datetime'],
                'entry_price': position['entry_price'],
                'exit_price': last_row['close'],
                'pnl_pct': pnl,
                'exit_reason': 'EOD Close',
                'trigger': position['trigger_time']
            })

    return trades


def analyze_single_day(df, date, target_times=['10:29', '14:03']):
    """Analyze a single day's minute data."""
    day_data = df[df['date'] == date].copy()
    if day_data.empty:
        return None

    print(f"\n📅 {date} Intraday Analysis:")
    print(f"   Bars: {len(day_data)} minutes")
    print(
        f"   Open: {day_data.iloc[0]['close']:.2f} → Close: {day_data.iloc[-1]['close']:.2f}")

    # Find signals at target times
    for target in target_times:
        target_data = day_data[day_data['time'] == target]
        if not target_data.empty:
            row = target_data.iloc[0]
            print(f"\n   ⏰ {target}:")
            print(f"      Price: {row['close']:.2f}")
            print(
                f"      MACD: {row['macd']:.4f} | Signal: {row['signal']:.4f}")
            print(f"      Volume Ratio: {row['volume_ratio']:.1f}x")

            # Check conditions
            macd_bullish = row['macd'] > row['signal']
            vol_ok = row['volume_ratio'] > 6

            status = []
            if macd_bullish:
                status.append("🟢 MACD Bullish")
            else:
                status.append("🔴 MACD Bearish")

            if vol_ok:
                status.append(f"📊 Vol {row['volume_ratio']:.1f}x > 6x ✅")
            else:
                status.append(f"📊 Vol {row['volume_ratio']:.1f}x < 6x ❌")

            print(f"      {' | '.join(status)}")

            if macd_bullish and vol_ok:
                print(f"      🚀 ENTRY SIGNAL!")

    # Show all golden/dead crosses for the day
    golden = day_data[day_data['golden_cross'] == True]
    dead = day_data[day_data['dead_cross'] == True]

    if not golden.empty:
        print(f"\n   🟡 Golden Crosses:")
        for _, row in golden.iterrows():
            print(
                f"      {row['time']}: {row['close']:.2f} (Vol: {row['volume_ratio']:.1f}x)")

    if not dead.empty:
        print(f"\n   🔴 Dead Crosses:")
        for _, row in dead.iterrows():
            print(f"      {row['time']}: {row['close']:.2f}")


def print_backtest_results(trades):
    """Print T+0 backtest results."""
    print("\n" + "=" * 70)
    print("  T+0 BACKTEST RESULTS")
    print("=" * 70)

    if not trades:
        print("\n   No trades executed in the period")
        return

    print(f"\n💰 Trade History ({len(trades)} trades):")
    for i, t in enumerate(trades, 1):
        emoji = "✅" if t['pnl_pct'] > 0 else "❌"
        entry_str = t['entry_time'].strftime('%m-%d %H:%M')
        exit_str = t['exit_time'].strftime('%H:%M')
        print(f"\n   {i}. {emoji} {entry_str} → {exit_str}")
        print(f"      Trigger: {t['trigger']} | Exit: {t['exit_reason']}")
        print(
            f"      Entry: {t['entry_price']:.2f} → Exit: {t['exit_price']:.2f}")
        print(f"      P&L: {t['pnl_pct']:+.2f}%")

    # Summary
    total_pnl = sum(t['pnl_pct'] for t in trades)
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    win_rate = len(wins) / len(trades) * 100

    avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0

    print(f"\n📊 Performance Summary:")
    print(f"   Total Trades:  {len(trades)}")
    print(f"   Wins/Losses:   {len(wins)}/{len(losses)}")
    print(f"   Win Rate:      {win_rate:.1f}%")
    print(f"   Total P&L:     {total_pnl:+.2f}%")
    print(f"   Avg Win:       {avg_win:+.2f}%")
    print(f"   Avg Loss:      {avg_loss:+.2f}%")

    # By trigger time
    print(f"\n📊 By Entry Time:")
    for trigger in ['10:29', '14:03']:
        trigger_trades = [t for t in trades if t['trigger'] == trigger]
        if trigger_trades:
            trigger_pnl = sum(t['pnl_pct'] for t in trigger_trades)
            trigger_wins = len([t for t in trigger_trades if t['pnl_pct'] > 0])
            print(
                f"   {trigger}: {len(trigger_trades)} trades, {trigger_wins} wins, {trigger_pnl:+.2f}% total")


def main():
    """Main function for T+0 strategy analysis."""
    bond_code = '111012'
    target_times = ['10:29', '14:03']
    volume_multiplier = 6.0

    print("=" * 70)
    print(f"  T+0 MACD Strategy - {bond_code} 福新转债")
    print("=" * 70)
    print(f"\n📋 Strategy Rules:")
    print(
        f"   • Entry: MACD Golden Cross + Volume > {volume_multiplier}x at {', '.join(target_times)}")
    print(f"   • Exit: MACD Dead Cross (same day)")
    print(f"   • Force close at end of day")

    print(f"\n🔄 Fetching minute data...")

    # Try efinance first
    df = get_minute_data_efinance(bond_code)
    if df is not None and not df.empty:
        print(f"   ✅ Got {len(df)} minute bars from efinance")
    else:
        # Try AkShare
        df = get_minute_data_akshare(bond_code)
        if df is not None and not df.empty:
            print(f"   ✅ Got {len(df)} minute bars from AkShare")

    if df is None or df.empty:
        print("   ❌ Could not fetch minute data")
        print("\n   Trying alternative: simulate with recent daily data...")

        # Fallback: use daily data to show concept
        try:
            import efinance as ef
            df = ef.bond.get_quote_history(bond_code)
            if df is not None and not df.empty:
                print(f"   ⚠️ Using daily data (minute data unavailable)")
                print(f"   Note: For real T+0 trading, you need real-time minute data")

                df['datetime'] = pd.to_datetime(df['日期'])
                df = df.rename(columns={
                    '开盘': 'open', '收盘': 'close', '最高': 'high',
                    '最低': 'low', '成交量': 'volume'
                })
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Show daily MACD status
                macd_line, signal_line, histogram = calculate_macd(df['close'])
                df['macd'] = macd_line
                df['signal'] = signal_line
                df['histogram'] = histogram

                latest = df.iloc[-1]
                print(
                    f"\n📈 Latest Daily MACD ({latest['datetime'].strftime('%Y-%m-%d')}):")
                print(f"   Price: {latest['close']:.2f}")
                print(f"   MACD: {latest['macd']:.4f}")
                print(f"   Signal: {latest['signal']:.4f}")
                print(
                    f"   Trend: {'🟢 BULLISH' if latest['macd'] > latest['signal'] else '🔴 BEARISH'}")

                print(f"\n⚠️ For T+0 intraday trading:")
                print(f"   1. Need real-time minute data feed")
                print(f"   2. Check MACD on 1-min chart at 10:29 and 14:03")
                print(f"   3. Enter if golden cross + volume > 6x")
                print(f"   4. Exit on dead cross same day")
        except Exception as e:
            print(f"   Error: {e}")
        return

    # Process minute data
    df = backtest_intraday(df, target_times, volume_multiplier)

    # Get unique dates
    dates = sorted(df['date'].unique())
    print(f"\n📅 Data covers {len(dates)} trading days")
    print(f"   From: {dates[0]} to {dates[-1]}")

    # Analyze recent days
    print("\n" + "=" * 70)
    print("  RECENT DAYS ANALYSIS")
    print("=" * 70)

    for date in dates[-5:]:  # Last 5 days
        analyze_single_day(df, date, target_times)

    # Run backtest
    trades = run_t0_backtest(df, target_times, volume_multiplier)
    print_backtest_results(trades)

    print("\n" + "=" * 70)
    print("  T+0 Strategy Ready - Monitor at 10:29 AM and 2:03 PM")
    print("=" * 70)


if __name__ == "__main__":
    main()
