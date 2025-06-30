"""
Investment Planning Project - Configuration Management
Centralized configuration for all screening parameters and settings
"""

import os
from datetime import datetime, timedelta

class Config:
    """Centralized configuration for investment screening project"""
    
    # === SCREENING PARAMETERS ===
    TOP_SELECTED = 30
    FINAL_TOP_N = 10
    
    # === DATA PERIODS ===
    FUNDAMENTAL_PERIOD = "1y"
    RETURNS_PERIOD = "1y"
    TECHNICAL_PERIOD_DAYS = 365
    
    # === TECHNICAL ANALYSIS ===
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    SMA_SHORT = 20
    SMA_MEDIUM = 50
    SMA_LONG = 200
    
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Volume analysis
    VOLUME_RATIO_THRESHOLD = 1.25
    
    # === RISK MANAGEMENT ===
    STOP_LOSS_PCT = 0.05
    TAKE_PROFIT_PCT = 0.10
    RISK_FREE_RATE = 0.05
    
    # Filtering thresholds
    MIN_SHARPE_RATIO = 0.7
    MAX_DRAWDOWN_PCT = 0.4  # 40%
    MIN_TRADING_DAYS = 200
    MAX_MISSING_DATA_PCT = 0.1  # 10%
    
    # === FILE PATHS ===
    ASSETS_FILE = 'assets_for_first_screening.txt'
    TOP_CANDIDATES_FILE = 'assets_top_for_refactor_screening.txt'
    TEMPORAL_ASSETS_FILE = 'assets_temporal.txt'
    REPORTS_DIR = 'reports'
    CACHE_DIR = 'cache'
    
    # === PORTFOLIO OPTIMIZATION ===
    PORTFOLIO_WEIGHTS = {
        'value': 0.3,
        'growth': 0.25,
        'quality': 0.25,
        'momentum': 0.2
    }
    
    NUM_MONTE_CARLO_PORTFOLIOS = 5000
    
    # === PERFORMANCE SETTINGS ===
    MAX_PARALLEL_WORKERS = None  # Will use CPU count
    CACHE_MAX_AGE_DAYS = 1
    
    # === REPORTING ===
    REPORT_DPI = 300
    FIGURE_SIZE = (16, 12)
    
    # === VALIDATION SETTINGS ===
    MIN_PE_RATIO = 1.0
    MAX_PE_RATIO = 100.0
    MIN_PB_RATIO = 0.1
    MAX_PB_RATIO = 20.0
    
    @classmethod
    def get_date_range(cls):
        """Get standardized date range for analysis"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=cls.TECHNICAL_PERIOD_DAYS)
        return start_date, end_date
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Validate configuration parameters"""
        assert cls.TOP_SELECTED > 0, "TOP_SELECTED must be positive"
        assert cls.FINAL_TOP_N <= cls.TOP_SELECTED, "FINAL_TOP_N must be <= TOP_SELECTED"
        assert 0 < cls.STOP_LOSS_PCT < 1, "STOP_LOSS_PCT must be between 0 and 1"
        assert 0 < cls.TAKE_PROFIT_PCT < 1, "TAKE_PROFIT_PCT must be between 0 and 1"
        assert sum(cls.PORTFOLIO_WEIGHTS.values()) == 1.0, "Portfolio weights must sum to 1.0"
        
        # Validate file existence
        if not os.path.exists(cls.ASSETS_FILE):
            raise FileNotFoundError(f"Assets file not found: {cls.ASSETS_FILE}")
    
    @classmethod
    def get_yfinance_period(cls, period_type='fundamental'):
        """Get period string for yfinance API"""
        period_map = {
            'fundamental': cls.FUNDAMENTAL_PERIOD,
            'returns': cls.RETURNS_PERIOD
        }
        return period_map.get(period_type, '1y')


# Environment-specific overrides (for development, testing, production)
class DevelopmentConfig(Config):
    """Development environment configuration"""
    TOP_SELECTED = 10  # Smaller dataset for faster testing
    FINAL_TOP_N = 5
    CACHE_MAX_AGE_DAYS = 0.1  # 2.4 hours
    
class TestingConfig(Config):
    """Testing environment configuration"""
    TOP_SELECTED = 5
    FINAL_TOP_N = 3
    CACHE_DIR = 'test_cache'
    REPORTS_DIR = 'test_reports'
    
class ProductionConfig(Config):
    """Production environment configuration"""
    pass  # Use base Config settings

# Configuration factory
def get_config(env='development'):
    """Get configuration based on environment"""
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }
    
    config_class = config_map.get(env.lower(), DevelopmentConfig)
    config_class.validate_config()
    config_class.create_directories()
    
    return config_class