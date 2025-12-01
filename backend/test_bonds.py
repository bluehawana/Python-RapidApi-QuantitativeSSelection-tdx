"""Get top 10 increased/decreased convertible bonds."""
import tushare as ts
import pandas as pd
from app.services.baostock_client import get_baostock_client

print('=== Convertible Bond Rankings ===\n')

# Get all active bonds from BaoStock
client = get_baostock_client()
bonds = client.get_convertible_bonds()
active_bonds = bonds[bonds['status'] == '1']
print(f"Found {len(active_bonds)} active convertible bonds\n")

# Build code list for tushare
all_codes = []
for code in active_bonds['code']:
    if code.startswith('sh.'):
        all_codes.append(code[3:])
    elif code.startswith('sz.'):
        all_codes.append(code[3:])

# Get realtime quotes in batches
print("Fetching realtime quotes...")
all_data = []
batch_size = 50

for i in range(0, len(all_codes), batch_size):
    batch = all_codes[i:i+batch_size]
    try:
        df = ts.get_realtime_quotes(batch)
        if df is not None and not df.empty:
            all_data.append(df)
    except Exception as e:
        print(f"Batch {i//batch_size + 1} error: {e}")

if all_data:
    df = pd.concat(all_data, ignore_index=True)
    print(f"Got quotes for {len(df)} bonds\n")

    # Convert to numeric
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['pre_close'] = pd.to_numeric(df['pre_close'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Calculate change percent
    df['change_pct'] = ((df['price'] - df['pre_close']) /
                        df['pre_close'] * 100).round(2)

    # Filter out invalid data
    df = df[df['price'] > 0]
    df = df[df['pre_close'] > 0]

    # Top 10 Gainers
    print("=" * 60)
    print("Top 10 Increased Bonds (涨幅榜)")
    print("=" * 60)
    top10_up = df.nlargest(10, 'change_pct')
    for idx, (_, row) in enumerate(top10_up.iterrows(), 1):
        amt = float(row['amount']) / 10000 if row['amount'] > 0 else 0
        print(
            f"{idx:2}. {row['code']} {row['name']:8} 价格:{row['price']:>8.2f}  涨幅:{row['change_pct']:>6.2f}%  成交额:{amt:>10.0f}万")

    # Top 10 Losers
    print("\n" + "=" * 60)
    print("Top 10 Decreased Bonds (跌幅榜)")
    print("=" * 60)
    top10_down = df.nsmallest(10, 'change_pct')
    for idx, (_, row) in enumerate(top10_down.iterrows(), 1):
        amt = float(row['amount']) / 10000 if row['amount'] > 0 else 0
        print(
            f"{idx:2}. {row['code']} {row['name']:8} 价格:{row['price']:>8.2f}  涨幅:{row['change_pct']:>6.2f}%  成交额:{amt:>10.0f}万")

    # Top 10 by Volume
    print("\n" + "=" * 60)
    print("Top 10 Trading Volume (成交额榜)")
    print("=" * 60)
    top10_vol = df.nlargest(10, 'amount')
    for idx, (_, row) in enumerate(top10_vol.iterrows(), 1):
        amt = float(row['amount']) / 10000 if row['amount'] > 0 else 0
        print(
            f"{idx:2}. {row['code']} {row['name']:8} 价格:{row['price']:>8.2f}  涨幅:{row['change_pct']:>6.2f}%  成交额:{amt:>10.0f}万")

    # Low price bonds (under 110)
    print("\n" + "=" * 60)
    print("Low Price Bonds (低价榜 < 110元)")
    print("=" * 60)
    low_price = df[df['price'] < 110].nsmallest(10, 'price')
    for idx, (_, row) in enumerate(low_price.iterrows(), 1):
        amt = float(row['amount']) / 10000 if row['amount'] > 0 else 0
        print(
            f"{idx:2}. {row['code']} {row['name']:8} 价格:{row['price']:>8.2f}  涨幅:{row['change_pct']:>6.2f}%  成交额:{amt:>10.0f}万")

else:
    print("Failed to get bond data")
