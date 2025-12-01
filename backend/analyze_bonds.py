"""
Analyze specific bonds for T+0 trading signals.
Flexible timing - find golden cross + volume patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def analyze_bond(code, name=""):
    """Analyze a single bond's T+0 potential."""
    try:
        import efinance as ef
        df = ef.bond.get_quote_history(code, klt=1)

        if df is None or df.empty:
            return None

        df['datetime'] = pd.to_datetime(df['日期'])
        df['time'] = df['datetime'].dt.strftime('%H:%M')
        df['close'] = pd.to_numeric(df['收盘'], errors='coerce')
        df['volume'] = pd.to_numeric(df['成交量'], errors='coerce')
        df['change'] = pd.to_numeric(df['涨跌幅'], errors='coerce')

        # MACD
        macd, signal, hist = calculate_macd(df['close'])
        df['macd'] = macd
        df['signal'] = signal
        df['hist'] = hist

        # Volume ratio
        vol_avg = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / vol_avg

        # Signals
        df['golden'] = (df['macd'] > df['signal']) & (
            df['macd'].shift(1) <= df['signal'].shift(1))
        df['dead'] = (df['macd'] < df['signal']) & (
            df['macd'].shift(1) >= df['signal'].shift(1))

        # Simulate trades
        trades = []
        pos = None

        for idx, row in df.iterrows():
            vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0

            if pos is None and row['golden'] and vol > 2:
                pos = {'time': row['time'], 'price': row['close'], 'vol': vol}
            elif pos and row['dead']:
                pnl = (row['close'] - pos['price']) / pos['price'] * 100
                trades.append({
                    'entry': pos['time'], 'exit': row['time'],
                    'entry_p': pos['price'], 'exit_p': row['close'],
                    'pnl': pnl, 'vol': pos['vol']
                })
                pos = None

        if pos:
            last = df.iloc[-1]
            pnl = (last['close'] - pos['price']) / pos['price'] * 100
            trades.append({
                'entry': pos['time'], 'exit': last['time'] + ' (EOD)',
                'entry_p': pos['price'], 'exit_p': last['close'],
                'pnl': pnl, 'vol': pos['vol']
            })

        latest = df.iloc[-1]
        first = df.iloc[0]
        day_change = (latest['close'] - first['close']) / first['close'] * 100

        return {
            'code': code,
            'name': name or df.iloc[0]['债券名称'],
            'price': latest['close'],
            'day_change': day_change,
            'macd': latest['macd'],
            'signal': latest['signal'],
            'hist': latest['hist'],
            'bullish': latest['macd'] > latest['signal'],
            'trades': trades,
            'total_pnl': sum(t['pnl'] for t in trades),
            'golden_times': df[df['golden']]['time'].tolist(),
            'dead_times': df[df['dead']]['time'].tolist()
        }
    except Exception as e:
        print(f"Error analyzing {code}: {e}")
        return None


def main():
    # Top gainers from earlier analysis
    bonds = [
        ('113672', '福蓉转债'),
        ('111012', '福新转债'),
        ('123207', '冠中转债'),
        ('123245', '集智转债'),
        ('113677', '华懋转债'),
        ('123211', '阳谷转债'),
        ('127082', '亚科转债'),
        ('113691', '和邦转债'),
        ('118043', '福立转债'),
        ('113639', '华正转债'),
    ]

    print("=" * 80)
    print("  T+0 Bond Analysis - Flexible Timing Strategy")
    print("=" * 80)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\n📋 Strategy: Golden Cross + High Volume → Dead Cross Exit")

    results = []

    print("\n🔄 Analyzing bonds...\n")

    for code, name in bonds:
        print(f"   {code} {name}...", end=" ")
        data = analyze_bond(code, name)
        if data:
            results.append(data)
            icon = "🟢" if data['bullish'] else "🔴"
            print(
                f"{icon} {len(data['trades'])} trades = {data['total_pnl']:+.2f}%")
        else:
            print("❌")

    if not results:
        return

    # Sort by T+0 P&L
    results.sort(key=lambda x: x['total_pnl'], reverse=True)

    print("\n" + "=" * 80)
    print("  T+0 SIMULATION RESULTS (Sorted by P&L)")
    print("=" * 80)

    print(f"\n{'Code':<8} {'Name':<8} {'Day%':>7} {'Trades':>7} {'T+0 P&L':>9} {'MACD':>8} {'Status'}")
    print("-" * 80)

    for r in results:
        icon = "🟢" if r['bullish'] else "🔴"
        print(f"{r['code']:<8} {r['name']:<8} {r['day_change']:>6.2f}% {len(r['trades']):>7} {r['total_pnl']:>8.2f}% {r['macd']:>8.3f} {icon}")

    # Top picks detail
    print("\n" + "=" * 80)
    print("  🎯 TOP 5 DETAILED ANALYSIS")
    print("=" * 80)

    for r in results[:5]:
        print(f"\n{'─' * 80}")
        print(
            f"📈 {r['code']} {r['name']} | Day: {r['day_change']:+.2f}% | T+0: {r['total_pnl']:+.2f}%")
        print(f"{'─' * 80}")

        print(
            f"   MACD: {r['macd']:.4f} | Signal: {r['signal']:.4f} | {'🟢 BULLISH' if r['bullish'] else '🔴 BEARISH'}")

        if r['golden_times']:
            print(
                f"   🟡 Golden Cross times: {', '.join(r['golden_times'][:8])}")
        if r['dead_times']:
            print(f"   🔴 Dead Cross times: {', '.join(r['dead_times'][:8])}")

        if r['trades']:
            print(f"   💰 Trades:")
            for t in r['trades']:
                emoji = "✅" if t['pnl'] > 0 else "❌"
                print(
                    f"      {t['entry']} → {t['exit']}: {t['entry_p']:.2f} → {t['exit_p']:.2f} = {t['pnl']:+.2f}% (Vol:{t['vol']:.1f}x) {emoji}")

        # Tomorrow tip
        if r['bullish'] and r['hist'] > 0:
            print(f"   💡 Tomorrow: Strong momentum, watch for golden cross + volume")
        elif r['bullish']:
            print(f"   💡 Tomorrow: MACD bullish, wait for histogram to strengthen")
        else:
            print(f"   💡 Tomorrow: Wait for golden cross signal")

    print("\n" + "=" * 80)
    print("  Key: Enter on Golden Cross + Volume > 2x, Exit on Dead Cross")
    print("=" * 80)


if __name__ == "__main__":
    main()
