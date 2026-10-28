import os
import threading
import time

import numpy as np
import pandas as pd
import yfinance as yf


# ---- Cache giá Yahoo trong bộ nhớ (TTL) ----------------------------------------------
# Mỗi lần phân tích gọi nhiều endpoint, cùng một (ticker, period) bị tải lại nhiều lần.
# Cache giúp nhanh hơn và giảm nguy cơ Yahoo chặn vì gọi quá nhiều.
# MARKET_CACHE_TTL: số giây giữ cache (mặc định 300 = 5 phút; đặt 0 để tắt).
CACHE_TTL_SECONDS = float(os.getenv('MARKET_CACHE_TTL', '300'))
CACHE_MAX_ENTRIES = 256
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()


def clear_price_cache() -> int:
    """Xoá toàn bộ cache, trả về số mục đã xoá."""
    with _CACHE_LOCK:
        n = len(_CACHE)
        _CACHE.clear()
    return n


def cache_info() -> dict:
    now = time.time()
    with _CACHE_LOCK:
        live = sum(1 for ts, _ in _CACHE.values() if now - ts < CACHE_TTL_SECONDS)
        return {'ttl_seconds': CACHE_TTL_SECONDS, 'entries': len(_CACHE), 'fresh_entries': live,
                'keys': sorted(f'{t}:{p}' for t, p in _CACHE)}


def get_close(ticker: str, period: str = '2y') -> pd.Series:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError('Ticker cannot be empty')
    key = (ticker, period)
    if CACHE_TTL_SECONDS > 0:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1].copy()          # copy: nơi gọi có sửa cũng không làm hỏng cache
    data = yf.download(ticker, period=period, interval='1d', auto_adjust=True,
                       progress=False, multi_level_index=False)
    if data.empty or 'Close' not in data:
        raise ValueError(f'No price data for {ticker}')
    close = pd.to_numeric(data['Close'], errors='coerce').dropna()
    if close.empty:
        raise ValueError(f'No valid close prices for {ticker}')
    close.name = ticker
    if CACHE_TTL_SECONDS > 0:               # chỉ cache khi thành công
        with _CACHE_LOCK:
            if len(_CACHE) >= CACHE_MAX_ENTRIES:
                _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]))
            _CACHE[key] = (time.time(), close.copy())
    return close


def calculate_beta(ticker: str, benchmark: str = 'SPY', period: str = '2y',
                   risk_free_rate: float = 0.04) -> dict:
    if not np.isfinite(risk_free_rate):
        raise ValueError('risk_free_rate must be finite')
    ticker, benchmark = ticker.upper(), benchmark.upper()
    prices = pd.concat([get_close(ticker, period), get_close(benchmark, period)], axis=1,
                       join='inner').dropna()
    prices.columns = ['asset', 'market']
    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError('At least 30 aligned daily returns are required')
    market_variance = returns['market'].var()
    if market_variance <= 0 or not np.isfinite(market_variance):
        raise ValueError('Benchmark variance is zero or invalid')
    beta = float(returns['asset'].cov(returns['market']) / market_variance)
    market_annual_return = float((prices['market'].iloc[-1] / prices['market'].iloc[0]) ** (252 / len(returns)) - 1)
    capm = risk_free_rate + beta * (market_annual_return - risk_free_rate)
    return {'ticker': ticker, 'benchmark': benchmark, 'period': period,
            'observations': len(returns), 'beta': beta,
            'risk_free_rate': risk_free_rate,
            'market_annual_return': market_annual_return,
            'capm_expected_return': float(capm)}


def calculate_momentum(ticker: str, period: str = '1y', lookback: int = 20) -> dict:
    if lookback < 1:
        raise ValueError('lookback must be positive')
    close = get_close(ticker, period)
    if len(close) <= lookback:
        raise ValueError(f'At least {lookback + 1} closing prices are required')
    value = float((close.iloc[-1] / close.iloc[-lookback - 1] - 1) * 100)
    return {'ticker': ticker.upper(), 'lookback_days': lookback,
            'momentum_pct': value,
            'signal': 'Positive' if value > 0 else 'Negative' if value < 0 else 'Neutral'}


def calculate_regime(ticker: str = 'SPY', period: str = '2y') -> dict:
    close = get_close(ticker, period)
    if len(close) < 200:
        raise ValueError('At least 200 trading days are required for SMA200')
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    last = float(close.iloc[-1])
    s20, s50, s200 = float(sma20.iloc[-1]), float(sma50.iloc[-1]), float(sma200.iloc[-1])
    mom20 = float((last / close.iloc[-21] - 1) * 100)
    if last > s50 > s200 and mom20 > 0:
        regime = 'Bull'
    elif last < s50 < s200 and mom20 < 0:
        regime = 'Bear'
    else:
        regime = 'Sideways'
    return {'ticker': ticker.upper(), 'last_close': last,
            'SMA_20': s20, 'SMA_50': s50, 'SMA_200': s200,
            'momentum_20d_pct': mom20, 'regime': regime,
            'rule': 'Bull: price>SMA50>SMA200 and momentum>0; Bear: price<SMA50<SMA200 and momentum<0; otherwise Sideways'}


