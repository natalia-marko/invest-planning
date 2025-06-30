import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import os
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import zscore
from data_cache import get_cache
from config import get_config

# Initialize configuration and cache
config = get_config()
cache = get_cache()

# Read tickers from assets_for_first_screening.txt
ASSETS_FILE = config.ASSETS_FILE
if not os.path.exists(ASSETS_FILE):
    print(f"Error: {ASSETS_FILE} not found. Please provide a list of tickers to compare.")
    exit(1)
with open(ASSETS_FILE, 'r') as f:
    TICKERS = [line.strip() for line in f if line.strip()]
if not TICKERS:
    print("No tickers found in assets_for_first_screening.txt.")
    exit(1)

# Use configuration parameters
FUNDAMENTAL_PERIOD = config.FUNDAMENTAL_PERIOD
RETURNS_PERIOD = config.RETURNS_PERIOD
TOP_SELECTED = config.TOP_SELECTED
REPORTS_DIR = config.REPORTS_DIR

print(f"Initialized with {len(TICKERS)} tickers, cache system enabled")
print(f"Configuration: TOP_SELECTED={TOP_SELECTED}, FUNDAMENTAL_PERIOD={FUNDAMENTAL_PERIOD}")

# --- FUNDAMENTAL DATA COLLECTION (WITH CACHING) ---
def get_fundamental_data(tickers, period="1y"):
    """Get fundamental data for tickers using intelligent caching"""
    data_list = []
    missing_indicators = {}
    
    print(f"Fetching fundamental data for {len(tickers)} tickers...")
    
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:  # Progress indicator
            print(f"Progress: {i}/{len(tickers)} tickers processed")
            
        try:
            # Use cached data fetching
            history = cache.get_stock_history(ticker, period)
            info = cache.get_stock_info(ticker)
            
            if history is None or history.empty:
                print(f"Skipping {ticker} due to missing price data.")
                continue
                
            if info is None:
                print(f"Skipping {ticker} due to missing fundamental data.")
                continue
            
            # Fill missing values in price data
            history = history.ffill().bfill()
            
            # Extract fundamental metrics
            pe = float(info.get("trailingPE", np.nan))
            pb = info.get("priceToBook", np.nan)
            de_ratio = info.get("debtToEquity", np.nan)
            eps_growth = info.get("earningsGrowth", np.nan)
            name = info.get("shortName", ticker)
            
            stock_data = {
                "Ticker": ticker,
                "Name": name,
                "Price": history["Close"].iloc[-1],
                "P/E": pe,
                "P/B": pb,
                "Debt/Equity": de_ratio,
                "EPS Growth": eps_growth,
            }
            data_list.append(stock_data)
            
            # Track missing indicators
            missing_indicators[ticker] = {
                "P/E": pd.isna(pe),
                "P/B": pd.isna(pb),
                "Debt/Equity": pd.isna(de_ratio),
                "EPS Growth": pd.isna(eps_growth),
            }
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    # Create DataFrame
    df = pd.DataFrame(data_list).set_index("Ticker")
    df_cleaned = df.dropna()
    
    # Report missing data
    for ticker, missing_data in missing_indicators.items():
        missing_items = [indicator for indicator, missing in missing_data.items() if missing]
        if missing_items:
            print(f"For {ticker}, missing indicators: {', '.join(missing_items)}")
    
    print(f"Number of assets with complete fundamental data: {len(df_cleaned)}")
    
    # Print cache statistics
    cache_stats = cache.get_cache_stats()
    print(f"Cache performance: {cache_stats['hit_rate_percent']:.1f}% hit rate "
          f"({cache_stats['hits']} hits, {cache_stats['misses']} misses)")
    
    return df_cleaned

# --- RANKING LOGIC ---
def rank_undervalued(df, top_selected=TOP_SELECTED):
    df = df.copy()
    df["P/E Rank"] = df["P/E"].rank(ascending=True)
    df["P/B Rank"] = df["P/B"].rank(ascending=True)
    df["D/E Rank"] = df["Debt/Equity"].rank(ascending=True)
    df["EPS Growth Rank"] = df["EPS Growth"].rank(ascending=False)
    df["Total Score"] = df[["P/E Rank", "P/B Rank", "D/E Rank", "EPS Growth Rank"]].mean(axis=1)
    return df.sort_values("Total Score").head(top_selected)

