# Investment Planning & Asset Screening Project

A comprehensive Python-based investment analysis system that implements multi-stage screening to identify undervalued assets and optimize portfolios.

## 🎯 Project Overview

This project implements a sophisticated investment screening workflow:

1. **Initial Screening** (~100+ assets) → **Top 30 candidates** → **Multi-factor analysis** → **Top 10 selections**
2. **Fundamental Analysis**: P/E, P/B, Debt/Equity, EPS Growth
3. **Technical Analysis**: RSI, MACD, SMA, Volume analysis
4. **Portfolio Optimization**: Sharpe ratio maximization
5. **Backtesting & Performance Evaluation**

## 🏗️ Project Structure

```
invest_planning/
├── config.py                    # Centralized configuration
├── custom_functions.py          # Technical analysis utilities
├── find_undervalued_assets.py   # Main fundamental screening
├── multi_factor_screener.py     # Multi-factor technical screening
├── assets_comparison.ipynb      # Interactive analysis notebook
├── requirements.txt             # Dependencies
├── assets_for_first_screening.txt  # Initial asset list (~100+ tickers)
├── assets_top_for_refactor_screening.txt  # Top 30 candidates
├── assets_temporal.txt          # Sample assets for testing
├── reports/                     # Generated analysis reports
└── cache/                       # Data cache (auto-created)
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd invest_planning

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

The project uses centralized configuration in `config.py`. Key parameters:

- `TOP_SELECTED = 30`: Number of top candidates from initial screening
- `FINAL_TOP_N = 10`: Final number of selections
- `MIN_SHARPE_RATIO = 0.7`: Minimum Sharpe ratio threshold
- `RISK_FREE_RATE = 0.05`: Risk-free rate for calculations

### 3. Running the Analysis

#### Option A: Complete Workflow
```bash
# Step 1: Initial fundamental screening
python find_undervalued_assets.py

# Step 2: Multi-factor technical screening
python multi_factor_screener.py
```

#### Option B: Interactive Analysis
```bash
# Launch Jupyter notebook for interactive analysis
jupyter notebook assets_comparison.ipynb
```

### 4. View Results

Results are automatically saved to the `reports/` directory:
- `undervalued_assets_report_YYYY-MM-DD.txt`: Fundamental analysis results
- `multi_factor_screener_YYYY-MM-DD.txt`: Technical screening results

## 📊 Key Features

### Fundamental Analysis
- **Value Metrics**: P/E ratio, P/B ratio
- **Growth Metrics**: EPS growth rate
- **Quality Metrics**: Debt-to-Equity ratio
- **Composite Scoring**: Weighted ranking system

### Technical Analysis
- **Momentum Indicators**: RSI, MACD
- **Trend Analysis**: Multiple SMAs (20, 50, 200-day)
- **Volume Analysis**: Volume ratio and confirmation
- **Signal Generation**: Buy/Sell signals with confluence

### Portfolio Optimization
- **Sharpe Ratio Maximization**: Risk-adjusted return optimization
- **Risk Metrics**: VaR, Maximum Drawdown, Volatility
- **Backtesting**: Strategy performance evaluation
- **Weight Allocation**: Optimal portfolio weights

## 🔧 Customization

### Adding New Assets
Edit `assets_for_first_screening.txt` and add ticker symbols (one per line):
```
AAPL
MSFT
GOOGL
```

### Modifying Screening Criteria
Adjust parameters in `config.py`:
```python
class Config:
    TOP_SELECTED = 50        # Increase candidate pool
    MIN_SHARPE_RATIO = 1.0   # Stricter Sharpe requirement
    STOP_LOSS_PCT = 0.03     # Tighter stop-loss
```

### Custom Indicators
Add new indicators in `custom_functions.py`:
```python
def calculate_custom_indicator(df):
    # Your custom technical indicator logic
    return df
```

## 📈 Output Examples

### Fundamental Screening Output
```
Top assets by Scaled Score (sorted):
Ticker  Name           Price    P/E   P/B  Debt/Equity  EPS Growth  Sharpe  Scaled Score
SLB     Schlumberger   45.23   12.5  1.8      0.32         0.15     1.24      2.35
PHM     PulteGroup     89.45   8.9   1.2      0.28         0.22     1.18      2.18
```

### Technical Screening Output
```
Top stocks from screening, multi-factor z-score composite:
Ticker  Name        Price   P/E  EPS Growth   ROE  12m Return  Volatility  Composite
SLB     Schlumberger 45.23  12.5     0.15    0.18      0.24       0.31       1.89
PHM     PulteGroup   89.45   8.9     0.22    0.21      0.18       0.28       1.76
```

## 🧪 Testing

Run tests to ensure code reliability:
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=.
```

## 📋 Development Roadmap

### High Priority
- [ ] Data caching system implementation
- [ ] Enhanced error handling and logging
- [ ] Parallel processing for data fetching
- [ ] Comprehensive unit tests

### Medium Priority
- [ ] Enhanced fundamental metrics (PEG, FCF Yield)
- [ ] Sector-adjusted scoring
- [ ] Risk management improvements
- [ ] Interactive web dashboard

### Advanced Features
- [ ] Machine learning integration
- [ ] ESG scoring
- [ ] Automated scheduling
- [ ] Email/SMS alerts

## ⚠️ Disclaimers

- **Not Financial Advice**: This tool is for educational and research purposes only
- **Market Risk**: All investments carry risk of loss
- **Data Accuracy**: Verify all data independently before making investment decisions
- **Historical Performance**: Past performance does not guarantee future results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [yfinance](https://github.com/ranaroussi/yfinance) for financial data API
- [scikit-learn](https://scikit-learn.org/) for machine learning utilities
- [pandas](https://pandas.pydata.org/) for data manipulation

## 📞 Support

If you encounter issues or have questions:
1. Check the [Issues](../../issues) page
2. Review the troubleshooting section below
3. Create a new issue with detailed information

### Troubleshooting

**Common Issues:**

1. **"No data found for ticker"**
   - Verify ticker symbol is correct
   - Check if ticker is actively traded
   - Ensure internet connection is stable

2. **"Insufficient data after filtering"**
   - Reduce `MIN_SHARPE_RATIO` threshold
   - Increase `TOP_SELECTED` parameter
   - Check data availability for selected period

3. **Memory errors with large datasets**
   - Reduce number of tickers in screening
   - Enable data caching
   - Use parallel processing efficiently

---

**Happy Investing! 📈**