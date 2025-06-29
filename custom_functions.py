#!/usr/bin/env python3

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

def calculate_technical_indicators(df):
    """
    Calculate various technical indicators for the stock.
    - IMPROVEMENT: Correctly calculates RSI using EMA (Wilder's smoothing).
    """
    # Simple Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # Volume Moving Average
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']

    # --- CORRECT RSI CALCULATION (using EMA) ---
    delta = df['Close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use Exponential Moving Average (EMA) for RSI calculation
    avg_gain = gain.ewm(com=13, min_periods=14).mean() # com=13 is equivalent to alpha=1/14
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD Calculation
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    return df.dropna() # Drop initial rows with NaN values

def generate_trading_signals(df):
    """
    Generate trading signals based on a confluence of indicators.
    - IMPROVEMENT: Uses a voting system for stronger signals (confluence).
    """
    signals = pd.DataFrame(index=df.index)
    
    # Generate individual signals (1 for Buy, -1 for Sell, 0 for Neutral)
    signals['SMA'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1)
    signals['RSI'] = np.select(
        [df['RSI'] < 30, df['RSI'] > 70],
        [1, -1],
        default=0
    )
    signals['MACD'] = np.where(df['MACD'] > df['Signal_Line'], 1, -1)
    
    # --- IMPROVED CONFLUENCE LOGIC ---
    # Create a score based on the sum of signals. A buy signal requires at least 2/3 indicators to be bullish.
    # A sell signal requires at least 2/3 to be bearish.
    # We also require high volume to confirm the move.
    
    signals['Indicator_Score'] = signals['SMA'] + signals['RSI'] + signals['MACD']
    high_volume_condition = df['Volume_Ratio'] > 1.25

    # Final Combined Signal
    signals['Signal'] = 0
    signals.loc[(signals['Indicator_Score'] >= 2) & high_volume_condition, 'Signal'] = 1  # Strong Buy
    signals.loc[(signals['Indicator_Score'] <= -2) & high_volume_condition, 'Signal'] = -1 # Strong Sell

    return signals

def find_trade_points(signals):
    """
    Find the exact points in time to execute a trade based on signal changes.
    Returns boolean Series for buy and sell points.
    """
    signal_col = signals['Signal']
    # A "buy" signal is the first day the signal turns to 1
    buy_signals = (signal_col == 1) & (signal_col.shift(1) != 1)
    # A "sell" signal is the first day the signal turns to -1
    sell_signals = (signal_col == -1) & (signal_col.shift(1) != -1)
    return buy_signals, sell_signals

def plot_analysis(df, signals, buy_points, sell_points, ticker):
    """
    Plot the stock price, indicators, and trade points.
    - IMPROVEMENT: Plots Volume Ratio on a secondary axis for better visualization.
    """
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f'Technical Analysis for {ticker.upper()}', fontsize=16)

    # Plot 1: Price, SMAs, and Trade Signals
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(df.index, df['Close'], label='Close Price', color='k')
    ax1.plot(df.index, df['SMA_50'], label='50-day SMA', color='orange', linestyle='--')
    ax1.plot(df.index, df['SMA_200'], label='200-day SMA', color='purple', linestyle='--')
    ax1.scatter(df.index[buy_points], df['Close'][buy_points], marker='^', color='g', label='Buy Signal', s=150, zorder=5)
    ax1.scatter(df.index[sell_points], df['Close'][sell_points], marker='v', color='r', label='Sell Signal', s=150, zorder=5)
    ax1.set_title('Price, Moving Averages, and Signals')
    ax1.legend()
    ax1.grid(True)

    # Plot 2: Volume and Volume Ratio
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.bar(df.index, df['Volume'], label='Volume', color='lightblue')
    ax2.plot(df.index, df['Volume_SMA_20'], label='20-day Volume MA', color='blue', linestyle='--')
    ax2.set_title('Volume Analysis')
    ax2.legend(loc='upper left')
    ax2.grid(True)
    # --- IMPROVEMENT: Secondary axis for Volume Ratio ---
    ax2b = ax2.twinx()
    ax2b.plot(df.index, df['Volume_Ratio'], label='Volume Ratio (Price/SMA20)', color='red', alpha=0.6)
    ax2b.axhline(1.25, color='red', linestyle='--', alpha=0.5)
    ax2b.set_ylim(0, ax2b.get_ylim()[1] * 0.5) # Adjust ylim to make it readable
    ax2b.legend(loc='upper right')

    # Plot 3: RSI
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.plot(df.index, df['RSI'], label='RSI')
    ax3.axhline(70, color='r', linestyle='--', label='Overbought (70)')
    ax3.axhline(30, color='g', linestyle='--', label='Oversold (30)')
    ax3.set_title('Relative Strength Index (RSI)')
    ax3.legend()
    ax3.grid(True)
    
    # Plot 4: MACD
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)
    ax4.plot(df.index, df['MACD'], label='MACD', color='blue')
    ax4.plot(df.index, df['Signal_Line'], label='Signal Line', color='orange', linestyle='--')
    ax4.bar(df.index, df['MACD'] - df['Signal_Line'], label='Histogram', color='gray', alpha=0.5)
    ax4.set_title('MACD')
    ax4.legend()
    ax4.grid(True)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.97]) # Adjust for suptitle
    plt.savefig('stock_analysis.png', dpi=300)
    plt.close()

