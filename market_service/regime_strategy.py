
"""Regime Switching Strategy Backtest."""

import numpy as np
import pandas as pd

from exposure_functions import get_close


def backtest_regime_strategy(
    weights,
    benchmark="SPY",
    period="2y",
    bull_exposure=1.0,
    bear_exposure=0.25,
    sideways_exposure=0.6,
    cost_bps=5.0
):
    if not weights:
        raise ValueError("Portfolio is empty")

    weights = {
        str(k).strip().upper(): float(v)
        for k, v in weights.items()
    }

    if any(
        not k or not np.isfinite(v) or v < 0
        for k, v in weights.items()
    ):
        raise ValueError("Invalid tickers or weights")

    if not np.isclose(sum(weights.values()), 1.0, atol=1e-6):
        raise ValueError("Weights must sum to 1")

    exposures = {
        "Bull": float(bull_exposure),
        "Bear": float(bear_exposure),
        "Sideways": float(sideways_exposure)
    }

    if any(
        not np.isfinite(x) or x < 0 or x > 1
        for x in exposures.values()
    ):
        raise ValueError("Exposures must be between 0 and 1")

    if not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("Invalid transaction cost")

    benchmark = benchmark.strip().upper()
    symbols = list(dict.fromkeys([*weights, benchmark]))

    prices = pd.concat(
        [get_close(t, period) for t in symbols],
        axis=1,
        join="inner"
    ).dropna().sort_index()

    if len(prices) < 202:
        raise ValueError(
            "At least 202 aligned trading days are required"
        )

    market = prices[benchmark]

    sma50 = market.rolling(50).mean()
    sma200 = market.rolling(200).mean()
    mom20 = market.pct_change(20)

    state = pd.Series(
        np.select(
            [
                (market > sma50)
                & (sma50 > sma200)
                & (mom20 > 0),

                (market < sma50)
                & (sma50 < sma200)
                & (mom20 < 0)
            ],
            ["Bull", "Bear"],
            default="Sideways"
        ),
        index=prices.index
    )

    returns = prices.pct_change()

    base = sum(
        returns[t] * w
        for t, w in weights.items()
    )

    # Dung tin hieu phien truoc, tranh look-ahead bias
    held_exposure = state.map(exposures).shift(1)

    sample = pd.DataFrame({
        "regime": state,
        "exposure": held_exposure,
        "portfolio_return": base,
        "benchmark_return": returns[benchmark]
    }).iloc[200:].dropna()

    # Phi thay doi ty trong dau tu
    turnover = sample["exposure"].diff().abs()
    turnover.iloc[0] = abs(sample["exposure"].iloc[0])

    sample["strategy_return"] = (
        sample["portfolio_return"] * sample["exposure"]
        - turnover * cost_bps / 10000
    )

    for key, col in [
        ("base", "portfolio_return"),
        ("strategy", "strategy_return"),
        ("benchmark", "benchmark_return")
    ]:
        sample[f"{key}_equity"] = (
            1 + sample[col]
        ).cumprod()

    def metrics(column, equity):
        r = sample[column]
        curve = sample[equity]

        vol = float(r.std() * np.sqrt(252))

        return {
            "total_return_pct": round(
                float((curve.iloc[-1] - 1) * 100), 3
            ),
            "annualized_volatility_pct": round(
                vol * 100, 3
            ),
            "max_drawdown_pct": round(
                float(
                    ((curve / curve.cummax()) - 1).min() * 100
                ), 3
            )
        }

    records = sample.reset_index().rename(
        columns={sample.index.name or "index": "date"}
    )

    records["date"] = pd.to_datetime(
        records["date"]
    ).dt.strftime("%Y-%m-%d")

    return {
        "benchmark": benchmark,
        "period": period,
        "exposure_rules": exposures,
        "cost_bps": cost_bps,
        "sessions": len(sample),
        "metrics": {
            "base": metrics(
                "portfolio_return", "base_equity"
            ),
            "strategy": metrics(
                "strategy_return", "strategy_equity"
            ),
            "benchmark": metrics(
                "benchmark_return", "benchmark_equity"
            )
        },
        "history": records[
            [
                "date",
                "regime",
                "exposure",
                "base_equity",
                "strategy_equity",
                "benchmark_equity"
            ]
        ].to_dict("records"),
        "assumptions": (
            "Prior-close regime signal; daily target-weight "
            "rebalancing; idle capital earns 0%; "
            "allocation-change costs only; no taxes/slippage."
        )
    }
