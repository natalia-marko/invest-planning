#!/usr/bin/env python3
"""
Cache Management Utility
Manage the investment analysis data cache with various operations
"""

import argparse
import sys
from datetime import datetime
from data_cache import get_cache
from config import get_config

def show_cache_info():
    """Display detailed cache information"""
    cache = get_cache()
    info = cache.get_cache_info()
    stats = cache.get_cache_stats()
    
    print("="*60)
    print("CACHE INFORMATION")
    print("="*60)
    print(f"Cache Directory: {info['cache_directory']}")
    print(f"Total Files: {info['total_files']}")
    print(f"Cache Size: {info['total_size_mb']:.2f} MB")
    print(f"Tickers Cached: {len(info['tickers_cached'])}")
    print(f"Data Types: {', '.join(info['data_types'])}")
    
    print(f"\nPERFORMANCE STATISTICS")
    print(f"Cache Hits: {stats['hits']}")
    print(f"Cache Misses: {stats['misses']}")
    print(f"Errors: {stats['errors']}")
    print(f"Hit Rate: {stats['hit_rate_percent']:.1f}%")
    
    if info['tickers_cached']:
        print(f"\nCACHED TICKERS:")
        # Sort and display in columns
        tickers = sorted(info['tickers_cached'])
        for i in range(0, len(tickers), 5):
            print("  " + "  ".join(f"{ticker:<8}" for ticker in tickers[i:i+5]))

def clear_cache(confirm=True):
    """Clear all cached data"""
    cache = get_cache()
    
    if confirm:
        info = cache.get_cache_info()
        response = input(f"This will delete {info['total_files']} cache files ({info['total_size_mb']:.2f} MB). Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return
    
    cache.invalidate_all()
    print("Cache cleared successfully!")

def clear_ticker(ticker):
    """Clear cached data for a specific ticker"""
    cache = get_cache()
    cache.invalidate_ticker(ticker.upper())
    print(f"Cleared cache for {ticker.upper()}")

def cleanup_old_cache(days=7):
    """Remove cache files older than specified days"""
    cache = get_cache()
    cache.cleanup_old_cache(days)
    print(f"Cleaned up cache files older than {days} days")

def test_cache_performance():
    """Test cache performance with sample tickers"""
    print("Testing cache performance...")
    
    # Sample tickers for testing
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    cache = get_cache()
    
    # First run (should mostly miss cache)
    print(f"\nFirst run (fetching {len(test_tickers)} tickers)...")
    start_time = datetime.now()
    
    data = cache.get_multiple_stocks_data(test_tickers)
    
    end_time = datetime.now()
    first_duration = (end_time - start_time).total_seconds()
    
    # Second run (should hit cache)
    print(f"Second run (should use cache)...")
    start_time = datetime.now()
    
    data2 = cache.get_multiple_stocks_data(test_tickers)
    
    end_time = datetime.now()
    second_duration = (end_time - start_time).total_seconds()
    
    # Results
    stats = cache.get_cache_stats()
    print(f"\nPERFORMANCE TEST RESULTS:")
    print(f"First run: {first_duration:.2f} seconds")
    print(f"Second run: {second_duration:.2f} seconds")
    print(f"Speed improvement: {first_duration/second_duration:.1f}x faster")
    print(f"Time saved: {first_duration - second_duration:.2f} seconds")
    print(f"Cache hit rate: {stats['hit_rate_percent']:.1f}%")

def warm_up_cache(ticker_file=None):
    """Pre-populate cache with tickers from file"""
    config = get_config()
    cache = get_cache()
    
    if ticker_file is None:
        ticker_file = config.ASSETS_FILE
    
    try:
        with open(ticker_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File {ticker_file} not found")
        return
    
    print(f"Warming up cache with {len(tickers)} tickers from {ticker_file}...")
    
    # Fetch data for all tickers to populate cache
    data = cache.get_multiple_stocks_data(tickers[:20])  # Limit to first 20 to avoid rate limits
    
    stats = cache.get_cache_stats()
    info = cache.get_cache_info()
    print(f"Cache warm-up completed!")
    print(f"Cached {len(data)} tickers successfully")
    print(f"Cache size: {info['total_size_mb']:.2f} MB")

def main():
    parser = argparse.ArgumentParser(description="Investment Analysis Cache Manager")
    parser.add_argument('action', choices=['info', 'clear', 'clear-ticker', 'cleanup', 'test', 'warmup'],
                       help='Action to perform')
    parser.add_argument('--ticker', type=str, help='Ticker symbol for clear-ticker action')
    parser.add_argument('--days', type=int, default=7, help='Days for cleanup action (default: 7)')
    parser.add_argument('--file', type=str, help='Ticker file for warmup action')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if args.action == 'info':
        show_cache_info()
    elif args.action == 'clear':
        clear_cache(confirm=not args.force)
    elif args.action == 'clear-ticker':
        if not args.ticker:
            print("Error: --ticker required for clear-ticker action")
            sys.exit(1)
        clear_ticker(args.ticker)
    elif args.action == 'cleanup':
        cleanup_old_cache(args.days)
    elif args.action == 'test':
        test_cache_performance()
    elif args.action == 'warmup':
        warm_up_cache(args.file)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)