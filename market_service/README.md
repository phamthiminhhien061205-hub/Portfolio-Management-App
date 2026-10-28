# Market Exposure & Regime Analysis

### Portfolio Management App — Market Analytics Microservice

A market analytics and portfolio risk management module developed as part of the **Portfolio Management App** project.

The module provides market exposure analysis, CAPM-based risk metrics, technical indicators, historical market regime detection, portfolio stress testing, and regime-aware strategy backtesting.

It is built using **Python, FastAPI, Streamlit, Yahoo Finance, and Docker**, allowing users to explore market conditions and evaluate portfolio behavior through an interactive dashboard.

---

## 1. Project Objectives

The primary objectives of this module are to:

- Analyze the relationship between individual stocks, portfolios, and the overall market.
- Evaluate systematic risk using CAPM and Beta.
- Identify market trends through technical indicators.
- Classify market conditions into Bull, Bear, and Sideways regimes.
- Examine portfolio performance under different market regimes.
- Simulate market shocks and portfolio losses.
- Implement a regime-aware investment strategy.
- Compare strategy performance against an original portfolio and a market benchmark.

The module focuses on transforming financial market data into interpretable risk indicators and historical investment strategy evaluations.

## 2. Implemented Features

### 2.1. CAPM & Beta Analysis

The module evaluates systematic market risk using the Capital Asset Pricing Model (CAPM).

CAPM Expected Return:

**E(Rᵢ) = Rf + βᵢ × (E(Rm) − Rf)**

Where:

- E(Rᵢ): Expected return of the asset
- Rf: Risk-free rate
- βᵢ: Asset Beta
- E(Rm): Expected market return

Beta measures the sensitivity of asset returns to market movements:

**βᵢ = Cov(Rᵢ, Rm) / Var(Rm)**

This analysis helps users understand how individual securities respond to changes in the overall market.

### 2.2. Portfolio Market Exposure

Portfolio Beta is calculated using the weighted average of individual asset Betas:

**βp = Σ(wᵢ × βᵢ)**

The dashboard supports:

- User-defined portfolio weights
- Individual asset Beta
- Portfolio Beta
- Weighted Beta contribution
- Market exposure visualization

### 2.3. Technical Indicators

The module uses technical indicators to analyze market direction and momentum.

Supported indicators include:

- Simple Moving Average (SMA20)
- Simple Moving Average (SMA50)
- Simple Moving Average (SMA200)
- Exponential Moving Average (EMA20)
- 20-day Price Momentum

These indicators help identify market trends, momentum changes, and potential shifts in market conditions.

### 2.4. Rolling Beta Analysis

Rolling Beta measures how the relationship between portfolio returns and benchmark returns changes over time.

Unlike a single historical Beta estimate, Rolling Beta provides a time-varying view of systematic market risk.

### 2.5. Market Regime Detection

The module classifies market conditions into three categories:

| Market Regime | Description |
|---|---|
| Bull | Positive market trend and momentum |
| Bear | Negative market trend and momentum |
| Sideways | Mixed or inconclusive market conditions |

Historical regime classification uses benchmark price behavior, moving averages, and momentum indicators.

### 2.6. Historical Market Regime Analysis

This feature evaluates portfolio performance across historical market regimes.

The dashboard provides:

- Historical regime visualization
- Benchmark price and moving averages
- Regime distribution
- Portfolio returns by regime
- Benchmark returns by regime
- Comparative performance charts

Users can examine how their portfolio behaves during different market conditions.

### 2.7. Market Stress Testing

The stress testing component estimates the potential impact of hypothetical market movements on a portfolio.

It helps users examine portfolio sensitivity to adverse market scenarios.

Stress test results are scenario-based estimates rather than forecasts of actual future losses.

### 2.8. Regime Switching Strategy

The Regime Switching Strategy dynamically adjusts portfolio equity exposure based on the detected market regime.

Default allocation rules:

| Market Regime | Equity Exposure | Cash Allocation |
|---|---:|---:|
| Bull | 100% | 0% |
| Sideways | 60% | 40% |
| Bear | 25% | 75% |

Users can customize these exposure levels through the Streamlit dashboard.

The strategy uses the previous trading session's regime signal to determine the next session's equity exposure, reducing look-ahead bias.

The current strategy uses fixed portfolio composition and regime-dependent aggregate equity exposure. It does not yet perform stock-level optimal rebalancing.

### 2.9. Strategy Backtesting

The backtesting engine evaluates historical performance using market price data.

Three approaches are compared:

1. Original Portfolio
2. Regime Switching Strategy
3. Market Benchmark (SPY by default)

