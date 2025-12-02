"""
Scanner Configuration
Edit these settings before running the scanner.
"""

# ============ TELEGRAM SETTINGS ============
# Set these as environment variables:
# export TELEGRAM_BOT_TOKEN="your_token"
# export TELEGRAM_CHAT_ID="your_chat_id"
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# ============ SCANNER SETTINGS ============
# How often to scan (seconds)
SCAN_INTERVAL = 60

# Minimum volume ratio to trigger alert
VOLUME_THRESHOLD = 3.0

# Minimum day change % to consider a bond
MIN_CHANGE_PCT = 1.0

# Number of top gainers to analyze
TOP_N_BONDS = 20

# ============ MARKET HOURS (China) ============
MARKET_OPEN_MORNING = "09:30"
MARKET_CLOSE_MORNING = "11:30"
MARKET_OPEN_AFTERNOON = "13:00"
MARKET_CLOSE_AFTERNOON = "15:00"
