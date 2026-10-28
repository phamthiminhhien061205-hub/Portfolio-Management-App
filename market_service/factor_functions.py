"""Factor analytics + risk regime cho market_service.

Bám theo bài Medium (myapp13.py), các khối: FACTOR DATA, CAPM ALPHA, Treynor,
ROLLING BETA ENGINE, ROLLING MOMENTUM EXPOSURE, REGIME DETECTION (RISK ON / RISK OFF).
"""
import numpy as np
import pandas as pd

from exposure_functions import get_close

FACTORS = ["SPY", "QQQ", "IWM", "^VIX"]
TRADING_DAYS = 252


def _series_records(s: pd.Series, key: str = "value"):
    return [{"date": d.strftime("%Y-%m-%d"), key: float(v)} for d, v in s.dropna().items()]


def _beta(y: pd.Series, x: pd.Series) -> float:
    var = x.var()
    if not np.isfinite(var) or var <= 0:
        return float("nan")
    return float(y.cov(x) / var)


def _validate_weights(weights: dict) -> dict:
    if not weights:
        raise ValueError("Portfolio must contain at least one asset")
    w = {str(k).strip().upper(): float(v) for k, v in weights.items()}
    if any((not k) or (not np.isfinite(v)) or v < 0 for k, v in w.items()):
        raise ValueError("Invalid tickers or weights")
    if abs(sum(w.values()) - 1.0) > 1e-6:
        raise ValueError("Portfolio weights must sum to 1.0")
    return w


def calculate_factor_analytics(weights: dict, period: str = "2y",
                               risk_free_rate: float = 0.0,
                               rolling_window: int = 20,
                               momentum_window: int = 12,
                               beta_matrix_window: int = 60) -> dict:
    """Beta của danh mục theo SPY/QQQ/IWM/^VIX, CAPM alpha, Treynor,
    rolling beta (vs SPY) và momentum exposure (rolling corr với momentum của SPY)."""
    w = _validate_weights(weights)
    if rolling_window < 5 or momentum_window < 1:
        raise ValueError("rolling_window must be >= 5 and momentum_window >= 1")
    if not np.isfinite(risk_free_rate):
        raise ValueError("risk_free_rate must be finite")

    tickers = list(w)
    cols = [get_close(t, period) for t in tickers] + [get_close(f, period) for f in FACTORS if f not in w]
    names = tickers + [f for f in FACTORS if f not in w]
    prices = pd.concat(cols, axis=1, join="inner").dropna()
    prices.columns = names
    returns = prices.pct_change().dropna()
    if len(returns) < max(30, rolling_window + momentum_window):
        raise ValueError("Not enough aligned daily returns")

    port = sum(returns[t] * wt for t, wt in w.items())
    factor_ret = returns[FACTORS]

    betas = {f: _beta(port, factor_ret[f]) for f in FACTORS}
    mkt_beta = betas["SPY"]

    ann_port = float(port.mean() * TRADING_DAYS)
    ann_mkt = float(factor_ret["SPY"].mean() * TRADING_DAYS)
    # CAPM alpha (Jensen, năm hoá). Với rf = 0 trùng công thức bài gốc: mean_p - beta * mean_m
    capm_alpha = ann_port - (risk_free_rate + mkt_beta * (ann_mkt - risk_free_rate))
    treynor = (ann_port - risk_free_rate) / mkt_beta if np.isfinite(mkt_beta) and mkt_beta != 0 else None

    rb = (port.rolling(rolling_window).cov(factor_ret["SPY"])
          / factor_ret["SPY"].rolling(rolling_window).var().replace(0, np.nan))
    rb = rb.replace([np.inf, -np.inf], np.nan)
    # Rolling alpha (bài: rolling mean(port) - rolling_beta * rolling mean(SPY)); nhân 252 để quy ra năm
    ra = ((port.rolling(rolling_window).mean()
           - rb * factor_ret["SPY"].rolling(rolling_window).mean()) * TRADING_DAYS).dropna()
    rb = rb.dropna()

    # Bài viết định nghĩa MOM = P(t)/P(t-12) - 1 -> tính trên GIÁ SPY (không phải trên lợi suất)
    spy_mom = prices["SPY"].pct_change(momentum_window).reindex(returns.index)
    me = port.rolling(rolling_window).corr(spy_mom).replace([np.inf, -np.inf], np.nan).dropna()

    # Rolling beta heatmap (60D) từng mã vs SPY + top/bottom beta (bài gốc: beta_matrix)
    spy_r = factor_ret["SPY"]
    spy_var = spy_r.rolling(beta_matrix_window).var().replace(0, np.nan)
    beta_matrix = pd.DataFrame({
        t: returns[t].rolling(beta_matrix_window).cov(spy_r) / spy_var for t in tickers
    }).replace([np.inf, -np.inf], np.nan).dropna(how="all")
    latest = beta_matrix.iloc[-1].dropna().sort_values(ascending=False) if len(beta_matrix) else pd.Series(dtype=float)
    top = [{"ticker": k, "beta": float(v)} for k, v in latest.head(5).items()]
    bottom = [{"ticker": k, "beta": float(v)} for k, v in latest.tail(5).sort_values().items()]

    # Active return attribution vs SPY
    active = (port - spy_r).dropna()
    cum_active = (1 + active).cumprod()
    te = float(active.std() * np.sqrt(TRADING_DAYS))
    attribution = {
        "tracking_error": te,
        "information_ratio": float(active.mean() * TRADING_DAYS / te) if te > 0 else None,
        "mean_active_return_annual": float(active.mean() * TRADING_DAYS),
        "cumulative_active": _series_records(cum_active, "value"),
        "active_returns": _series_records(active, "value"),
    }

    return {
        "period": period,
        "observations": int(len(returns)),
        "weights": w,
        "risk_free_rate": risk_free_rate,
        "factor_betas": betas,
        "market_beta": mkt_beta,
        "capm_alpha": float(capm_alpha),
        "treynor": treynor,
        "rolling_window": rolling_window,
        "rolling_beta_latest": float(rb.iloc[-1]) if len(rb) else None,
        "rolling_beta": _series_records(rb, "beta"),
        "rolling_alpha_latest": float(ra.iloc[-1]) if len(ra) else None,
        "rolling_alpha": _series_records(ra, "alpha"),
        "momentum_window": momentum_window,
        "momentum_exposure_latest": float(me.iloc[-1]) if len(me) else None,
        "momentum_exposure": _series_records(me, "correlation"),
        "beta_matrix_window": beta_matrix_window,
        "beta_matrix": [
            {"date": d.strftime("%Y-%m-%d"), **{t: (None if pd.isna(v) else float(v)) for t, v in row.items()}}
            for d, row in beta_matrix.iterrows()
        ],
        "highest_beta": top,
        "lowest_beta": bottom,
        "attribution": attribution,
        "note": "Beta/alpha là thống kê lịch sử, không phải dự báo.",
    }


