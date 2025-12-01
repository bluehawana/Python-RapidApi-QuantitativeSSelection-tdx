"""
Unified T+0 Bond Scanner
Combines: MACD status + actual T+0 trade simulation
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig


def analyze_bond(code, name=""):
    try:
        import efinance as ef
        df = ef.bond.get_quote_history(code, klt=1)

        if df is None or df.empty:
            return None

        df['datetime'] = pd.to_datetime(df['日期'])
        df['time'] = df['datetime'].dt.strftime('%H:%M')
        df['close'] = pd.to_numeric(df['收盘'], errors='coerce')
        df['volume'] = pd.to_numeric(df['成交量'], errors='coerce')

        macd, sig, hist = calculate_macd(df['close'])
        df['macd'], df['signal'], df['hist'] = macd, sig, hist

        vol_avg = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / vol_avg

        df['golden'] = (df['macd'] > df['signal']) & (
            df['macd'].shift(1) <= df['signal'].shift(1))
        df['dead'] = (df['macd'] < df['signal']) & (
            df['macd'].shift(1) >= df['signal'].shift(1))

        # Simulate T+0 trades
        trades = []
        pos = None
        for _, row in df.iterrows():
            vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0
            if pos is None and row['golden'] and vol > 2:
                pos = {'time': row['time'], 'price': row['close'], 'vol': vol}
            elif pos and row['dead']:
                pnl = (row['close'] - pos['price']) / pos['price'] * 100
                trades.append(
                    {'entry': pos['time'], 'exit': row['time'], 'pnl': pnl})
                pos = None
        if pos:
            last = df.iloc[-1]
            pnl = (last['close'] - pos['price']) / pos['price'] * 100
            trades.append({'entry': pos['time'], 'exit': 'EOD', 'pnl': pnl})

        latest = df.iloc[-1]
        first = df.iloc[0]
        day_change = (latest['close'] - first['close']) / first['close'] * 100

        # Histogram trend (last 5 bars)
        hist_trend = hist.iloc[-5:].diff().mean() if len(hist) >= 5 else 0

        return {
            'code': code,
            'name': name or df.iloc[0]['债券名称'],
            'price': latest['close'],
            'day_change': day_change,
            'macd': latest['macd'],
            'signal': latest['signal'],
            'hist': latest['hist'],
            'hist_trend': hist_trend,
            'bullish': latest['macd'] > latest['signal'],
            't0_pnl': sum(t['pnl'] for t in trades),
            'num_trades': len(trades),
            'trades': trades
        }
    except Exception as e:
        return None


def main():
    bonds = [
        ('113672', '福蓉转债'), ('111012', '福新转债'), ('123207', '冠中转债'),
        ('123245', '集智转债'), ('113677', '华懋转债'), ('123211', '阳谷转债'),
        ('127082', '亚科转债'), ('113691', '和邦转债'), ('118043', '福立转债'),
        ('113639', '华正转债'),
    ]

    print("=" * 85)
    print("  UNIFIED T+0 SCANNER - Tomorrow's Picks")
    print("=" * 85)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    results = []
    print("\n🔄 Analyzing...\n")

    for code, name in bonds:
        data = analyze_bond(code, name)
        if data:
            results.append(data)
            print(
                f"   {code} {name}: Day {data['day_change']:+.1f}%, T+0 {data['t0_pnl']:+.2f}%, {'🟢' if data['bullish'] else '🔴'}")

    # Calculate unified score
    for r in results:
        score = 0
        # MACD bullish at close: +2
        if r['bullish']:
            score += 2
        # Histogram positive: +1
        if r['hist'] > 0:
            score += 1
        # Histogram trending up: +1
        if r['hist_trend'] > 0:
            score += 1
        # Positive T+0 P&L: +2
        if r['t0_pnl'] > 0:
            score += 2
        # Multiple profitable trades: +1
        if r['num_trades'] >= 2 and r['t0_pnl'] > 0:
            score += 1
        r['score'] = score

    # Sort by unified score
    results.sort(key=lambda x: (x['score'], x['t0_pnl']), reverse=True)

    print("\n" + "=" * 85)
    print("  UNIFIED RANKING (MACD Status + T+0 Performance)")
    print("=" * 85)

    print(f"\n{'Rank':<5} {'Code':<8} {'Name':<8} {'Day%':>7} {'T+0%':>7} {'MACD':>6} {'Hist↑':>6} {'Score':>6}")
    print("-" * 85)

    for i, r in enumerate(results, 1):
        macd_icon = "🟢" if r['bullish'] else "🔴"
        trend_icon = "↑" if r['hist_trend'] > 0 else "↓"
        stars = "⭐" * min(r['score'], 5)
        print(f"{i:<5} {r['code']:<8} {r['name']:<8} {r['day_change']:>6.1f}% {r['t0_pnl']:>6.2f}% {macd_icon:<6} {trend_icon:<6} {r['score']}/7 {stars}")

    # Top picks
    print("\n" + "=" * 85)
    print("  🎯 TOP PICKS FOR TOMORROW")
    print("=" * 85)

    for r in results[:3]:
        print(
            f"\n📈 {r['code']} {r['name']} | Score: {r['score']}/7 {'⭐' * r['score']}")
        print(
            f"   Day: {r['day_change']:+.2f}% | T+0 Sim: {r['t0_pnl']:+.2f}% ({r['num_trades']} trades)")
        print(
            f"   MACD: {'🟢 Bullish' if r['bullish'] else '🔴 Bearish'} | Histogram: {'↑ Up' if r['hist_trend'] > 0 else '↓ Down'}")

        if r['trades']:
            print(f"   Best trades today:")
            for t in sorted(r['trades'], key=lambda x: x['pnl'], reverse=True)[:2]:
                emoji = "✅" if t['pnl'] > 0 else "❌"
                print(
                    f"      {t['entry']} → {t['exit']}: {t['pnl']:+.2f}% {emoji}")

        # Recommendation
        if r['bullish'] and r['hist_trend'] > 0 and r['t0_pnl'] > 0:
            print(f"   💡 STRONG: MACD bullish + trending up + profitable T+0")
        elif r['t0_pnl'] > 0:
            print(f"   💡 GOOD: Profitable T+0 pattern, watch for golden cross")
        elif r['bullish']:
            print(f"   💡 WATCH: MACD bullish but T+0 was weak today")
        else:
            print(f"   💡 WAIT: Need golden cross signal")

    print("\n" + "=" * 85)
    print("  Strategy: Golden Cross + Volume > 2x → Enter, Dead Cross → Exit")
    print("=" * 85)


if __name__ == "__main__":
    main()
