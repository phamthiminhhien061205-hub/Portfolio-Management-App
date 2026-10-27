from fastapi import FastAPI, HTTPException
import yfinance as yf

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