def regime_score(spy: pd.Series):
    """Regime score của bài: trung bình 3 tín hiệu 0/1
    trend (MA50 > MA200), momentum (pct_change 12 phiên > 0), volatility (vol 20d < phân vị 70%).
    > 0.66: BULL, < 0.33: BEAR, còn lại NEUTRAL."""
    ret = spy.pct_change()
    vol = ret.rolling(20).std() * np.sqrt(TRADING_DAYS)
    ma200 = spy.rolling(200).mean()
    df = pd.DataFrame({
        "trend": (spy.rolling(50).mean() > ma200).astype(int),
        "momentum": (spy.pct_change(12) > 0).astype(int),
        "vol": (vol < vol.quantile(0.7)).astype(int),
    })[ma200.notna() & vol.notna()]
    score = df.mean(axis=1)
    state = pd.Series(np.where(score > 0.66, "BULL", np.where(score < 0.33, "BEAR", "NEUTRAL")),
                      index=score.index)
    return score, state


def calculate_risk_regime(period: str = "2y", vix_threshold: float = 20.0) -> dict:
    """RISK ON/OFF (SPY>MA200, QQQ>MA200, VIX<20) và regime score BULL/NEUTRAL/BEAR
    (trend + momentum + volatility) của SPY, như bài gốc."""
    prices = pd.concat([get_close(t, period) for t in ["SPY", "QQQ", "^VIX"]],
                       axis=1, join="inner").dropna()
    prices.columns = ["SPY", "QQQ", "^VIX"]
    if len(prices) < 201:
        raise ValueError("At least 201 trading days are required (MA200)")

    spy_ma200 = prices["SPY"].rolling(200).mean()
    qqq_ma200 = prices["QQQ"].rolling(200).mean()
    last = prices.iloc[-1]
    checks = {
        "spy_above_ma200": bool(last["SPY"] > spy_ma200.iloc[-1]),
        "qqq_above_ma200": bool(last["QQQ"] > qqq_ma200.iloc[-1]),
        "vix_below_threshold": bool(last["^VIX"] < vix_threshold),
    }
    risk = "RISK ON" if all(checks.values()) else "RISK OFF"

    score, state = regime_score(prices["SPY"])

    return {
        "period": period,
        "risk_regime": risk,
        "vix_threshold": vix_threshold,
        "checks": checks,
        "latest": {"spy": float(last["SPY"]), "qqq": float(last["QQQ"]), "vix": float(last["^VIX"])},
        "score_regime": state.iloc[-1],
        "score": float(score.iloc[-1]),
        "history": [{"date": d.strftime("%Y-%m-%d"), "score": float(score[d]), "regime": state[d]}
                    for d in score.index],
    }