def backtest_strategy(df, buy_signals, sell_signals, stop_loss_pct=0.05, take_profit_pct=0.10):
    """
    - NEW FEATURE: Simple backtest to evaluate strategy performance.
    """
    cash = 10000
    position = 0
    portfolio_value = []
    
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        
        # Check stop-loss or take-profit
        if position > 0:
            if current_price <= stop_loss_price or current_price >= take_profit_price:
                cash = position * current_price
                position = 0
        
        # Check for buy signal
        if position == 0 and buy_signals.iloc[i]:
            position = cash / current_price
            cash = 10000
            # Set exit targets
            stop_loss_price = current_price * (1 - stop_loss_pct)
            take_profit_price = current_price * (1 + take_profit_pct)

        # Check for sell signal (as an exit for a long position)
        elif position > 0 and sell_signals.iloc[i]:
            cash = position * current_price
            position = 0

        # Update portfolio value
        current_value = cash + position * current_price
        portfolio_value.append(current_value)

    # Handle empty portfolio_value to avoid IndexError
    if not portfolio_value:
        return float('nan'), float('nan'), []

    # Final calculations
    final_value = portfolio_value[-1]
    total_return_pct = ((final_value / 10000) - 1) * 100
    buy_hold_return_pct = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
    
    return total_return_pct, buy_hold_return_pct, portfolio_value

def calculate_sortino_ratio(returns, risk_free_rate):
    avg_return = returns.mean() * 252
    downside_returns = returns[returns < 0]
    downside_std = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
    return (avg_return - risk_free_rate) / downside_std if downside_std != 0 else np.nan

def analyze_asset(ticker, start_date, end_date):
    print(f"\n===== Analyzing {ticker} =====")
    stock = yf.Ticker(ticker)
    df_raw = stock.history(start=start_date, end=end_date)
    if df_raw.empty:
        print(f"No data found for ticker {ticker}. Skipping.")
        return None
    # Print actual data window (optional, can comment out)
    # data_start = df_raw.index.min()
    # data_end = df_raw.index.max()
    # window_years = (data_end - data_start).days / 365
    # print(f"Data window: {data_start.date()} to {data_end.date()} ({window_years:.2f} years)")
    df = calculate_technical_indicators(df_raw)
    if df.empty:
        print(f"No valid data after technical indicator calculation for ticker {ticker}. Skipping.")
        return None
    signals = generate_trading_signals(df)
    buy_points, sell_points = find_trade_points(signals)
    strategy_return, buy_hold_return, portfolio_history = backtest_strategy(df, buy_points, sell_points)
    last_price = df['Close'].iloc[-1]
    last_signal = signals['Signal'].iloc[-1]
    signal_text = "BUY" if last_signal == 1 else "SELL" if last_signal == -1 else "NEUTRAL"
    # Calculate Sharpe ratio for the asset (annualized, daily returns)
    returns = df['Close'].pct_change().dropna()
    ann_return = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float('nan')
    print(f"Current Price: ${last_price:.2f}")
    print(f"Buy & Hold Return (1y): {buy_hold_return:.2f}%")
    print(f"Buy/Sell Strategy Return (1y): {strategy_return:.2f}%")
    print(f"Sharpe Ratio (1y): {sharpe:.2f}")
    print(f"Current Signal: {signal_text}")
    return {
        'ticker': ticker,
        'df': df,
        'buy_points': buy_points,
        'sell_points': sell_points,
        'buy_hold_return': buy_hold_return,
        'last_price': last_price,
        'signal': signal_text,
        'sharpe': sharpe
    }

