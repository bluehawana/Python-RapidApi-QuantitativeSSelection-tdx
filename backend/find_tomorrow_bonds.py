"""
Find potential bonds for tomorrow's T+0 trading.

Strategy: MACD golden cross + high volume entry, dead cross exit
- Flexible timing based on each bond's pattern
- Analyze today's signals to predict tomorrow's behavior
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD."""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def get_top_gainers():
    """Get top 10 convertible bond gainers today."""
    try:
        import efinance as ef
        df = ef.bond.get_realtime_quotes()

        if df is None or df.empty:
            return None

        df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
        df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce')
        df = df[df['涨跌幅'].notna()]
        df = df.sort_values('涨跌幅', ascending=False)

        return df.head(10)

    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_bond_signals(code):
    """Analyze a bond's intraday signals - find best entry/exit times."""
    try:
        import efinance as ef

        df = ef.bond.get_quote_history(code, klt=1)

        if df is None or df.empty:
            return None

        df['datetime'] = pd.to_datetime(df['日期'])
        df['time'] = df['datetime'].dt.strftime('%H:%M')
        df['close'] = pd.to_numeric(df['收盘'], errors='coerce')
        df['volume'] = pd.to_numeric(df['成交量'], errors='coerce')

        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(df['close'])
        df['macd'] = macd_line
        df['signal'] = signal_line
        df['histogram'] = histogram

        # Volume ratio
        volume_avg = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / volume_avg

        # Detect golden crosses and dead crosses
        df['golden_cross'] = (df['macd'] > df['signal']) & (
            df['macd'].shift(1) <= df['signal'].shift(1))
        df['dead_cross'] = (df['macd'] < df['signal']) & (
            df['macd'].shift(1) >= df['signal'].shift(1))

        # Find all golden crosses with their volume
        golden_crosses = df[df['golden_cross'] == True].copy()
        dead_crosses = df[df['dead_cross'] == True].copy()

        # Find best entry signals (golden cross + high volume)
        best_entries = []
        for idx, row in golden_crosses.iterrows():
            vol = row['volume_ratio'] if not pd.isna(
                row['volume_ratio']) else 0
            best_entries.append({
                'time': row['time'],
                'price': row['close'],
                'volume_ratio': vol
            })

        # Find exit signals
        exits = []
        for idx, row in dead_crosses.iterrows():
            exits.append({
                'time': row['time'],
                'price': row['close']
            })

        # Simulate trades: entry on golden cross with vol > 2x, exit on next dead cross
        trades = []
        position = None

        for idx, row in df.iterrows():
            vol = row['volume_ratio'] if not pd.isna(
                row['volume_ratio']) else 0

            if position is None and row['golden_cross'] and vol > 2:
                position = {'time': row['time'],
                            'price': row['close'], 'vol': vol}
            elif position is not None and row['dead_cross']:
                pnl = (row['close'] - position['price']) / \
                    position['price'] * 100
                trades.append({
                    'entry_time': position['time'],
                    'exit_time': row['time'],
                    'entry_price': position['price'],
                    'exit_price': row['close'],
                    'pnl': pnl,
                    'entry_vol': position['vol']
                })
                position = None

        # Close at end if still holding
        if position:
            last = df.iloc[-1]
            pnl = (last['close'] - position['price']) / position['price'] * 100
            trades.append({
                'entry_time': position['time'],
                'exit_time': last['time'],
                'entry_price': position['price'],
                'exit_price': last['close'],
                'pnl': pnl,
                'entry_vol': position['vol'],
                'note': 'EOD'
            })

        # Current status
        latest = df.iloc[-1]

        return {
            'close': latest['close'],
            'macd': latest['macd'],
            'signal': latest['signal'],
            'histogram': latest['histogram'],
            'macd_bullish': latest['macd'] > latest['signal'],
            'golden_crosses': best_entries,
            'dead_crosses': exits,
            'trades': trades,
            'total_pnl': sum(t['pnl'] for t in trades) if trades else 0,
            'num_trades': len(trades)
        }

    except Exception as e:
        return None


