"""
Real-time T+0 Bond Scanner with Telegram Alerts

Runs during market hours (9:30-15:00), scans for:
- Golden Cross + High Volume signals
- Sends alerts to Telegram when found

Usage:
1. Set your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID below
2. Run: python realtime_scanner.py
3. Or schedule to run at market open
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import requests
import time as time_module
import warnings
warnings.filterwarnings('ignore')

# ============ CONFIGURE YOUR TELEGRAM HERE ============
TELEGRAM_BOT_TOKEN = "8118773821:AAEzT87IEeZH3X_dcTZll4eE6fPHShuKYlA"
TELEGRAM_CHAT_ID = "1141127507"
# ======================================================

# Scan interval in seconds
SCAN_INTERVAL = 60  # Check every 1 minute

# Alert thresholds
VOLUME_THRESHOLD = 3.0  # Volume > 3x average triggers alert
MIN_CHANGE_PCT = 1.0    # Minimum day change % to consider


def send_telegram(message):
    """Send message to Telegram."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[TELEGRAM DISABLED] {message}")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig


def is_market_hours():
    """Check if within China market hours.

    China market: 9:30-11:30, 13:00-15:00 CST (UTC+8)
    Your local time (UTC+1 or similar): 2:30-4:30, 6:00-8:00 AM

    Adjust LOCAL_OFFSET if needed (hours behind China)
    """
    LOCAL_OFFSET = 7  # Your timezone is 7 hours behind China

    now = datetime.now().time()

    # Morning session: China 9:30-11:30 = Local 2:30-4:30
    morning_start = time(9 - LOCAL_OFFSET + 24 if 9 -
                         LOCAL_OFFSET < 0 else 9 - LOCAL_OFFSET, 30)
    morning_end = time(11 - LOCAL_OFFSET + 24 if 11 -
                       LOCAL_OFFSET < 0 else 11 - LOCAL_OFFSET, 30)

    # Afternoon session: China 13:00-15:00 = Local 6:00-8:00
    afternoon_start = time(13 - LOCAL_OFFSET, 0)
    afternoon_end = time(15 - LOCAL_OFFSET, 0)

    # For 7 hour offset: morning 2:30-4:30, afternoon 6:00-8:00
    morning = time(2, 30) <= now <= time(4, 30)
    afternoon = time(6, 0) <= now <= time(8, 0)

    return morning or afternoon


def get_all_bonds():
    """Get all convertible bonds with real-time data."""
    try:
        import efinance as ef
        df = ef.bond.get_realtime_quotes()
        if df is not None and not df.empty:
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce')
            df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
            return df
    except Exception as e:
        print(f"Error getting bonds: {e}")
    return None


def analyze_bond_realtime(code):
    """Analyze a single bond for entry signals."""
    try:
        import efinance as ef
        df = ef.bond.get_quote_history(code, klt=1)

        if df is None or len(df) < 30:
            return None

        df['close'] = pd.to_numeric(df['收盘'], errors='coerce')
        df['volume'] = pd.to_numeric(df['成交量'], errors='coerce')
        df['time'] = pd.to_datetime(df['日期']).dt.strftime('%H:%M')

        macd, sig, hist = calculate_macd(df['close'])
        df['macd'], df['signal'], df['hist'] = macd, sig, hist

        vol_avg = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / vol_avg

        # Detect signals
        df['golden'] = (df['macd'] > df['signal']) & (
            df['macd'].shift(1) <= df['signal'].shift(1))
        df['dead'] = (df['macd'] < df['signal']) & (
            df['macd'].shift(1) >= df['signal'].shift(1))

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # Check for fresh golden cross (in last 3 bars)
        recent_golden = df['golden'].iloc[-3:].any()

        return {
            'price': latest['close'],
            'macd': latest['macd'],
            'signal': latest['signal'],
            'hist': latest['hist'],
            'vol_ratio': latest['vol_ratio'] if not pd.isna(latest['vol_ratio']) else 0,
            'bullish': latest['macd'] > latest['signal'],
            'golden_cross': recent_golden,
            'dead_cross': latest['dead'],
            'time': latest['time']
        }
    except:
        return None


