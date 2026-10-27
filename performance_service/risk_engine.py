import numpy as np
import pandas as pd


TRADING_DAYS = 252
ROLLING_WINDOW = 20
MIN_OBSERVATIONS = 60


# =========================================================
# HELPER
# =========================================================
def percentile_rank(values, current_value):
    """
    Tính percentile tương đối của current_value
    so với chính lịch sử của portfolio.
    """

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return None

    return float(
        np.mean(values < current_value)
    )


# =========================================================
# 1. RELATIVE RISK LEVEL
# =========================================================
def calculate_relative_risk(returns):

    series = pd.Series(
        returns,
        dtype=float
    )

    if len(series) < MIN_OBSERVATIONS:

        return {
            "risk_level": "INSUFFICIENT_DATA",
            "risk_index": None,
            "volatility_percentile": None,
            "drawdown_percentile": None,
            "latest_rolling_volatility": None,
            "methodology": (
                "At least 60 observations are required "
                "for relative historical risk assessment."
            )
        }

    # -------------------------
    # Rolling Volatility
    # -------------------------
    rolling_vol = (
        series
        .rolling(ROLLING_WINDOW)
        .std(ddof=1)
        * np.sqrt(TRADING_DAYS)
    ).dropna()

    latest_vol = float(
        rolling_vol.iloc[-1]
    )

    vol_percentile = percentile_rank(
        rolling_vol.values,
        latest_vol
    )

    # -------------------------
    # Drawdown
    # -------------------------
    cumulative = (
        1 + series
    ).cumprod()

    running_max = cumulative.cummax()

    drawdown = (
        cumulative
        / running_max
        - 1
    )

    drawdown_severity = -drawdown

    current_dd = float(
        drawdown_severity.iloc[-1]
    )

    dd_percentile = percentile_rank(
        drawdown_severity.values,
        current_dd
    )

    # -------------------------
    # Combined Relative Index
    # -------------------------
    risk_index = (
        vol_percentile
        + dd_percentile
    ) / 2

    if risk_index < 1 / 3:
        level = "LOW"

    elif risk_index < 2 / 3:
        level = "MEDIUM"

    else:
        level = "HIGH"

    return {
        "risk_level": level,
        "risk_index": float(risk_index),
        "volatility_percentile": float(
            vol_percentile
        ),
        "drawdown_percentile": float(
            dd_percentile
        ),
        "latest_rolling_volatility": latest_vol,
        "methodology": (
            "Project-specific relative risk level based "
            "on the portfolio's own historical rolling "
            "volatility and drawdown distribution. "
            "This is not an external investment rating."
        )
    }


# =========================================================
# 2. RISK ALERT SYSTEM
# =========================================================
def generate_risk_alerts(
    returns,
    alert_percentile=0.90
):

    series = pd.Series(
        returns,
        dtype=float
    )

    if len(series) < MIN_OBSERVATIONS:

        return [{
            "type": "DATA",
            "severity": "INFO",
            "message": (
                "Not enough observations for "
                "historical anomaly detection."
            )
        }]

    alerts = []

    # -------------------------
    # Volatility Alert
    # -------------------------
    rolling_vol = (
        series
        .rolling(ROLLING_WINDOW)
        .std(ddof=1)
        * np.sqrt(TRADING_DAYS)
    ).dropna()

    current_vol = float(
        rolling_vol.iloc[-1]
    )

    vol_percentile = percentile_rank(
        rolling_vol.values,
        current_vol
    )

    if vol_percentile >= alert_percentile:

        alerts.append({
            "type": "VOLATILITY",
            "severity": "WARNING",
            "message": (
                f"Current rolling volatility is around "
                f"the {vol_percentile * 100:.0f}th "
                f"percentile of this portfolio's "
                f"historical observations."
            )
        })

    # -------------------------
    # Drawdown Alert
    # -------------------------
    cumulative = (
        1 + series
    ).cumprod()

    drawdown = (
        cumulative
        / cumulative.cummax()
        - 1
    )

    severity_series = -drawdown

    current_severity = float(
        severity_series.iloc[-1]
    )

    dd_percentile = percentile_rank(
        severity_series.values,
        current_severity
    )

    if (
        current_severity > 0
        and
        dd_percentile >= alert_percentile
    ):

        alerts.append({
            "type": "DRAWDOWN",
            "severity": "WARNING",
            "message": (
                f"Current drawdown severity is around "
                f"the {dd_percentile * 100:.0f}th "
                f"percentile of historical observations."
            )
        })

    if not alerts:

        alerts.append({
            "type": "SYSTEM",
            "severity": "OK",
            "message": (
                "No major historical risk anomaly "
                "was detected under the current rules."
            )
        })

    return alerts