# --- PORTFOLIO OPTIMIZATION ---
def optimize_portfolio(returns):
    if returns.empty:
        return np.array([])
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    n_assets = len(mean_returns)
    def negative_sharpe(weights):
        port_return = np.dot(weights, mean_returns)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -port_return / port_vol if port_vol != 0 else np.inf
    constraints = ({"type": "eq", "fun": lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(n_assets))
    initial_weights = np.ones(n_assets) / n_assets
    result = minimize(negative_sharpe, initial_weights, method="SLSQP", bounds=bounds, constraints=constraints)
    return result.x if result.success else np.array([])

# --- METRICS CALCULATION ---
def calculate_metrics(returns):
    returns = returns.dropna()
    if returns.empty:
        return {"Cumulative Return": np.nan, "Annualized Return": np.nan, "Annualized Volatility": np.nan, "Sharpe Ratio": np.nan, "Max Drawdown": np.nan}
    cumulative_return = (1 + returns).prod() - 1
    annualized_return = (1 + cumulative_return) ** (252 / len(returns)) - 1
    annualized_vol = returns.std() * np.sqrt(252)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol != 0 else np.nan
    cumulative_returns = (1 + returns).cumprod()
    rolling_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    return {
        "Cumulative Return": cumulative_return,
        "Annualized Return": annualized_return,
        "Annualized Volatility": annualized_vol,
        "Sharpe Ratio": sharpe_ratio,
        "Max Drawdown": max_drawdown,
    }

def calculate_sharpe(returns):
    ann_return = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    return ann_return / ann_vol if ann_vol > 0 else float('nan')

# --- MAIN LOGIC ---
def main():
    print("Fetching fundamental data...")
    fundamentals = get_fundamental_data(TICKERS, period=FUNDAMENTAL_PERIOD)
    if fundamentals.empty:
        print("No fundamental data available.")
        return
    print("\nRanking undervalued assets...")
    ranked = rank_undervalued(fundamentals, top_selected=TOP_SELECTED)
    print(ranked[["Name", "Price", "P/E", "P/B", "Debt/Equity", "EPS Growth", "Total Score"]])
    print(f"Number of assets with complete fundamental data: {len(fundamentals)}")
    print(f"Number of assets after return data filtering: {len(ranked)}")
    # Fetch returns and calculate Sharpe for the top undervalued assets (CACHED)
    print("\nFetching returns and calculating Sharpe for top undervalued assets...")
    returns_data = {}
    sharpes = {}
    skipped_tickers = []
    
    for ticker in ranked.index:
        # Use cached historical data
        hist = cache.get_stock_history(ticker, RETURNS_PERIOD)
        
        if hist is None or hist.empty:
            print(f"No return data for {ticker}, skipping.")
            skipped_tickers.append(ticker)
            continue
            
        returns = hist["Close"].pct_change().dropna()
        returns_data[ticker] = returns
        sharpes[ticker] = calculate_sharpe(returns)
    # Add Sharpe to ranked DataFrame
    ranked = ranked.loc[[t for t in ranked.index if t in returns_data.keys()]]
    ranked['Sharpe'] = [sharpes[t] for t in ranked.index]
    # Calculate Scaled Score: combine normalized -P/E rank, EPS Growth rank, Sharpe rank
    ranked['P/E Rank'] = ranked['P/E'].rank(ascending=True)
    ranked['EPS Growth Rank'] = ranked['EPS Growth'].rank(ascending=False)
    ranked['Sharpe Rank'] = ranked['Sharpe'].rank(ascending=False)
    scaler = MinMaxScaler()
    norm_ranks = scaler.fit_transform(ranked[['P/E Rank', 'EPS Growth Rank', 'Sharpe Rank']])
    ranked['Scaled Score'] = -norm_ranks[:,0] + norm_ranks[:,1] + norm_ranks[:,2]
    ranked = ranked.sort_values('Scaled Score', ascending=False)
    # Print and save top assets by Scaled Score with all relevant columns (top 10)
    top_assets = ranked[["Name", "Price", "P/E", "P/B", "Debt/Equity", "EPS Growth", "Sharpe", "Scaled Score"]].head(TOP_SELECTED)
    print("\nTop assets by Scaled Score (sorted):")
    print(top_assets)
    # Print and save top 30 shortlist for transparency
    top_30 = ranked[["Name", "Price", "P/E", "P/B", "Debt/Equity", "EPS Growth", "Sharpe", "Scaled Score"]].head(30)
    print("\nTop 30 assets shortlisted for further analysis:")
    print(top_30)
    # Save to report file (write mode)
    today = datetime.now().strftime('%Y-%m-%d')
    report_path = os.path.join(REPORTS_DIR, f'undervalued_assets_report_{today}.txt')
    with open(report_path, 'w') as f:
        f.write("Top assets by Scaled Score (sorted):\n")
        f.write(top_assets.to_string())
        f.write("\n\n")
        f.write("Top 30 assets shortlisted for further analysis:\n")
        f.write(top_30.to_string())
        f.write("\n\n")
    # Save top 30 tickers to top_candidates_for_refactor_screening.txt
    top_30_tickers = ranked.head(30).index.tolist()
    with open(config.TOP_CANDIDATES_FILE, 'w') as f:
        for ticker in top_30_tickers:
            f.write(f"{ticker}\n")
    # Fetch returns for the top undervalued assets
    print("\nFetching returns for top undervalued assets...")
    returns_df = pd.DataFrame(returns_data).dropna()
    # Portfolio optimization
    print("\nOptimizing portfolio of undervalued assets...")
    weights = optimize_portfolio(returns_df)
    if weights.size == 0:
        print("Portfolio optimization failed.")
        return
    # Portfolio metrics
    port_returns = returns_df.dot(weights)
    metrics = calculate_metrics(port_returns)
    # Save report (append mode)
    with open(report_path, 'a') as f:
        f.write("Portfolio Weights (optimized for Sharpe ratio):\n")
        for ticker, w in zip(ranked.index, weights):
            f.write(f"{ticker}: {w:.2%}\n")
        f.write("\nPortfolio Metrics:\n")
        for k, v in metrics.items():
            f.write(f"{k}: {v:.2%}\n")
        if skipped_tickers:
            f.write("\nSkipped tickers due to missing return data:\n")
            f.write(", ".join(skipped_tickers))
            f.write("\n")
        
        # Add cache performance to report
        cache_stats = cache.get_cache_stats()
        cache_info = cache.get_cache_info()
        f.write(f"\nCache Performance Summary:\n")
        f.write(f"Hit Rate: {cache_stats['hit_rate_percent']:.1f}%\n")
        f.write(f"Total Requests: {cache_stats['total_requests']}\n")
        f.write(f"Cache Size: {cache_info['total_size_mb']:.2f} MB\n")
        f.write(f"Cached Tickers: {len(cache_info['tickers_cached'])}\n")
    
    print(f"\nReport saved to {report_path}")
    print("\nPortfolio Weights:")
    for ticker, w in zip(ranked.index, weights):
        print(f"{ticker}: {w:.2%}")
    print("\nPortfolio Metrics:")
    for k, v in metrics.items():
        print(f"{k}: {v:.2%}")
    if skipped_tickers:
        print("\nSkipped tickers due to missing return data:")
        print(", ".join(skipped_tickers))
    
    # Final cache performance summary
    print(f"\n" + "="*50)
    print("PERFORMANCE SUMMARY")
    print("="*50)
    final_cache_stats = cache.get_cache_stats()
    final_cache_info = cache.get_cache_info()
    print(f"Cache Hit Rate: {final_cache_stats['hit_rate_percent']:.1f}%")
    print(f"Total API Calls: {final_cache_stats['misses']}")
    print(f"Cache Size: {final_cache_info['total_size_mb']:.2f} MB")
    print(f"Time Saved: Estimated {final_cache_stats['hits'] * 2:.0f} seconds from cache hits")
    print(f"Next run will be significantly faster with {len(final_cache_info['tickers_cached'])} tickers cached!")

if __name__ == '__main__':
    main() 