def main():
    print("=" * 85)
    print("  T+0 Bond Scanner - Finding Tomorrow's Opportunities")
    print("=" * 85)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\n📋 Strategy: MACD Golden Cross + High Volume Entry → Dead Cross Exit")
    print("   (Flexible timing based on each bond's pattern)")

    print("\n🔄 Getting top 10 gainers...")
    top_gainers = get_top_gainers()

    if top_gainers is None:
        print("❌ No data")
        return

    print(f"   ✅ Got {len(top_gainers)} bonds\n")

    results = []

    for idx, row in top_gainers.iterrows():
        code = row['债券代码']
        name = row['债券名称']
        change = row['涨跌幅']

        print(f"   Analyzing {code} {name}...", end=" ")

        data = analyze_bond_signals(code)

        if data:
            results.append({
                'code': code,
                'name': name,
                'change': change,
                **data
            })
            status = "🟢" if data['macd_bullish'] else "🔴"
            print(
                f"{status} {data['num_trades']} trades, {data['total_pnl']:+.2f}%")
        else:
            print("❌")

    if not results:
        print("\n❌ No results")
        return

    # Sort by today's simulated P&L
    df = pd.DataFrame(results)
    df = df.sort_values('total_pnl', ascending=False)

    print("\n" + "=" * 85)
    print("  TODAY'S T+0 SIMULATION RESULTS")
    print("=" * 85)

    print(f"\n{'Code':<8} {'Name':<10} {'Change':>8} {'Trades':>7} {'T+0 P&L':>10} {'MACD':>8} {'Status'}")
    print("-" * 85)

    for _, row in df.iterrows():
        status = "🟢 Bull" if row['macd_bullish'] else "🔴 Bear"
        print(f"{row['code']:<8} {row['name']:<10} {row['change']:>7.2f}% {row['num_trades']:>7} {row['total_pnl']:>9.2f}% {row['macd']:>8.3f} {status}")

    # Detailed analysis for top picks
    print("\n" + "=" * 85)
    print("  🎯 DETAILED ANALYSIS - TOP PICKS FOR TOMORROW")
    print("=" * 85)

    for _, row in df.head(5).iterrows():
        print(f"\n{'─' * 85}")
        print(f"📈 {row['code']} {row['name']} | Today: {row['change']:+.2f}%")
        print(f"{'─' * 85}")

        print(f"\n   Current Status:")
        print(f"   • Price: {row['close']:.2f}")
        print(f"   • MACD: {row['macd']:.4f} | Signal: {row['signal']:.4f}")
        print(f"   • Histogram: {row['histogram']:.4f}")
        print(
            f"   • Trend: {'🟢 BULLISH' if row['macd_bullish'] else '🔴 BEARISH'}")

        if row['golden_crosses']:
            print(f"\n   🟡 Golden Crosses Today:")
            for gc in row['golden_crosses'][:5]:
                vol_status = "📊" if gc['volume_ratio'] > 3 else ""
                print(
                    f"      {gc['time']}: {gc['price']:.2f} (Vol: {gc['volume_ratio']:.1f}x) {vol_status}")

        if row['dead_crosses']:
            print(f"\n   🔴 Dead Crosses Today:")
            for dc in row['dead_crosses'][:5]:
                print(f"      {dc['time']}: {dc['price']:.2f}")

        if row['trades']:
            print(f"\n   💰 Simulated Trades Today:")
            for i, t in enumerate(row['trades'], 1):
                emoji = "✅" if t['pnl'] > 0 else "❌"
                note = f" ({t.get('note', '')})" if t.get('note') else ""
                print(
                    f"      {i}. {t['entry_time']} → {t['exit_time']}: {t['entry_price']:.2f} → {t['exit_price']:.2f} = {t['pnl']:+.2f}% {emoji}{note}")
            print(f"      Total: {row['total_pnl']:+.2f}%")

        # Tomorrow recommendation
        print(f"\n   💡 Tomorrow Strategy:")
        if row['macd_bullish'] and row['histogram'] > 0:
            print(f"      Watch for golden cross + volume spike → Enter")
            print(f"      Exit on dead cross")
        elif row['macd_bullish']:
            print(f"      MACD bullish but histogram weak")
            print(f"      Wait for histogram to turn positive")
        else:
            print(f"      MACD bearish - wait for golden cross first")

    print("\n" + "=" * 85)
    print("  Strategy: Enter on Golden Cross + High Volume, Exit on Dead Cross")
    print("  Timing is flexible - watch for signals throughout the day!")
    print("=" * 85)


if __name__ == "__main__":
    main()