# =========================================================
# 3. EXPLAINABLE ASSESSMENT
# =========================================================
def explain_portfolio(
    returns,
    total_return,
    volatility,
    sharpe,
    max_drawdown
):

    series = pd.Series(
        returns,
        dtype=float
    )

    insights = []

    # Return
    if total_return >= 0:

        insights.append(
            f"The portfolio gained "
            f"{total_return * 100:.2f}% "
            f"during the observed period."
        )

    else:

        insights.append(
            f"The portfolio lost "
            f"{abs(total_return) * 100:.2f}% "
            f"during the observed period."
        )

    # Volatility
    insights.append(
        f"Annualized volatility is "
        f"{volatility * 100:.2f}%."
    )

    # Sharpe
    if sharpe > 0:

        insights.append(
            "Risk-adjusted performance is positive "
            "under the current Sharpe calculation."
        )

    elif sharpe < 0:

        insights.append(
            "Risk-adjusted performance is negative "
            "under the current Sharpe calculation."
        )

    else:

        insights.append(
            "The current Sharpe Ratio is zero."
        )

    # Drawdown
    insights.append(
        f"The maximum decline from a previous "
        f"portfolio peak was "
        f"{abs(max_drawdown) * 100:.2f}%."
    )

    positive_ratio = float(
        (series > 0).mean()
    )

    insights.append(
        f"{positive_ratio * 100:.1f}% "
        f"of observed sessions generated "
        f"positive returns."
    )

    return insights


# =========================================================
# 4. PORTFOLIO HEALTH SCORE
# =========================================================
def calculate_health_score(returns):

    series = pd.Series(
        returns,
        dtype=float
    )

    if len(series) < MIN_OBSERVATIONS:

        return {
            "score": None,
            "components": None,
            "methodology": (
                "At least 60 observations are required "
                "for Portfolio Health Score."
            )
        }

    # -------------------------
    # Stability
    # -------------------------
    rolling_vol = (
        series
        .rolling(ROLLING_WINDOW)
        .std(ddof=1)
        * np.sqrt(TRADING_DAYS)
    ).dropna()

    latest_vol = float(
        rolling_vol.iloc[-1]
    )

    vol_percentile = percentile_rank(
        rolling_vol.values,
        latest_vol
    )

    stability_score = (
        1 - vol_percentile
    ) * 100

    # -------------------------
    # Drawdown Resilience
    # -------------------------
    cumulative = (
        1 + series
    ).cumprod()

    drawdown = (
        cumulative
        / cumulative.cummax()
        - 1
    )

    severity = -drawdown

    latest_severity = float(
        severity.iloc[-1]
    )

    dd_percentile = percentile_rank(
        severity.values,
        latest_severity
    )

    drawdown_score = (
        1 - dd_percentile
    ) * 100

    # -------------------------
    # Positive-return consistency
    # -------------------------
    consistency_score = float(
        series.gt(0).mean()
        * 100
    )

    # -------------------------
    # Rolling Sharpe Relative Score
    # -------------------------
    rolling_mean = (
        series
        .rolling(ROLLING_WINDOW)
        .mean()
    )

    rolling_std = (
        series
        .rolling(ROLLING_WINDOW)
        .std(ddof=1)
    )

    rolling_sharpe = (
        rolling_mean
        / rolling_std
        * np.sqrt(TRADING_DAYS)
    )

    rolling_sharpe = (
        rolling_sharpe
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
    )

    if len(rolling_sharpe) == 0:

        risk_adjusted_score = 50.0

    else:

        latest_sharpe = float(
            rolling_sharpe.iloc[-1]
        )

        sharpe_percentile = percentile_rank(
            rolling_sharpe.values,
            latest_sharpe
        )

        risk_adjusted_score = (
            sharpe_percentile * 100
        )

    health_score = np.mean([
        stability_score,
        drawdown_score,
        consistency_score,
        risk_adjusted_score
    ])

    return {
        "score": round(
            float(health_score),
            1
        ),

        "components": {
            "stability": round(
                float(stability_score),
                1
            ),

            "drawdown_resilience": round(
                float(drawdown_score),
                1
            ),

            "return_consistency": round(
                float(consistency_score),
                1
            ),

            "risk_adjusted_performance": round(
                float(risk_adjusted_score),
                1
            )
        },

        "methodology": (
            "Internal relative score from 0 to 100. "
            "It combines stability, drawdown resilience, "
            "return consistency and relative "
            "risk-adjusted performance. "
            "This is not an external investment rating."
        )
    }