Performance metrics include:

| Metric | Description |
|---|---|
| Cumulative Return | Total compounded return over the backtest period |
| Annualized Volatility | Annualized standard deviation of daily returns |
| Maximum Drawdown | Largest peak-to-trough decline in portfolio value |
| Equity Curve | Historical cumulative growth of invested capital |

The backtest also supports configurable transaction cost assumptions.

The model assumes daily target-weight portfolio rebalancing, zero interest on idle cash, and transaction costs based on changes in aggregate equity exposure.

## 3. System Architecture

The Market Service follows a modular architecture.

**Streamlit Dashboard → FastAPI REST API → Financial Analytics Functions → Yahoo Finance Data**

### Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Backend Framework | FastAPI |
| Dashboard | Streamlit |
| Market Data | Yahoo Finance / yfinance |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| Deployment | Docker / Docker Compose |

### Main Source Files

```text
market_service/
├── main.py
├── market_functions.py
├── exposure_functions.py
├── regime_strategy.py
├── factor_functions.py
├── test_market_service.py
├── dashboard.py
├── db.py
├── Dockerfile
├── requirements.txt
└── README.md
```

**File Responsibilities**

- `main.py`: FastAPI application and REST endpoints.
- `market_functions.py`: Core market analytics functions.
- `exposure_functions.py`: Portfolio exposure, regime analysis, and risk calculations.
- `regime_strategy.py`: Regime Switching Strategy and historical backtesting.
- `factor_functions.py`: Factor betas (SPY/QQQ/IWM/^VIX), CAPM alpha, Treynor, rolling beta, momentum exposure, RISK ON/OFF.
- `test_market_service.py`: Offline tests with synthetic data.
- `dashboard.py`: Interactive Streamlit dashboard.
- `db.py`: Database-related utilities.
- `Dockerfile`: Container configuration.
- `requirements.txt`: Python dependencies.

## 4. Installation and Setup

### Prerequisites

- Python 3.12 or a compatible version
- Docker Desktop
- Git
- Visual Studio Code
- Internet connection for retrieving market data

