"""
T+0 Simple Strategy for 111012 福新转债

Strategy Rules:
- Entry: 10:29 AM if MACD bullish + volume high
- Exit: 14:03 PM (fixed time)
- Same day round trip
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD on minute data."""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def main():
    """T+0 Strategy: Entry 10:29, Exit 14:03"""
    bond_code = '111012'
    entry_time = '10:29'
    exit_time = '14:03'

    print("=" * 70)
    print(f"  T+0 Strategy - {bond_code} 福新转债")
    print("=" * 70)
    print(f"\n📋 Strategy Rules:")
    print(f"   • Entry: {entry_time} if MACD bullish + high volume")
    print(f"   • Exit: {exit_time} (fixed time)")

    print(f"\n🔄 Fetching minute data...")

    try:
        import efinance as ef
        df = ef.bond.get_quote_history(bond_code, klt=1)

        if df is None or df.empty:
            print("   ❌ No data")
            return

        print(f"   ✅ Got {len(df)} minute bars")

        # Process data
        df['datetime'] = pd.to_datetime(df['日期'])
        df['time'] = df['datetime'].dt.strftime('%H:%M')
        df['close'] = pd.to_numeric(df['收盘'], errors='coerce')
        df['volume'] = pd.to_numeric(df['成交量'], errors='coerce')

        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(df['close'])
        df['macd'] = macd_line
        df['signal'] = signal_line

        # Volume ratio
        volume_avg = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / volume_avg

        # Get entry and exit data
        entry_data = df[df['time'] == entry_time]
        exit_data = df[df['time'] == exit_time]

        print(f"\n📊 Today's Analysis:")

        if not entry_data.empty:
            entry = entry_data.iloc[0]
            vol_ratio = entry['volume_ratio'] if not pd.isna(
                entry['volume_ratio']) else 0
            macd_bullish = entry['macd'] > entry['signal']

            print(f"\n   ⏰ {entry_time} (Entry Check):")
            print(f"      Price: {entry['close']:.2f}")
            print(
                f"      MACD: {entry['macd']:.4f} vs Signal: {entry['signal']:.4f}")
            print(f"      Volume Ratio: {vol_ratio:.1f}x")
            print(
                f"      MACD Status: {'🟢 BULLISH' if macd_bullish else '🔴 BEARISH'}")

            if macd_bullish and vol_ratio > 3:  # Relaxed volume threshold
                print(f"      ✅ ENTRY SIGNAL!")
                entry_price = entry['close']
            else:
                print(f"      ❌ No entry (need MACD bullish + volume)")
                entry_price = None
        else:
            print(f"\n   ⏰ {entry_time}: No data")
            entry_price = None

        if not exit_data.empty:
            exit_row = exit_data.iloc[0]
            print(f"\n   ⏰ {exit_time} (Exit):")
            print(f"      Price: {exit_row['close']:.2f}")
            exit_price = exit_row['close']
        else:
            print(f"\n   ⏰ {exit_time}: No data yet")
            exit_price = None

        # Calculate P&L
        if entry_price and exit_price:
            pnl = (exit_price - entry_price) / entry_price * 100
            emoji = "✅" if pnl > 0 else "❌"
            print(f"\n💰 Trade Result:")
            print(f"   Entry: {entry_price:.2f} @ {entry_time}")
            print(f"   Exit:  {exit_price:.2f} @ {exit_time}")
            print(f"   P&L:   {pnl:+.2f}% {emoji}")
        elif entry_price and not exit_price:
            # Use current price
            current = df.iloc[-1]
            unrealized = (current['close'] - entry_price) / entry_price * 100
            print(f"\n💰 Open Position:")
            print(f"   Entry: {entry_price:.2f} @ {entry_time}")
            print(f"   Current: {current['close']:.2f} @ {current['time']}")
            print(f"   Unrealized: {unrealized:+.2f}%")
            print(f"   ⏳ Wait for {exit_time} to exit")

        # Show day summary
        first = df.iloc[0]
        last = df.iloc[-1]
        day_change = (last['close'] - first['close']) / first['close'] * 100
        print(f"\n📈 Day Summary:")
        print(f"   Open: {first['close']:.2f} → Current: {last['close']:.2f}")
        print(f"   Day Change: {day_change:+.2f}%")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
