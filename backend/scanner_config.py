"""
Scanner Configuration
Edit these settings before running the scanner.
"""

# ============ TELEGRAM SETTINGS ============
TELEGRAM_BOT_TOKEN = "8118773821:AAEzT87IEeZH3X_dcTZll4eE6fPHShuKYlA"
TELEGRAM_CHAT_ID = "1141127507"

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