def calculate_benchmark_comparison(weights: dict, benchmark: str = "SPY", period: str = "2y") -> dict:
    """Danh mục vs benchmark (SPY): total return, alpha (chênh lệch), đường tăng trưởng,
    drawdown và rolling volatility 20D (bài gốc: SPY BENCHMARK / Risk Engine)."""
    w = _validate_weights(weights)
    benchmark = benchmark.strip().upper()
    names = list(w) + ([benchmark] if benchmark not in w else [])
    prices = pd.concat([get_close(t, period) for t in names], axis=1, join="inner").dropna()
    prices.columns = names
    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError("At least 30 aligned daily returns are required")

    port = sum(returns[t] * wt for t, wt in w.items())
    bench = returns[benchmark]
    p_cum, b_cum = (1 + port).cumprod(), (1 + bench).cumprod()
    p_dd, b_dd = p_cum / p_cum.cummax() - 1, b_cum / b_cum.cummax() - 1
    p_total, b_total = float((p_cum.iloc[-1] - 1) * 100), float((b_cum.iloc[-1] - 1) * 100)

    def vol(r):
        return r.rolling(20).std() * np.sqrt(TRADING_DAYS)

    return {
        "benchmark": benchmark,
        "period": period,
        "observations": int(len(returns)),
        "portfolio_total_return_pct": p_total,
        "benchmark_total_return_pct": b_total,
        "alpha_vs_benchmark_pct": p_total - b_total,
        "portfolio_annual_vol_pct": float(port.std() * np.sqrt(TRADING_DAYS) * 100),
        "benchmark_annual_vol_pct": float(bench.std() * np.sqrt(TRADING_DAYS) * 100),
        "portfolio_max_drawdown_pct": float(p_dd.min() * 100),
        "benchmark_max_drawdown_pct": float(b_dd.min() * 100),
        "cumulative": [{"date": d.strftime("%Y-%m-%d"), "portfolio": float(p_cum[d]), "benchmark": float(b_cum[d])}
                       for d in p_cum.index],
        "drawdown": [{"date": d.strftime("%Y-%m-%d"), "portfolio": float(p_dd[d]), "benchmark": float(b_dd[d])}
                     for d in p_cum.index],
        "rolling_vol_20d": [{"date": d.strftime("%Y-%m-%d"), "portfolio": float(vp), "benchmark": float(vb)}
                            for d, vp, vb in zip(p_cum.index, vol(port), vol(bench)) if not (pd.isna(vp) or pd.isna(vb))],
    }


# ---------------------------------------------------------------- SPY benchmark (bài: "SPY BENCHMARK")
def _max_drawdown_series(cum: pd.Series) -> pd.Series:
    return cum / cum.cummax() - 1


