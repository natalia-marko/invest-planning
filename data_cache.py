"""
Data Caching System for Investment Analysis
Intelligent caching of financial data with automatic invalidation
"""

import os
import pickle
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import yfinance as yf
from config import Config

class DataCache:
    """
    Intelligent caching system for financial data with automatic invalidation
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_age_days: float = 1.0):
        """
        Initialize the data cache
        
        Args:
            cache_dir: Directory to store cache files (default from config)
            max_age_days: Maximum age of cached data in days
        """
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.max_age = timedelta(days=max_age_days)
        self.fundamental_max_age = timedelta(days=1)  # Fundamentals update less frequently
        self.price_max_age = timedelta(hours=4)  # Price data updates more frequently
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
    
    def _get_cache_path(self, ticker: str, data_type: str, period: Optional[str] = None) -> str:
        """Generate cache file path"""
        if period:
            filename = f"{ticker}_{data_type}_{period}.pkl"
        else:
            filename = f"{ticker}_{data_type}.pkl"
        return os.path.join(self.cache_dir, filename)
    
    def _get_metadata_path(self, ticker: str, data_type: str, period: Optional[str] = None) -> str:
        """Generate metadata file path"""
        if period:
            filename = f"{ticker}_{data_type}_{period}_meta.json"
        else:
            filename = f"{ticker}_{data_type}_meta.json"
        return os.path.join(self.cache_dir, filename)
    
    def _is_cache_valid(self, cache_path: str, data_type: str) -> bool:
        """Check if cached data is still valid"""
        if not os.path.exists(cache_path):
            return False
        
        # Get appropriate max age based on data type
        if data_type == 'fundamentals':
            max_age = self.fundamental_max_age
        elif data_type in ['history', 'prices']:
            max_age = self.price_max_age
        else:
            max_age = self.max_age
        
        # Check file age
        modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - modified_time < max_age
    
    def _save_metadata(self, ticker: str, data_type: str, metadata: Dict, period: Optional[str] = None):
        """Save metadata about cached data"""
        metadata_path = self._get_metadata_path(ticker, data_type, period)
        metadata['cached_at'] = datetime.now().isoformat()
        metadata['ticker'] = ticker
        metadata['data_type'] = data_type
        metadata['period'] = period
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self, ticker: str, data_type: str, period: Optional[str] = None) -> Optional[Dict]:
        """Load metadata about cached data"""
        metadata_path = self._get_metadata_path(ticker, data_type, period)
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def get_stock_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Get stock price history with caching
        
        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            DataFrame with stock price history or None if error
        """
        cache_path = self._get_cache_path(ticker, 'history', period)
        
        # Try to load from cache
        if self._is_cache_valid(cache_path, 'history'):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                    self.stats['hits'] += 1
                    return data
            except Exception as e:
                print(f"Cache read error for {ticker} history: {e}")
                self.stats['errors'] += 1
        
        # Fetch from API
        try:
            self.stats['misses'] += 1
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            if not data.empty:
                # Cache the data
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)
                
                # Save metadata
                metadata = {
                    'rows': len(data),
                    'columns': list(data.columns),
                    'date_range': [data.index.min().isoformat(), data.index.max().isoformat()],
                    'period': period
                }
                self._save_metadata(ticker, 'history', metadata, period)
                
                return data
            else:
                print(f"No history data available for {ticker}")
                return None
                
        except Exception as e:
            print(f"Error fetching history for {ticker}: {e}")
            self.stats['errors'] += 1
            return None
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """
        Get stock fundamental information with caching
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with stock info or None if error
        """
        cache_path = self._get_cache_path(ticker, 'fundamentals')
        
        # Try to load from cache
        if self._is_cache_valid(cache_path, 'fundamentals'):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                    self.stats['hits'] += 1
                    return data
            except Exception as e:
                print(f"Cache read error for {ticker} fundamentals: {e}")
                self.stats['errors'] += 1
        
        # Fetch from API
        try:
            self.stats['misses'] += 1
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info and len(info) > 1:  # Basic validation
                # Cache the data
                with open(cache_path, 'wb') as f:
                    pickle.dump(info, f)
                
                # Save metadata
                metadata = {
                    'keys_count': len(info.keys()),
                    'has_financials': bool(info.get('trailingPE')),
                    'company_name': info.get('shortName', 'Unknown'),
                    'sector': info.get('sector', 'Unknown'),
                    'market_cap': info.get('marketCap', 0)
                }
                self._save_metadata(ticker, 'fundamentals', metadata)
                
                return info
            else:
                print(f"No fundamental data available for {ticker}")
                return None
                
        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")
            self.stats['errors'] += 1
            return None
    
    def get_multiple_stocks_data(self, tickers: list, period: str = "1y") -> Dict[str, Dict]:
        """
        Get data for multiple stocks efficiently
        
        Args:
            tickers: List of ticker symbols
            period: Time period for historical data
            
        Returns:
            Dictionary with ticker as key and data dict as value
        """
        results = {}
        
        for ticker in tickers:
            ticker_data = {
                'history': self.get_stock_history(ticker, period),
                'info': self.get_stock_info(ticker)
            }
            
            # Only include if we have at least one type of data
            if ticker_data['history'] is not None or ticker_data['info'] is not None:
                results[ticker] = ticker_data
        
        return results
    
    def invalidate_ticker(self, ticker: str):
        """Remove all cached data for a specific ticker"""
        files_removed = 0
        
        for file in os.listdir(self.cache_dir):
            if file.startswith(f"{ticker}_"):
                file_path = os.path.join(self.cache_dir, file)
                try:
                    os.remove(file_path)
                    files_removed += 1
                except Exception as e:
                    print(f"Error removing cache file {file}: {e}")
        
        print(f"Removed {files_removed} cache files for {ticker}")
    
    def invalidate_all(self):
        """Remove all cached data"""
        files_removed = 0
        
        for file in os.listdir(self.cache_dir):
            if file.endswith(('.pkl', '.json')):
                file_path = os.path.join(self.cache_dir, file)
                try:
                    os.remove(file_path)
                    files_removed += 1
                except Exception as e:
                    print(f"Error removing cache file {file}: {e}")
        
        print(f"Removed {files_removed} cache files")
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_requests = self.stats['hits'] + self.stats['misses'] + self.stats['errors']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'errors': self.stats['errors'],
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def get_cache_info(self) -> Dict:
        """Get information about cached data"""
        cache_info = {
            'cache_directory': self.cache_dir,
            'total_files': 0,
            'total_size_mb': 0,
            'tickers_cached': set(),
            'data_types': set()
        }
        
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    cache_info['total_files'] += 1
                    cache_info['total_size_mb'] += os.path.getsize(file_path) / (1024 * 1024)
                    
                    # Extract ticker and data type from filename
                    if '_' in file and file.endswith(('.pkl', '.json')):
                        parts = file.split('_')
                        ticker = parts[0]
                        data_type = parts[1] if len(parts) > 1 else 'unknown'
                        
                        cache_info['tickers_cached'].add(ticker)
                        cache_info['data_types'].add(data_type)
        
        cache_info['tickers_cached'] = list(cache_info['tickers_cached'])
        cache_info['data_types'] = list(cache_info['data_types'])
        cache_info['total_size_mb'] = round(cache_info['total_size_mb'], 2)
        
        return cache_info
    
    def cleanup_old_cache(self, max_age_days: float = 7.0):
        """Remove cache files older than specified age"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        files_removed = 0
        
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if modified_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            files_removed += 1
                        except Exception as e:
                            print(f"Error removing old cache file {file}: {e}")
        
        print(f"Cleaned up {files_removed} old cache files")


# Global cache instance
_cache_instance = None

def get_cache(cache_dir: Optional[str] = None, max_age_days: float = 1.0) -> DataCache:
    """Get or create global cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = DataCache(cache_dir, max_age_days)
    
    return _cache_instance

