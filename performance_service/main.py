from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

import numpy as np

from risk_engine import (
    calculate_relative_risk,
    generate_risk_alerts,
    explain_portfolio,
    calculate_health_score,
    concentration_analysis,
    rebalance_to_position_limit
)


# =========================================================
# APP
# =========================================================
app = FastAPI(
    title="Portfolio Performance & Risk Service",
    description=(
        "Portfolio performance analytics and "
        "risk intelligence service."
    ),
    version="2.0"
)


# =========================================================
# INPUT MODELS
# =========================================================
class PortfolioInput(BaseModel):

    returns: List[float]

    dates: Optional[List[str]] = None

    tickers: Optional[List[str]] = None

    weights: Optional[List[float]] = None

    position_limit: Optional[float] = None

    alert_percentile: float = 0.90


class StressTestInput(BaseModel):

    portfolio_value: float

    scenario_shocks: List[float]

    beta: Optional[float] = None


class RebalanceInput(BaseModel):

    tickers: List[str]

    weights: List[float]

    position_limit: float


# =========================================================
# VALIDATION
# =========================================================
def validate_returns(returns):

    if len(returns) < 2:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least 2 return observations "
                "are required."
            )
        )

    array = np.asarray(
        returns,
        dtype=float
    )

    if not np.all(
        np.isfinite(array)
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Returns contain invalid values."
            )
        )

    return array


def validate_portfolio_structure(
    tickers,
    weights
):

    if tickers is None and weights is None:
        return

    if tickers is None or weights is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "tickers and weights must "
                "be provided together."
            )
        )

    if len(tickers) != len(weights):

        raise HTTPException(
            status_code=400,
            detail=(
                "tickers and weights must "
                "have the same length."
            )
        )

    if len(tickers) == 0:

        raise HTTPException(
            status_code=400,
            detail="Portfolio cannot be empty."
        )

    if any(
        weight < 0
        for weight in weights
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Negative portfolio weights "
                "are not supported."
            )
        )

    weight_sum = sum(weights)

    if abs(weight_sum - 1.0) > 0.01:

        raise HTTPException(
            status_code=400,
            detail=(
                "Portfolio weights must sum "
                "approximately to 1.0."
            )
        )


# =========================================================
# HOME / HEALTH CHECK
# =========================================================
@app.get("/")
def home():

    return {
        "service":
            "Portfolio Performance & Risk",

        "version":
            "2.0",

        "status":
            "running"
    }


# =========================================================
# MAIN PERFORMANCE ANALYSIS
# =========================================================
@app.post("/analyze")
def analyze_portfolio(
    data: PortfolioInput
):

    returns = validate_returns(
        data.returns
    )

    validate_portfolio_structure(
        data.tickers,
        data.weights
    )

    if not (
        0 < data.alert_percentile < 1
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "alert_percentile must be "
                "between 0 and 1."
            )
        )

    # =====================================================
    # 1. CUMULATIVE PERFORMANCE
    # =====================================================
    cumulative = np.cumprod(
        1 + returns
    )

    # =====================================================
    # 2. TOTAL RETURN
    # =====================================================
    total_return = (
        cumulative[-1] - 1
    )

    # =====================================================
    # 3. ANNUALIZED RETURN
    # =====================================================
    annual_return = (
        np.mean(returns)
        * 252
    )

    # =====================================================
    # 4. ANNUALIZED VOLATILITY
    # =====================================================
    daily_std = np.std(
        returns,
        ddof=1
    )

    volatility = (
        daily_std
        * np.sqrt(252)
    )

    # =====================================================
    # 5. SHARPE RATIO
    # =====================================================
    if daily_std != 0:

        sharpe = (
            np.mean(returns)
            / daily_std
            * np.sqrt(252)
        )

    else:

        sharpe = 0.0

    # =====================================================
    # 6. DRAWDOWN
    # =====================================================
    running_max = np.maximum.accumulate(
        cumulative
    )

    drawdown = (
        cumulative
        / running_max
        - 1
    )

    max_drawdown = float(
        np.min(drawdown)
    )

    # =====================================================
    # 7. NEW: RELATIVE RISK LEVEL
    # =====================================================
    risk_assessment = (
        calculate_relative_risk(
            returns
        )
    )

    # =====================================================
    # 8. NEW: ALERT SYSTEM
    # =====================================================
    alerts = generate_risk_alerts(
        returns,
        data.alert_percentile
    )

    # =====================================================
    # 9. NEW: EXPLAINABLE ASSESSMENT
    # =====================================================
    explanation = explain_portfolio(
        returns,
        float(total_return),
        float(volatility),
        float(sharpe),
        float(max_drawdown)
    )

    # =====================================================
    # 10. NEW: HEALTH SCORE
    # =====================================================
    portfolio_health = (
        calculate_health_score(
            returns
        )
    )

    # =====================================================
    # 11. NEW: CONCENTRATION
    # =====================================================
    concentration = None

    if (
        data.tickers is not None
        and
        data.weights is not None
    ):

        concentration = (
            concentration_analysis(
                data.tickers,
                data.weights,
                data.position_limit
            )
        )

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "total_return":
            float(total_return),

        "annual_return":
            float(annual_return),

        "volatility":
            float(volatility),

        "sharpe":
            float(sharpe),

        "max_drawdown":
            float(max_drawdown),

        "cumulative_performance":
            cumulative.tolist(),

        "drawdown_series":
            drawdown.tolist(),

        "risk_assessment":
            risk_assessment,

        "alerts":
            alerts,

        "explanation":
            explanation,

        "portfolio_health":
            portfolio_health,

        "concentration":
            concentration,

        "observation_count":
            len(returns)
    }


# =========================================================
# STRESS TEST
# =========================================================
@app.post("/stress-test")
def stress_test(
    data: StressTestInput
):

    if data.portfolio_value <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "portfolio_value must "
                "be greater than 0."
            )
        )

    if not data.scenario_shocks:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one scenario "
                "shock is required."
            )
        )

    scenarios = []

    for market_shock in (
        data.scenario_shocks
    ):

        # If beta exists:
        # approximate portfolio response
        if data.beta is not None:

            portfolio_shock = (
                market_shock
                * data.beta
            )

            mode = (
                "Beta-adjusted market shock"
            )

        else:

            portfolio_shock = (
                market_shock
            )

            mode = (
                "Direct portfolio shock"
            )

        change = (
            data.portfolio_value
            * portfolio_shock
        )

        estimated_value = (
            data.portfolio_value
            + change
        )

        scenarios.append({
            "market_shock":
                float(market_shock),

            "portfolio_shock":
                float(portfolio_shock),

            "estimated_loss_or_gain":
                float(change),

            "estimated_portfolio_value":
                float(estimated_value),

            "mode":
                mode
        })

    return {
        "initial_portfolio_value":
            data.portfolio_value,

        "beta":
            data.beta,

        "scenarios":
            scenarios,

        "methodology": (
            "Scenario analysis only. "
            "When beta is supplied, estimated "
            "portfolio shock equals market shock "
            "multiplied by beta. "
            "This is not a forecast."
        )
    }


# =========================================================
# RISK-BASED REBALANCING
# =========================================================
@app.post("/rebalance-risk")
def risk_rebalance(
    data: RebalanceInput
):

    validate_portfolio_structure(
        data.tickers,
        data.weights
    )

    try:

        result = (
            rebalance_to_position_limit(
                data.tickers,
                data.weights,
                data.position_limit
            )
        )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )