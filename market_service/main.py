from fastapi import FastAPI, HTTPException
import yfinance as yf

from pydantic import BaseModel, Field
from typing import Dict
from math import isfinite

from market_service.exposure_functions import (
    calculate_beta,
    calculate_momentum,
    calculate_regime,
    calculate_portfolio_exposure
)

from market_service.market_functions import (
    fetch_stock_data,
    process_data,
    calculate_metrics,
    add_technical_indicators
)

app = FastAPI(title="Market Service")


@app.get("/")
def home():
    return {"message": "Market Service is running"}


@app.get("/market/stock/{ticker}")
def get_stock(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d")

        if data.empty:
            raise HTTPException(
                status_code=404,
                detail="Stock data not found"
            )

        return {
            "ticker": ticker,
            "last_price": float(data["Close"].iloc[-1]),
            "high": float(data["High"].max()),
            "low": float(data["Low"].min()),
            "volume": int(data["Volume"].sum())
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/market/history/{ticker}")
def get_stock_history(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d"
):
    try:
        data = fetch_stock_data(ticker, period, interval)

        if data.empty:
            raise HTTPException(
                status_code=404,
                detail="Stock data not found"
            )

        data = process_data(data)

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": data.to_dict(orient="records")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/market/indicators/{ticker}")
def get_stock_indicators(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d"
):
    try:
        data = fetch_stock_data(ticker, period, interval)

        if data.empty:
            raise HTTPException(
                status_code=404,
                detail="Stock data not found"
            )

        data = process_data(data)

        last_close, change, pct_change, high, low, volume = calculate_metrics(data)

        data = add_technical_indicators(data)

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "metrics": {
                "last_close": last_close,
                "change": change,
                "pct_change": pct_change,
                "high": high,
                "low": low,
                "volume": volume
            },
            "indicators": {
                "SMA_20": None if data["SMA_20"].isna().iloc[-1] else float(data["SMA_20"].iloc[-1]),
                "EMA_20": None if data["EMA_20"].isna().iloc[-1] else float(data["EMA_20"].iloc[-1])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


class PortfolioRequest(BaseModel):
    weights: Dict[str, float] = Field(
        ...,
        description="Weights as fractions summing to 1.0"
    )
    benchmark: str = "SPY"
    period: str = "2y"


def handle_exposure_error(error):
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(
        status_code=503,
        detail=f"Market data service unavailable: {error}"
    )


@app.get("/market/beta/{ticker}")
def get_beta(
    ticker: str,
    benchmark: str = "SPY",
    period: str = "2y",
    risk_free_rate: float = 0.04
):
    try:
        return calculate_beta(
            ticker, benchmark, period, risk_free_rate
        )
    except Exception as e:
        handle_exposure_error(e)


@app.get("/market/momentum/{ticker}")
def get_momentum(
    ticker: str,
    period: str = "1y",
    lookback: int = 20
):
    try:
        return calculate_momentum(ticker, period, lookback)
    except Exception as e:
        handle_exposure_error(e)


@app.get("/market/regime/{ticker}")
def get_regime(ticker: str, period: str = "2y"):
    try:
        return calculate_regime(ticker, period)
    except Exception as e:
        handle_exposure_error(e)


@app.post("/market/exposure")
def get_portfolio_exposure(request: PortfolioRequest):
    try:
        return calculate_portfolio_exposure(
            request.weights,
            request.benchmark,
            request.period
        )
    except Exception as e:
        handle_exposure_error(e)
