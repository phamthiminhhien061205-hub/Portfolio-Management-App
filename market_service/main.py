import math
from datetime import date, datetime
from typing import Dict

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from exposure_functions import (
    cache_info,
    clear_price_cache,
    calculate_beta,
    calculate_momentum,
    calculate_portfolio_exposure,
    calculate_regime,
    calculate_rolling_beta,
    historical_market_regime,
)
from market_functions import (
    add_technical_indicators,
    calculate_metrics,
    fetch_stock_data,
    process_data,
)
from factor_functions import (
    backtest_article_regime_strategy,
    calculate_benchmark_comparison,
    calculate_factor_analytics,
    calculate_risk_regime,
)
from regime_strategy import backtest_regime_strategy

app = FastAPI(title="Market Service")


def clean_json_values(value):
    """Convert pandas/NumPy values into JSON-safe Python values."""
    if value is None or value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, dict):
        return {str(k): clean_json_values(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json_values(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat() if not np.isnat(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return clean_json_values(value.tolist())
    return value


def handle_exposure_error(error):
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(
        status_code=503,
        detail=f"Market data service unavailable: {error}",
    )


@app.get("/")
def home():
    return {"message": "Market Service is running"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "market_service"}


@app.get("/market/stock/{ticker}")
def get_stock(ticker: str):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        return clean_json_values({
            "ticker": ticker,
            "last_price": float(data["Close"].iloc[-1]),
            "high": float(data["High"].max()),
            "low": float(data["Low"].min()),
            "volume": int(data["Volume"].sum()),
        })
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/market/history/{ticker}")
def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    try:
        data = fetch_stock_data(ticker, period, interval)
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        data = process_data(data)
        # Missing moving-average values in early rows are represented as JSON null.
        records = data.to_dict(orient="records")
        return clean_json_values({
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": records,
        })
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/market/indicators/{ticker}")
def get_stock_indicators(ticker: str, period: str = "1mo", interval: str = "1d"):
    try:
        data = fetch_stock_data(ticker, period, interval)
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        data = process_data(data)
        last_close, change, pct_change, high, low, volume = calculate_metrics(data)
        data = add_technical_indicators(data)
        return clean_json_values({
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "metrics": {
                "last_close": last_close,
                "change": change,
                "pct_change": pct_change,
                "high": high,
                "low": low,
                "volume": volume,
            },
            "indicators": {
                "SMA_20": data["SMA_20"].iloc[-1],
                "EMA_20": data["EMA_20"].iloc[-1],
            },
        })
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class PortfolioRequest(BaseModel):
    weights: Dict[str, float] = Field(..., description="Weights as fractions summing to 1.0")
    benchmark: str = "SPY"
    period: str = "2y"


@app.get("/market/beta/{ticker}")
def get_beta(ticker: str, benchmark: str = "SPY", period: str = "2y", risk_free_rate: float = 0.04):
    try:
        return clean_json_values(calculate_beta(ticker, benchmark, period, risk_free_rate))
    except Exception as exc:
        handle_exposure_error(exc)


@app.get("/market/momentum/{ticker}")
def get_momentum(ticker: str, period: str = "1y", lookback: int = 20):
    try:
        return clean_json_values(calculate_momentum(ticker, period, lookback))
    except Exception as exc:
        handle_exposure_error(exc)


@app.get("/market/regime/{ticker}")
def get_regime(ticker: str, period: str = "2y"):
    try:
        return clean_json_values(calculate_regime(ticker, period))
    except Exception as exc:
        handle_exposure_error(exc)


@app.post("/market/exposure")
def get_portfolio_exposure(request: PortfolioRequest):
    try:
        return clean_json_values(calculate_portfolio_exposure(request.weights, request.benchmark, request.period))
    except Exception as exc:
        handle_exposure_error(exc)


@app.get("/market/rolling-beta/{ticker}")
def get_rolling_beta(ticker: str, benchmark: str = "SPY", period: str = "2y", window: int = 60):
    try:
        return clean_json_values(calculate_rolling_beta(ticker=ticker, benchmark=benchmark, period=period, window=window))
    except Exception as exc:
        handle_exposure_error(exc)


class HistoricalRegimeRequest(BaseModel):
    weights: Dict[str, float]
    benchmark: str = "SPY"
    period: str = "2y"


@app.post("/market/historical-regime")
def get_historical_regime(payload: HistoricalRegimeRequest):
    try:
        return clean_json_values(historical_market_regime(weights=payload.weights, benchmark=payload.benchmark, period=payload.period))
    except Exception as exc:
        handle_exposure_error(exc)


class RegimeBacktestRequest(BaseModel):
    weights: Dict[str, float]
    benchmark: str = "SPY"
    period: str = "2y"
    bull_exposure: float = Field(default=1.0, ge=0, le=1)
    bear_exposure: float = Field(default=0.25, ge=0, le=1)
    sideways_exposure: float = Field(default=0.6, ge=0, le=1)
    cost_bps: float = Field(default=5.0, ge=0)


@app.post("/market/regime-backtest")
def regime_backtest(payload: RegimeBacktestRequest):
    try:
        return clean_json_values(backtest_regime_strategy(**payload.model_dump()))
    except Exception as exc:
        handle_exposure_error(exc)


class FactorRequest(BaseModel):
    weights: Dict[str, float] = Field(..., description="Weights as fractions summing to 1.0")
    period: str = "2y"
    risk_free_rate: float = 0.0
    rolling_window: int = Field(default=20, ge=5)
    momentum_window: int = Field(default=12, ge=1)
    beta_matrix_window: int = Field(default=60, ge=20)


@app.post("/market/factors")
def get_factor_analytics(payload: FactorRequest):
    """Factor betas (SPY/QQQ/IWM/^VIX), CAPM alpha, Treynor, rolling beta, momentum exposure."""
    try:
        return clean_json_values(calculate_factor_analytics(**payload.model_dump()))
    except Exception as exc:
        handle_exposure_error(exc)


@app.get("/market/risk-regime")
def get_risk_regime(period: str = "2y", vix_threshold: float = 20.0):
    """RISK ON / RISK OFF (SPY, QQQ vs MA200 + VIX) và regime score BULL/NEUTRAL/BEAR."""
    try:
        return clean_json_values(calculate_risk_regime(period, vix_threshold))
    except Exception as exc:
        handle_exposure_error(exc)


class BenchmarkRequest(BaseModel):
    weights: Dict[str, float]
    benchmark: str = "SPY"
    period: str = "2y"


@app.post("/market/benchmark")
def get_benchmark_comparison(payload: BenchmarkRequest):
    """Danh mục vs SPY: total return, alpha, growth, drawdown, rolling volatility."""
    try:
        return clean_json_values(calculate_benchmark_comparison(**payload.model_dump()))
    except Exception as exc:
        handle_exposure_error(exc)


class ArticleStrategyRequest(BaseModel):
    weights: Dict[str, float]
    period: str = "2y"
    max_weight: float = Field(default=0.5, gt=0, le=1)
    lag: int = Field(default=1, ge=0, le=1)


@app.post("/market/regime-strategy")
def regime_strategy_article(payload: ArticleStrategyRequest):
    """Regime switching đúng bài: BULL=Max Sharpe, NEUTRAL=equal weight, BEAR=cash."""
    try:
        return clean_json_values(backtest_article_regime_strategy(**payload.model_dump()))
    except Exception as exc:
        handle_exposure_error(exc)


@app.get("/market/cache")
def get_cache_info():
    """Trạng thái cache giá Yahoo (TTL, số mục, các khoá)."""
    return cache_info()


@app.delete("/market/cache")
def delete_cache():
    """Xoá cache giá để buộc tải lại dữ liệu mới nhất."""
    return {"cleared_entries": clear_price_cache()}
