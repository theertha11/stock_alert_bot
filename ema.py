import time
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Path to CSV with stock tickers (update this path as needed)
csv_path = '/home/theertha/Downloads/Telegram Desktop/nifty_500.csv'

# Read tickers from CSV
try:
    stocks_df = pd.read_csv(csv_path)
except Exception as e:
    print(f"❌ Error reading CSV file: {e}")
    exit(1)

# Ensure the CSV has at least 3 columns (ticker assumed in the third column)
if stocks_df.shape[1] < 3:
    print("❌ CSV does not have enough columns.")
    exit(1)

# Extract tickers from the third column (index 2)
tickers = stocks_df.iloc[:, 2].dropna().astype(str).tolist()
# Clean ticker symbols and ensure '.NS' suffix
tickers = [ticker.strip() for ticker in tickers if ticker.strip()]
tickers = [ticker if ticker.endswith('.NS') else ticker + '.NS' for ticker in tickers]
tickers = sorted(set(tickers)) # remove duplicates and sort

print(f"Total stocks fetched: {len(tickers)}")

# Set date range (past 1 year)
end_date = datetime.today()
start_date = end_date - timedelta(days=365)

# List to accumulate each stock's Close price series
close_series_list = []

for ticker in tickers:
    try:
        print(f"Fetching data for {ticker}...")
        df = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False)
        time.sleep(1.5)
        if df is None or df.empty:
            print(f"⚠️ No data for {ticker}, skipping.")
            continue
        # Extract and rename the Close prices series
        close_prices = df['Close']
        close_prices.name = ticker
        close_series_list.append(close_prices)
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")

if close_series_list:
    # Combine all Close price series into a single DataFrame
    combined_df = pd.concat(close_series_list, axis=1)
    combined_df.sort_index(inplace=True)
    # Drop any rows where all values are NaN (if applicable)
    combined_df.dropna(how='all', inplace=True)
    # Save the combined DataFrame to an Excel file
    combined_df.to_excel("stocks_close_prices.xlsx")
    print("✅ Data fetching completed. Saved to 'stocks_close_prices.xlsx'.")
else:
    print("❌ No valid data fetched.")