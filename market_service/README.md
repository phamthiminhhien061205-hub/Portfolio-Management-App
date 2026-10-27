
# Market Service – Portfolio Management App

## 1. Overview
Market Service provides stock market data through REST APIs built with FastAPI.

## 2. Technologies
- Python 3.12
- FastAPI
- Uvicorn
- yfinance
- pandas
- ta
- Docker & Docker Compose

## 3. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | / | Service health message |
| GET | /market/stock/{ticker} | Stock price and market information |
| GET | /market/history/{ticker} | Historical OHLCV data |
| GET | /market/indicators/{ticker} | Technical indicators and metrics |

## 4. Run with Docker

From the project root:

```bash
docker compose up -d --build market-service
```

Check container status:

```bash
docker compose ps
```

## 5. API Documentation

Swagger UI:

http://localhost:8002/docs

## 6. Example Requests

```text
GET /market/stock/AAPL
GET /market/history/AAPL?period=1mo&interval=1d
GET /market/indicators/AAPL?period=3mo&interval=1d
```

## 7. Error Handling

Invalid or unavailable stock ticker:

HTTP 404

```json
{
  "detail": "Stock data not found"
}
```

## 8. Testing

Verified:
- Service startup
- Stock market data retrieval
- Historical stock data retrieval
- Technical indicators (SMA20, EMA20)
- Invalid ticker error handling

## 9. Git Branch

market-service