def clear_global_cache():
    """Clear the global cache instance"""
    global _cache_instance
    _cache_instance = None


# Convenience functions for backward compatibility
def get_stock_data_cached(ticker: str, period: str = "1y") -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
    """
    Get both historical data and fundamental info for a stock
    
    Returns:
        Tuple of (historical_data, fundamental_info)
    """
    cache = get_cache()
    history = cache.get_stock_history(ticker, period)
    info = cache.get_stock_info(ticker)
    return history, info

def get_multiple_stocks_cached(tickers: list, period: str = "1y") -> Dict[str, Dict]:
    """Get data for multiple stocks with caching"""
    cache = get_cache()
    return cache.get_multiple_stocks_data(tickers, period)


if __name__ == "__main__":
    # Test the cache system
    print("Testing Data Cache System...")
    
    # Initialize cache
    cache = DataCache()
    
    # Test with a few tickers
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    print(f"\nFetching data for {test_tickers}...")
    start_time = datetime.now()
    
    data = cache.get_multiple_stocks_data(test_tickers)
    
    end_time = datetime.now()
    print(f"First fetch completed in {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Test cache hit
    print(f"\nFetching same data again (should be cached)...")
    start_time = datetime.now()
    
    data2 = cache.get_multiple_stocks_data(test_tickers)
    
    end_time = datetime.now()
    print(f"Second fetch completed in {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Print cache statistics
    print(f"\nCache Statistics:")
    stats = cache.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Print cache info
    print(f"\nCache Information:")
    info = cache.get_cache_info()
    for key, value in info.items():
        print(f"  {key}: {value}")