### Step 1: Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd Portfolio-Management-App
```

Replace `<YOUR_REPOSITORY_URL>` with the actual GitHub repository URL.

### Step 2: Create a Virtual Environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```powershell
pip install -r market_service/requirements.txt
# (tuỳ chọn) chạy dashboard Streamlit riêng: pip install -r market_service/requirements-dashboard.txt
```

### Step 4: Start the Market Service with Docker

Run the following command from the project root:

```powershell
docker compose up -d --build market-service
```

### Step 5: Access FastAPI Documentation

Open:

http://localhost:8003/docs

### Step 6: Start the Streamlit Dashboard

From the project root:

```powershell
python -m streamlit run market_service/dashboard.py --server.port 8503
```

Open:

http://localhost:8503

## 5. API Documentation

The Market Service provides REST endpoints for financial analytics and portfolio risk evaluation.

### Regime Backtesting Endpoint

**POST `/market/regime-backtest`**

Example request:

```json
{
  "weights": {
    "AAPL": 0.3,
    "MSFT": 0.3,
    "NVDA": 0.2,
    "GOOGL": 0.2
  },
  "benchmark": "SPY",
  "period": "2y",
  "bull_exposure": 1.0,
  "bear_exposure": 0.25,
  "sideways_exposure": 0.6,
  "cost_bps": 5
}
```

The API returns:

- Benchmark and analysis period
- Equity exposure rules
- Number of backtest sessions
- Performance metrics for each strategy
- Historical equity curves
- Market regime information
- Backtest assumptions

Additional endpoints for market analytics and historical regime analysis are available in the FastAPI Swagger documentation.

## 6. Dashboard Overview

The Streamlit dashboard provides an interactive environment for portfolio analysis.

Users can:

- Select a market benchmark.
- Configure the historical data period.
- Define portfolio tickers and weights.
- Set the risk-free rate.
- Run portfolio market exposure analysis.
- Explore technical indicators and historical regimes.
- Evaluate portfolio stress scenarios.
- Configure Regime Switching Strategy parameters.
- Compare backtesting results through interactive charts.

## 7. Backtesting Methodology

The backtesting process follows these steps:

1. Retrieve historical prices for portfolio assets and the benchmark.
2. Align historical trading dates.
3. Calculate daily asset and benchmark returns.
4. Calculate SMA50, SMA200, and 20-day momentum.
5. Classify historical market regimes.
6. Shift regime signals by one trading session to prevent look-ahead bias.
7. Determine the equity exposure for each session.
8. Apply simplified transaction cost assumptions.
9. Calculate cumulative portfolio values.
10. Compare performance metrics across strategies.

### Model Assumptions and Limitations

- Historical returns do not guarantee future performance.
- Market regimes are estimated using technical indicators.
- The strategy does not forecast future market conditions.
- Idle cash earns zero interest.
- Transaction costs are simplified.
- Taxes, execution slippage, and full stock-level trading costs are not modeled.
- Results depend on the selected assets, time period, and market conditions.

## 8. Future Development

Planned enhancements include:

### Concentration-Aware Portfolio Risk

- Asset correlation analysis
- Portfolio concentration metrics
- Risk contribution by asset
- Effective Number of Bets

### Multi-Factor Exposure Analytics

- SPY market factor
- QQQ growth/technology proxy
- IWM small-cap proxy
- VIX volatility indicator
- CAPM Alpha and Rolling Factor Exposure

### Intelligent Portfolio Rebalancing

- Regime-aware allocation recommendations
- Portfolio concentration constraints
- Risk-based portfolio optimization
- Before-and-after portfolio comparison

### Advanced Backtesting

- Additional investment strategies
- Sharpe Ratio and Sortino Ratio
- Risk-adjusted performance comparison
- Transaction-cost sensitivity analysis
- Out-of-sample testing

### Intelligent Risk Alerts

- High-Beta warnings
- Portfolio concentration alerts
- Drawdown threshold alerts
- Market regime transition notifications

## 9. Academic Context

This module is developed as an extension of a Portfolio Management App project for academic study and demonstration.

It applies concepts from:

- Financial Portfolio Management
- Capital Asset Pricing Model
- Systematic Risk Analysis
- Technical Market Analysis
- Portfolio Risk Management
- Quantitative Investment Strategies
- Historical Backtesting

The project is intended for educational and research purposes only.

**Disclaimer:** This application does not provide personalized investment advice. All simulations and analyses are subject to data quality, model assumptions, and historical market conditions.


## 9. Microservice integration (group project)

- Service folder: `market_service/` (flat layout; run with `uvicorn main:app --port 8003`).
- Docker: `docker compose up market-service --build` with `build: ./market_service` and port `8003:8003`.
- The Streamlit `dashboard.py` is an optional development tool; the official UI belongs to `frontend/`.

### Endpoints added for the assignment

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/market/factors` | Portfolio factor betas vs SPY/QQQ/IWM/^VIX, CAPM alpha, Treynor, rolling beta (vs SPY), momentum exposure |
| GET | `/market/risk-regime` | RISK ON/OFF (SPY & QQQ > MA200 and VIX < 20) and BULL/NEUTRAL/BEAR regime score |

Example body for `POST /market/factors`:

```json
{"weights": {"AAPL": 0.4, "MSFT": 0.3, "NVDA": 0.3}, "period": "2y", "risk_free_rate": 0.0}
```

Run offline tests: `pip install -r requirements-dev.txt && pytest -q`

### Streamlit UI for the new endpoints (`market_ui.py`)

```powershell
cd market_service
pip install -r requirements-dashboard.txt
streamlit run market_ui.py --server.port 8503
```

Tabs: Factors (betas, CAPM alpha, Treynor, rolling beta, momentum exposure), Risk Regime (RISK ON/OFF + score),
Historical Regime, Regime Backtest. Set `MARKET_API_URL` to change the API address (default `http://127.0.0.1:8003`).

### Regime-switching strategy exactly as in the article

`POST /market/regime-strategy` - BULL = Max Sharpe weights (SLSQP, long-only, max weight 0.5), NEUTRAL = equal weight,
BEAR = cash. Regime = score of trend (MA50>MA200) + momentum (12D) + low volatility (20D vol < 70th percentile) on SPY.
`lag=1` (default) uses the previous session's regime to avoid look-ahead; `lag=0` reproduces the article's same-day logic.
Compared against the static user portfolio and SPY. Requires `scipy`.

### Price cache and rolling alpha

- **Yahoo price cache:** `get_close()` keeps each `(ticker, period)` in memory for `MARKET_CACHE_TTL` seconds
  (default 300; set `0` to disable). `GET /market/cache` shows entries, `DELETE /market/cache` clears them
  (use it to force fresh data). Only successful downloads are cached. `/market/historical-regime` still calls
  Yahoo directly and is not cached.
- **Rolling alpha:** `POST /market/factors` now also returns `rolling_alpha` / `rolling_alpha_latest`
  = (rolling mean of portfolio return - rolling beta x rolling mean of SPY return) x 252 (annualized), window = `rolling_window`.