# =========================================================
# 5. CONCENTRATION RISK
# =========================================================
def concentration_analysis(
    tickers,
    weights,
    position_limit=None
):

    if not tickers or not weights:
        return None

    weights = np.asarray(
        weights,
        dtype=float
    )

    hhi = float(
        np.sum(weights ** 2)
    )

    effective_assets = (
        1 / hhi
        if hhi > 0
        else 0
    )

    max_index = int(
        np.argmax(weights)
    )

    sorted_weights = np.sort(
        weights
    )[::-1]

    top3_weight = float(
        sorted_weights[:3].sum()
    )

    alerts = []

    if position_limit is not None:

        for ticker, weight in zip(
            tickers,
            weights
        ):

            if weight > position_limit:

                alerts.append({
                    "ticker": ticker,
                    "weight": float(weight),
                    "limit": float(position_limit),
                    "message": (
                        f"{ticker} represents "
                        f"{weight * 100:.1f}% of the portfolio, "
                        f"above the user-defined "
                        f"{position_limit * 100:.1f}% limit."
                    )
                })

    return {
        "largest_position": {
            "ticker": tickers[max_index],
            "weight": float(
                weights[max_index]
            )
        },

        "top3_weight": top3_weight,

        "hhi": hhi,

        "effective_number_of_assets": float(
            effective_assets
        ),

        "alerts": alerts,

        "methodology": (
            "Concentration analytics use portfolio weights, "
            "HHI and effective number of assets. "
            "Position-limit alerts are based on the "
            "user-defined limit."
        )
    }


# =========================================================
# 6. RISK-BASED REBALANCING
# =========================================================
def rebalance_to_position_limit(
    tickers,
    weights,
    position_limit
):

    weights = np.asarray(
        weights,
        dtype=float
    ).copy()

    n_assets = len(weights)

    if position_limit <= 0 or position_limit > 1:

        raise ValueError(
            "Position limit must be between 0 and 1."
        )

    if n_assets * position_limit < 1 - 1e-9:

        raise ValueError(
            "Position limit is too low for the "
            "number of assets. A feasible portfolio "
            "cannot sum to 100%."
        )

    original = weights.copy()

    # Already compliant
    if np.all(weights <= position_limit + 1e-12):

        return {
            "changed": False,

            "original_weights": {
                ticker: float(weight)
                for ticker, weight
                in zip(tickers, original)
            },

            "suggested_weights": {
                ticker: float(weight)
                for ticker, weight
                in zip(tickers, weights)
            },

            "changes": {
                ticker: 0.0
                for ticker in tickers
            },

            "message": (
                "All positions already comply "
                "with the user-defined limit."
            )
        }

    # Iterative cap + redistribution
    for _ in range(100):

        over_mask = (
            weights > position_limit + 1e-12
        )

        if not np.any(over_mask):
            break

        excess = float(
            np.sum(
                weights[over_mask]
                - position_limit
            )
        )

        weights[over_mask] = position_limit

        under_mask = (
            weights
            < position_limit - 1e-12
        )

        capacity = (
            position_limit
            - weights[under_mask]
        )

        total_capacity = float(
            capacity.sum()
        )

        if total_capacity <= 0:
            break

        weights[under_mask] += (
            excess
            * capacity
            / total_capacity
        )

    # Numerical normalization
    weights = weights / weights.sum()

    original_dict = {
        ticker: float(weight)
        for ticker, weight
        in zip(tickers, original)
    }

    suggested_dict = {
        ticker: float(weight)
        for ticker, weight
        in zip(tickers, weights)
    }

    changes = {
        ticker: float(
            new - old
        )
        for ticker, old, new
        in zip(
            tickers,
            original,
            weights
        )
    }

    return {
        "changed": True,

        "original_weights":
            original_dict,

        "suggested_weights":
            suggested_dict,

        "changes":
            changes,

        "message": (
            "Risk-based rebalancing caps positions "
            "at the user-defined limit and redistributes "
            "excess weight across positions with "
            "remaining capacity. "
            "This is not Max-Sharpe optimization."
        )
    }