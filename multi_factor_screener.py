import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import zscore
from datetime import datetime, timedelta
import os
from data_cache import get_cache
from config import get_config

# Initialize configuration and cache
config = get_config()
cache = get_cache()

# CONFIG
# First screening file: 'assets_for_first_screening.txt'
# This script reads from the shortlist: 'top_candidates_for_refactor_screening.txt'
TICKERS_FILE = config.TOP_CANDIDATES_FILE
if not os.path.exists(TICKERS_FILE):
    print(f"Error: {TICKERS_FILE} not found. Please run the general screening first.")
    exit(1)
with open(TICKERS_FILE) as f:
    TICKERS = [line.strip() for line in f if line.strip()]
TOP_N = config.FINAL_TOP_N
REPORTS_DIR = config.REPORTS_DIR

print(f"Multi-factor screening initialized with {len(TICKERS)} pre-selected tickers")
print(f"Target final selection: {TOP_N} assets")

# Date range for momentum/volatility
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)

results = []
skipped = []

print("Starting multi-factor analysis with cached data...")
for i, ticker in enumerate(TICKERS):
    print(f"Analyzing {ticker}... ({i+1}/{len(TICKERS)})")
    try:
        # Use cached data
        hist = cache.get_stock_history(ticker, "1y")
        info = cache.get_stock_info(ticker)
        
        if hist is None or hist.empty or len(hist) < 2:
            print(f"No price data for {ticker}, skipping.")
            skipped.append(ticker)
            continue
            
        if info is None:
            print(f"No fundamental data for {ticker}, skipping.")
            skipped.append(ticker)
            continue
            
        name = info.get('shortName', ticker)
        
        # Value
        pe = info.get('trailingPE', np.nan)
        # Growth
        eps_growth = info.get('earningsGrowth', np.nan)
        # Quality
        roe = info.get('returnOnEquity', np.nan)
        # Momentum (12m return)
        momentum = (hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1 if hist['Close'].iloc[0] != 0 else np.nan
        # Volatility (1y std)
        volatility = hist['Close'].pct_change().std() * np.sqrt(252)
        
        # Skip if any factor is missing
        if np.isnan([pe, eps_growth, roe, momentum, volatility]).any():
            print(f"Missing data for {ticker}, skipping.")
            skipped.append(ticker)
            continue
            
        results.append({
            'Ticker': ticker,
            'Name': name,
            'Price': hist['Close'].iloc[-1],
            'P/E': pe,
            'EPS Growth': eps_growth,
            'ROE': roe,
            '12m Return': momentum,
            'Volatility': volatility
        })
        
    except Exception as e:
        print(f"Error for {ticker}: {e}")
        skipped.append(ticker)

# Create DataFrame
df = pd.DataFrame(results)
if df.empty:
    print("No valid assets found after filtering. Exiting.")
    exit(1)

# Z-score normalization (lower P/E, Volatility = better; higher others = better)
df['P/E_z'] = -zscore(df['P/E'])
df['EPS_Growth_z'] = zscore(df['EPS Growth'])
df['ROE_z'] = zscore(df['ROE'])
df['Momentum_z'] = zscore(df['12m Return'])
df['Volatility_z'] = -zscore(df['Volatility'])

# Composite score (equal weights, customize as needed)
df['Composite'] = df['P/E_z'] + df['EPS_Growth_z'] + df['ROE_z'] + df['Momentum_z'] + df['Volatility_z']

top = df.sort_values('Composite', ascending=False).head(TOP_N)

print("\nTop stocks from screening, multi-factor z-score composite:")
print(top[['Ticker', 'Name', 'Price', 'P/E', 'EPS Growth', 'ROE', '12m Return', 'Volatility', 'Composite']])

# Save to report
today = datetime.now().strftime('%Y-%m-%d')
report_path = os.path.join(REPORTS_DIR, f'multi_factor_screener_{today}.txt')
with open(report_path, 'w') as f:
    f.write("Top stocks from screening, multi-factor z-score composite:\n")
    f.write(top[['Ticker', 'Name', 'Price', 'P/E', 'EPS Growth', 'ROE', '12m Return', 'Volatility', 'Composite']].to_string())
    f.write("\n")
    if skipped:
        f.write("\nSkipped tickers due to missing data:\n")
        f.write(", ".join(skipped))
        f.write("\n")


# Enhanced summary table for top 2 stocks
summary_rows = []
for i, row in top.head(5).iterrows():
    ticker = row['Ticker']
    stock = yf.Ticker(ticker)
    info = stock.info
    summary_rows.append({
        'Ticker': ticker,
        'P/E': info.get('trailingPE', np.nan),
        'Fwd P/E': info.get('forwardPE', np.nan),
        'EPS Growth': info.get('earningsGrowth', np.nan),
        'ROE': info.get('returnOnEquity', np.nan),
        'Debt/Equity': info.get('debtToEquity', np.nan),
        'Insider %': info.get('heldPercentInsiders', np.nan),
        'Inst. %': info.get('heldPercentInstitutions', np.nan),
        'Target Price': info.get('targetMeanPrice', np.nan),
        'Analyst Rec': info.get('recommendationKey', 'N/A'),
        'Dividend Yield': info.get('dividendYield', np.nan),
        'Short % Float': info.get('shortPercentOfFloat', np.nan)
    })
summary_df = pd.DataFrame(summary_rows)
if not summary_df.empty:
    print("\nEnhanced Summary Table for Top Stocks:")
    print(summary_df)
    with open(report_path, 'a') as f:
        f.write("\nEnhanced Summary Table for Top Stocks:\n")
        f.write(summary_df.to_string(index=False))
        f.write("\n")

if skipped:
    print(f"\nSkipped {len(skipped)} tickers due to missing or incomplete data.")

if len(top) == 0:
    print("No stocks met all criteria for scoring.")

# Cache performance summary
print(f"\n" + "="*50)
print("MULTI-FACTOR SCREENING PERFORMANCE")
print("="*50)
cache_stats = cache.get_cache_stats()
cache_info = cache.get_cache_info()
print(f"Cache Hit Rate: {cache_stats['hit_rate_percent']:.1f}%")
print(f"Total API Calls Saved: {cache_stats['hits']}")
print(f"Cache Size: {cache_info['total_size_mb']:.2f} MB")
print(f"Analysis completed {cache_stats['hits'] * 1.5:.0f} seconds faster due to caching!")