def scan_for_signals():
    """Scan all bonds for entry signals."""
    signals = []

    # Get top movers
    bonds = get_all_bonds()
    if bonds is None:
        return signals

    # Filter to top 20 gainers with decent volume
    bonds = bonds[bonds['涨跌幅'] >= MIN_CHANGE_PCT]
    bonds = bonds.sort_values('涨跌幅', ascending=False).head(20)

    print(f"   Analyzing {len(bonds)} bonds...", end=" ")

    for _, row in bonds.iterrows():
        code = row['债券代码']
        name = row['债券名称']
        change = row['涨跌幅']

        data = analyze_bond_realtime(code)
        if data is None:
            continue

        # Check for entry signal: Golden cross + high volume + MACD bullish
        if data['golden_cross'] and data['vol_ratio'] > VOLUME_THRESHOLD and data['bullish']:
            signals.append({
                'code': code,
                'name': name,
                'price': data['price'],
                'change': change,
                'vol_ratio': data['vol_ratio'],
                'macd': data['macd'],
                'signal_type': 'GOLDEN_CROSS_ENTRY',
                'time': data['time']
            })

        # Also alert on high volume + bullish MACD (potential entry coming)
        elif data['vol_ratio'] > VOLUME_THRESHOLD * 1.5 and data['bullish']:
            signals.append({
                'code': code,
                'name': name,
                'price': data['price'],
                'change': change,
                'vol_ratio': data['vol_ratio'],
                'macd': data['macd'],
                'signal_type': 'HIGH_VOLUME_WATCH',
                'time': data['time']
            })

    return signals


def format_alert(signal):
    """Format signal as Telegram message."""
    emoji = "🚀" if signal['signal_type'] == 'GOLDEN_CROSS_ENTRY' else "👀"

    msg = f"""
{emoji} <b>{signal['signal_type']}</b>

📈 <b>{signal['code']} {signal['name']}</b>
💰 Price: {signal['price']:.2f}
📊 Day: {signal['change']:+.2f}%
📊 Volume: {signal['vol_ratio']:.1f}x average
⏰ Time: {signal['time']}

{'🟢 ENTRY SIGNAL - Consider buying!' if signal['signal_type'] == 'GOLDEN_CROSS_ENTRY' else '⚠️ Watch for golden cross'}
"""
    return msg.strip()


def run_scanner():
    """Main scanner loop."""
    print("=" * 60)
    print("  T+0 Real-time Bond Scanner with Telegram Alerts")
    print("=" * 60)

    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n⚠️  TELEGRAM NOT CONFIGURED!")
        print("   Edit TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in this file")
        print("   Running in console-only mode...\n")
    else:
        print(f"\n✅ Telegram configured, alerts will be sent")
        send_telegram(
            "🤖 T+0 Scanner Started!\nMonitoring top 20 bonds for signals...")

    print(f"📋 Strategy: Golden Cross + Volume > {VOLUME_THRESHOLD}x")
    print(f"🔄 Scan interval: {SCAN_INTERVAL} seconds")
    print(f"📊 Monitoring: Top 20 gainers with change >= {MIN_CHANGE_PCT}%\n")

    alerted = set()  # Track already alerted signals to avoid spam
    scan_count = 0

    while True:
        now = datetime.now()
        scan_count += 1

        # Check market hours
        if not is_market_hours():
            print(f"[{now.strftime('%H:%M:%S')}] Market closed. Waiting...")
            time_module.sleep(60)
            continue

        print(f"[{now.strftime('%H:%M:%S')}] Scan #{scan_count}...", end=" ")

        try:
            signals = scan_for_signals()

            if signals:
                new_signals = [
                    s for s in signals if f"{s['code']}_{s['signal_type']}" not in alerted]

                print(f"Found {len(signals)} signals ({len(new_signals)} new)")

                for sig in new_signals:
                    key = f"{sig['code']}_{sig['signal_type']}"
                    alerted.add(key)

                    # Print to console
                    emoji = "🚀" if sig['signal_type'] == 'GOLDEN_CROSS_ENTRY' else "👀"
                    print(
                        f"\n   {emoji} {sig['code']} {sig['name']}: {sig['change']:+.2f}% Vol:{sig['vol_ratio']:.1f}x")

                    # Send Telegram
                    msg = format_alert(sig)
                    send_telegram(msg)
            else:
                print("No signals")

        except Exception as e:
            print(f"Error: {e}")

        # Reset alerts every hour to allow re-alerting
        if now.minute == 0:
            alerted.clear()

        time_module.sleep(SCAN_INTERVAL)


def run_once():
    """Run a single scan (for testing)."""
    print("=" * 60)
    print("  T+0 Scanner - Single Scan Mode")
    print("=" * 60)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Scanning top 20 gainers...\n")

    signals = scan_for_signals()

    if signals:
        print(f"Found {len(signals)} signals:\n")
        for sig in signals:
            emoji = "🚀" if sig['signal_type'] == 'GOLDEN_CROSS_ENTRY' else "👀"
            print(f"{emoji} {sig['code']} {sig['name']}")
            print(
                f"   Price: {sig['price']:.2f} | Change: {sig['change']:+.2f}%")
            print(f"   Volume: {sig['vol_ratio']:.1f}x | Time: {sig['time']}")
            print(f"   Type: {sig['signal_type']}\n")
    else:
        print("No signals found")

    return signals


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single scan mode for testing
        run_once()
    else:
        # Continuous monitoring mode
        run_scanner()