# ---------------------------------------------------------------- Regime-switching (đúng như bài)
def _max_sharpe_weights(returns: pd.DataFrame, max_weight: float = 0.5) -> np.ndarray:
    """Max Sharpe long-only, tổng = 1, mỗi mã <= max_weight (SLSQP) — như myapp9/10/13."""
    from scipy.optimize import minimize

    n = returns.shape[1]
    max_weight = max(max_weight, 1.0 / n)          # tránh bài toán vô nghiệm khi n < 1/max_weight
    mean_r, cov = returns.mean().values * TRADING_DAYS, returns.cov().values * TRADING_DAYS

    def neg_sharpe(w):
        vol = np.sqrt(w @ cov @ w)
        return -(w @ mean_r) / vol if vol > 0 else 0.0

    res = minimize(neg_sharpe, np.full(n, 1.0 / n), method="SLSQP",
                   bounds=[(0, max_weight)] * n,
                   constraints=({"type": "eq", "fun": lambda x: np.sum(x) - 1},))
    w = res.x if res.success else np.full(n, 1.0 / n)
    return np.clip(w, 0, None) / np.clip(w, 0, None).sum()


def backtest_article_regime_strategy(weights: dict, period: str = "2y", max_weight: float = 0.5,
                                     lag: int = 1) -> dict:
    """Chiến lược của bài: BULL -> danh mục Max Sharpe; NEUTRAL -> equal weight; BEAR -> tiền mặt.
    Regime tính từ SPY bằng regime_score. lag=1: dùng regime của phiên trước (tránh look-ahead);
    lag=0 giống code bài (dùng regime cùng ngày). So sánh với danh mục tĩnh (weights) và SPY."""
    w = _validate_weights(weights)
    if lag not in (0, 1):
        raise ValueError("lag must be 0 or 1")
    tickers = list(w)
    cols = [get_close(t, period) for t in tickers] + [get_close("SPY", period)]
    prices = pd.concat(cols, axis=1, join="inner").dropna()
    prices.columns = tickers + ["__spy__"]
    if len(prices) < 202:
        raise ValueError("At least 202 aligned trading days are required")
    returns = prices.pct_change().dropna()
    _, state = regime_score(prices["__spy__"])
    # căn theo NGÀY (bài gốc ghép theo vị trí nên bị lệch ngày)
    state = state.reindex(returns.index).shift(lag)
    valid = state.notna()
    r = returns[valid]
    state = state[valid]
    if len(r) < 20:
        raise ValueError("Not enough data after the MA200 warm-up; use a longer period")

    opt_w = _max_sharpe_weights(returns[tickers], max_weight)
    eq_w = np.full(len(tickers), 1.0 / len(tickers))
    asset = r[tickers]
    opt_ret, eq_ret = asset.values @ opt_w, asset.values @ eq_w
    strat = pd.Series(np.where(state == "BULL", opt_ret, np.where(state == "BEAR", 0.0, eq_ret)), index=r.index)
    static = pd.Series(asset.values @ np.array([w[t] for t in tickers]), index=r.index)
    spy = r["__spy__"]

    def metrics(x):
        cum = (1 + x).cumprod()
        return {"total_return_pct": float((cum.iloc[-1] - 1) * 100),
                "annualized_volatility_pct": float(x.std() * np.sqrt(TRADING_DAYS) * 100),
                "sharpe": None if x.std() == 0 else float(x.mean() / x.std() * np.sqrt(TRADING_DAYS)),
                "max_drawdown_pct": float(_max_drawdown_series(cum).min() * 100)}

    eq = pd.DataFrame({"strategy": (1 + strat).cumprod(), "static": (1 + static).cumprod(),
                       "spy": (1 + spy).cumprod()})
    return {
        "period": period, "lag": lag, "sessions": int(len(r)),
        "rules": {"BULL": "max-Sharpe weights", "NEUTRAL": "equal weight", "BEAR": "cash (0%)"},
        "max_sharpe_weights": {t: float(x) for t, x in zip(tickers, opt_w)},
        "state_share_pct": {k: float((state == k).mean() * 100) for k in ("BULL", "NEUTRAL", "BEAR")},
        "metrics": {"strategy": metrics(strat), "static": metrics(static), "spy": metrics(spy)},
        "history": [{"date": d.strftime("%Y-%m-%d"), "regime": state[d],
                     "strategy_equity": float(eq.loc[d, "strategy"]),
                     "static_equity": float(eq.loc[d, "static"]),
                     "spy_equity": float(eq.loc[d, "spy"])} for d in eq.index],
        "assumptions": "Tiền mặt lãi 0%; không phí giao dịch; tỷ trọng Max Sharpe ước lượng trên toàn bộ "
                       "giai đoạn (in-sample, như bài gốc) nên kết quả có thiên lệch lạc quan.",
    }