def portfolio_metrics(results, weights):
    price_dfs = [res['df']['Close'].rename(res['ticker']) for res in results]
    prices = pd.concat(price_dfs, axis=1).dropna()
    returns = prices.pct_change().dropna()
    weights = np.array(weights)
    port_returns = returns.dot(weights)
    ann_return = np.mean(port_returns) * 252
    ann_vol = np.std(port_returns) * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else np.nan
    cumulative = (1 + port_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min()
    return {
        'ann_return': ann_return,
        'ann_vol': ann_vol,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown
    }

def save_report_image(results, metrics, filename):
    fig, ax = plt.subplots(figsize=(10, 2 + 0.4*len(results)))
    ax.axis('off')
    lines = []
    lines.append(f"Portfolio Report - {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"{'Ticker':<8} {'Price':>8} {'Sharpe':>8} {'B&H%':>8} {'Signal':>8}")
    for r in results:
        lines.append(f"{r['ticker']:<8} {r['last_price']:>8.2f} {r['sharpe']:>8.2f} {r['buy_hold_return']:>8.2f} {r['signal']:>8}")
    lines.append("")
    lines.append("Portfolio Level Metrics (Weighted by Amount):")
    lines.append(f"Annualized Return:     {metrics['ann_return']*100:.2f}%")
    lines.append(f"Annualized Volatility: {metrics['ann_vol']*100:.2f}%")
    lines.append(f"Sharpe Ratio:          {metrics['sharpe']:.2f}")
    lines.append(f"Max Drawdown:          {metrics['max_drawdown']*100:.2f}%")
    report_text = "\n".join(lines)
    ax.text(0, 1, report_text, fontsize=14, va='top', family='monospace')
    plt.tight_layout()
    plt.savefig(filename, dpi=200, bbox_inches='tight')
    plt.close()

def filter_assets(df, min_sharpe, max_drawdown=None):
    mask = df['Sharpe'] >= min_sharpe
    if max_drawdown is not None:
        mask &= (df['MaxDrawdown%'] >= max_drawdown * 100)
    return df[mask]

def plot_efficient_frontier(filtered_df, returns_dict, num_portfolios=5000):
    filtered_tickers = filtered_df['Ticker'].tolist()
    returns_matrix = pd.DataFrame({t: returns_dict[t] for t in filtered_tickers}).dropna()
    valid_tickers = list(returns_matrix.columns)
    mean_returns = returns_matrix.mean() * 252
    cov_matrix = returns_matrix.cov() * 252
    port_returns, port_vols, port_sharpes, port_weights = [], [], [], []
    for _ in range(num_portfolios):
        weights = np.random.dirichlet(np.ones(len(valid_tickers)), size=1)[0]
        port_weights.append(weights)
        port_return = np.dot(weights, mean_returns[valid_tickers])
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.loc[valid_tickers, valid_tickers], weights)))
        sharpe = port_return / port_vol if port_vol > 0 else 0
        port_returns.append(port_return)
        port_vols.append(port_vol)
        port_sharpes.append(sharpe)
    port_returns = np.array(port_returns)
    port_vols = np.array(port_vols)
    port_sharpes = np.array(port_sharpes)
    port_weights = np.array(port_weights)
    min_vol_idx = np.argmin(port_vols)
    max_sharpe_idx = np.argmax(port_sharpes)
    asset_vols = filtered_df.set_index('Ticker').loc[valid_tickers]['ann_vol'].values
    asset_returns = filtered_df.set_index('Ticker').loc[valid_tickers]['ann_return'].values
    asset_labels = valid_tickers
    top5_indices = np.argsort(port_weights[max_sharpe_idx])[-5:][::-1]
    top5_assets = [valid_tickers[i] for i in top5_indices]
    top5_weights = port_weights[max_sharpe_idx][top5_indices]
    print('Top 5 assets by max Sharpe portfolio weight:')
    for t, w in zip(top5_assets, top5_weights):
        print(f'{t}: {w:.2%}')
    plt.figure(figsize=(10,6))
    plt.plot(port_vols, port_returns, label='Efficient frontier', color='dodgerblue')
    plt.scatter(asset_vols, asset_returns, marker='o', color='black', label='assets')
    for i, label in enumerate(asset_labels):
        plt.annotate(label, (asset_vols[i], asset_returns[i]), textcoords='offset points', xytext=(5,5), ha='left', fontsize=9)
    plt.scatter(port_vols[min_vol_idx], port_returns[min_vol_idx], marker='*', color='red', s=200, label='Minimum Volatility')
    plt.scatter(port_vols[max_sharpe_idx], port_returns[max_sharpe_idx], marker='*', color='limegreen', s=200, label='Maximum Sharpe Ratio')
    plt.xlabel('Volatility (Risk)')
    plt.ylabel('Expected Return')
    plt.title('Efficient Frontier with Asset Risk/Return')
    plt.legend()
    plt.tight_layout()
    today = datetime.now().strftime('%Y-%m-%d')
    reports_dir = 'reports'
    os.makedirs(reports_dir, exist_ok=True)
    plot_path = os.path.join(reports_dir, f"efficient_frontier_labeled_{today}.png")
    plt.savefig(plot_path, dpi=200)
    plt.show()

def plot_correlation_matrix(returns_matrix):
    corr = returns_matrix.corr()
    print("Correlation Matrix:")
    print(corr)
    plt.figure(figsize=(8,6))
    sns.heatmap(corr, annot=True, cmap='coolwarm')
    plt.title("Asset Return Correlation Matrix")
    plt.show()

def bootstrap_ci(data, n_bootstrap=1000, ci=95):
    means = [np.mean(np.random.choice(data, size=len(data), replace=True)) for _ in range(n_bootstrap)]
    lower = np.percentile(means, (100-ci)/2)
    upper = np.percentile(means, 100-(100-ci)/2)
    return lower, upper

# Portfolio-level technical analysis plot
def plot_portfolio_analysis(results, filename, start_date=None, end_date=None):
    # Filter out assets with no data in the full-year window
    filtered_results = []
    for res in results:
        df = res['df']
        buy_points = res['buy_points']
        sell_points = res['sell_points']
        # Convert index to naive for comparison
        df_naive = df.copy()
        df_naive.index = df_naive.index.tz_localize(None) if hasattr(df_naive.index, 'tz') and df_naive.index.tz is not None else df_naive.index
        # Reindex buy/sell points to match df_naive
        buy_points_naive = buy_points.reindex(df_naive.index, fill_value=False)
        sell_points_naive = sell_points.reindex(df_naive.index, fill_value=False)
        # Check if any data falls within the [start_date, end_date] window
        if start_date is not None and end_date is not None:
            df_window = df_naive[(df_naive.index >= start_date) & (df_naive.index <= end_date)]
            if df_window.empty:
                continue  # Skip this asset
        filtered_results.append((res, df_naive, buy_points_naive, sell_points_naive))
    n = len(filtered_results)
    fig, axes = plt.subplots(n, 1, figsize=(16, 4*n), sharex=False)
    if n == 1:
        axes = [axes]
    for ax, (res, df_naive, buy_points_naive, sell_points_naive) in zip(axes, filtered_results):
        ticker = res['ticker']
        # data_start = res.get('data_start', df_naive.index.min())
        # data_end = res.get('data_end', df_naive.index.max())
        ax.plot(df_naive.index, df_naive['Close'], label='Close Price', color='k')
        ax.plot(df_naive.index, df_naive['SMA_50'], label='50-day SMA', color='orange', linestyle='--')
        ax.plot(df_naive.index, df_naive['SMA_200'], label='200-day SMA', color='purple', linestyle='--')
        ax.scatter(df_naive.index[buy_points_naive], df_naive['Close'][buy_points_naive], marker='^', color='g', label='Buy', s=80, zorder=5)
        ax.scatter(df_naive.index[sell_points_naive], df_naive['Close'][sell_points_naive], marker='v', color='r', label='Sell', s=80, zorder=5)
        ax.set_title(f"{ticker} | 1y | Sharpe: {res['sharpe']:.2f} | B&H: {res['buy_hold_return']:.2f}% | Signal: {res['signal']}")
        ax.legend()
        ax.grid(True)

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()