def calculate_portfolio_exposure(weights: dict[str, float], benchmark: str = 'SPY',
                                 period: str = '2y') -> dict:
    if not weights:
        raise ValueError('Portfolio must contain at least one asset')
    if any(not np.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError('Weights must be finite and nonnegative')
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError('Portfolio weights must sum to 1.0')
    if len({k.upper() for k in weights}) != len(weights):
        raise ValueError('Duplicate tickers')
    benchmark = benchmark.upper()
    tickers = {t.upper(): w for t, w in weights.items()}
    series = [get_close(t, period) for t in tickers]
    market = get_close(benchmark, period)
    prices = pd.concat(series + [market], axis=1, join='inner').dropna()
    prices.columns = list(tickers) + ['__benchmark__']
    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError('At least 30 aligned daily returns are required')
    variance = returns['__benchmark__'].var()
    if variance <= 0 or not np.isfinite(variance):
        raise ValueError('Invalid benchmark variance')
    components = []
    for ticker, weight in tickers.items():
        beta = float(returns[ticker].cov(returns['__benchmark__']) / variance)
        components.append({'ticker': ticker, 'weight': weight, 'beta': beta,
                           'weighted_beta': weight * beta})
    portfolio_beta = sum(c['weighted_beta'] for c in components)
    return {'benchmark': benchmark, 'period': period, 'observations': len(returns),
            'portfolio_beta': portfolio_beta, 'components': components,
            'market_sensitivity': 'High' if portfolio_beta >= 1.2 else 'Moderate' if portfolio_beta >= 0.8 else 'Low',
            'note': 'Beta describes historical linear market sensitivity, not a guaranteed forecast.'}


def calculate_rolling_beta(
    ticker: str,
    benchmark: str = "SPY",
    period: str = "2y",
    window: int = 60
):
    if window < 20:
        raise ValueError("Window must be at least 20")

    prices = pd.concat(
        [
            get_close(ticker, period),
            get_close(benchmark, period)
        ],
        axis=1,
        join="inner"
    ).dropna()

    prices.columns = ["asset", "market"]
    returns = prices.pct_change().dropna()

    if len(returns) < window:
        raise ValueError("Not enough data for rolling beta")

    covariance = returns["asset"].rolling(window).cov(
        returns["market"]
    )
    variance = returns["market"].rolling(window).var()

    rolling_beta = (covariance / variance.replace(0, np.nan))
    rolling_beta = rolling_beta.replace(
        [np.inf, -np.inf], np.nan
    ).dropna()

    return {
        "ticker": ticker.upper(),
        "benchmark": benchmark.upper(),
        "window": window,
        "data": [
            {
                "date": date.strftime("%Y-%m-%d"),
                "beta": float(value)
            }
            for date, value in rolling_beta.items()
        ]
    }


import numpy as np
import pandas as pd
import yfinance as yf


def historical_market_regime(
    weights,
    benchmark="SPY",
    period="2y"
):
    if not weights:
        raise ValueError("Danh mục không được rỗng")

    weights = {k.upper(): float(v) for k, v in weights.items()}

    if any(v < 0 for v in weights.values()):
        raise ValueError("Tỷ trọng không được âm")

    if not np.isclose(sum(weights.values()), 1.0):
        raise ValueError("Tổng tỷ trọng phải bằng 1")

    tickers = list(set([*weights.keys(), benchmark.upper()]))

    prices = {}
    for ticker in tickers:
        df = yf.Ticker(ticker).history(
            period=period,
            interval="1d",
            auto_adjust=True
        )

        if df.empty:
            raise ValueError(f"Không có dữ liệu: {ticker}")

        prices[ticker] = df["Close"].rename(ticker)

    prices = pd.concat(prices.values(), axis=1)
    prices.index = pd.to_datetime(prices.index, utc=True)
    prices = prices.sort_index().dropna()

    if len(prices) < 201:
        raise ValueError("Cần ít nhất 201 phiên dữ liệu")

    benchmark = benchmark.upper()
    market = prices[benchmark]

    sma50 = market.rolling(50).mean()
    sma200 = market.rolling(200).mean()
    momentum = market.pct_change(20)

    bull = (
        (market > sma50)
        & (sma50 > sma200)
        & (momentum > 0)
    )
    bear = (
        (market < sma50)
        & (sma50 < sma200)
        & (momentum < 0)
    )

    regime = pd.Series(
        np.select(
            [bull, bear],
            ["Bull", "Bear"],
            default="Sideways"
        ),
        index=prices.index
    )

    returns = prices.pct_change()

    # Danh mục tái cân bằng về tỷ trọng mục tiêu mỗi phiên
    portfolio_returns = sum(
        returns[ticker] * weight
        for ticker, weight in weights.items()
    )

    result = pd.DataFrame({
        "close": market,
        "sma50": sma50,
        "sma200": sma200,
        "momentum20": momentum,
        "regime": regime,
        "portfolio_return": portfolio_returns,
        "benchmark_return": returns[benchmark]
    }).iloc[200:].dropna()

    if result.empty:
        raise ValueError("Không đủ dữ liệu sau khi tính SMA200")

    summary = []
    for state in ["Bull", "Bear", "Sideways"]:
        subset = result[result["regime"] == state]
        count = len(subset)

        summary.append({
            "regime": state,
            "sessions": count,
            "percentage": round(
                count / len(result) * 100, 2
            ),
            "avg_portfolio_return_pct": round(
                subset["portfolio_return"].mean() * 100, 4
            ) if count else None,
            "avg_benchmark_return_pct": round(
                subset["benchmark_return"].mean() * 100, 4
            ) if count else None
        })

    result = result.reset_index()
    result = result.rename(
        columns={result.columns[0]: "date"}
    )
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")

    return {
        "benchmark": benchmark,
        "period": period,
        "current_regime": result["regime"].iloc[-1],
        "summary": summary,
        "history": result.replace(
            {np.nan: None}
        ).to_dict(orient="records")
    }
