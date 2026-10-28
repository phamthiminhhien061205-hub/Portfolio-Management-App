"""Test bằng dữ liệu giả (không cần mạng). Chạy: pytest -q   hoặc   python test_market_service.py"""
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import exposure_functions, factor_functions, regime_strategy, main

IDX = pd.bdate_range("2023-01-02", periods=520)


def fake_close(ticker, period="2y"):
    rng = np.random.default_rng(abs(hash(ticker)) % (2**32))
    base = 15.0 if ticker == "^VIX" else 100.0
    s = pd.Series(base * np.exp(np.cumsum(rng.normal(0.0004, 0.01, len(IDX)))), index=IDX, name=ticker)
    return s


_real_get_close = exposure_functions.get_close      # giữ bản thật để test cache
for m in (exposure_functions, factor_functions, regime_strategy):
    m.get_close = fake_close
client = TestClient(main.app)
W = {"AAPL": 0.5, "MSFT": 0.3, "NVDA": 0.2}


def test_health_and_factors():
    assert client.get("/health").json()["status"] == "ok"
    r = client.post("/market/factors", json={"weights": W}).json()
    assert set(r["factor_betas"]) == {"SPY", "QQQ", "IWM", "^VIX"}
    assert r["rolling_beta_latest"] is not None and r["momentum_exposure_latest"] is not None
    assert r["treynor"] is not None
    assert len(r["beta_matrix"]) > 100 and set(r["beta_matrix"][0]) >= {"date", "AAPL", "MSFT", "NVDA"}
    assert len(r["highest_beta"]) == 3 and r["highest_beta"][0]["beta"] >= r["lowest_beta"][0]["beta"]
    assert r["attribution"]["cumulative_active"] and r["attribution"]["tracking_error"] > 0


def test_benchmark():
    r = client.post("/market/benchmark", json={"weights": W}).json()
    assert abs(r["alpha_vs_benchmark_pct"] - (r["portfolio_total_return_pct"] - r["benchmark_total_return_pct"])) < 1e-9
    assert r["cumulative"] and r["drawdown"] and r["rolling_vol_20d"]
    assert r["portfolio_max_drawdown_pct"] <= 0


def test_risk_regime():
    r = client.get("/market/risk-regime").json()
    assert r["risk_regime"] in ("RISK ON", "RISK OFF")
    assert r["score_regime"] in ("BULL", "NEUTRAL", "BEAR")


def test_existing_endpoints_still_work():
    assert client.post("/market/exposure", json={"weights": W}).status_code == 200
    assert client.get("/market/regime/SPY").json()["regime"] in ("Bull", "Bear", "Sideways")
    assert client.post("/market/regime-backtest", json={"weights": W}).status_code == 200
    assert client.post("/market/historical-regime", json={"weights": W}).status_code in (200, 400, 503)


def test_article_regime_strategy():
    s = client.post("/market/regime-strategy", json={"weights": W}).json()
    assert abs(sum(s["max_sharpe_weights"].values()) - 1) < 1e-6
    assert all(v <= 0.5 + 1e-6 for v in s["max_sharpe_weights"].values())
    assert set(s["metrics"]) == {"strategy", "static", "spy"} and s["sessions"] > 100
    assert abs(sum(s["state_share_pct"].values()) - 100) < 1e-6


def test_momentum_is_price_based():
    r = client.post("/market/factors", json={"weights": {"SPY": 1.0}}).json()
    assert r["factor_betas"]["SPY"] > 0.999 and abs(r["capm_alpha"]) < 1e-9


def test_rolling_alpha():
    r = client.post("/market/factors", json={"weights": W}).json()
    assert r["rolling_alpha_latest"] is not None and len(r["rolling_alpha"]) > 100
    assert set(r["rolling_alpha"][0]) == {"date", "alpha"}


def test_price_cache():
    calls = []

    def fake_download(ticker, **kw):
        calls.append(ticker)
        return pd.DataFrame({"Close": fake_close(ticker).values}, index=IDX)

    old = exposure_functions.yf.download
    exposure_functions.yf.download = fake_download
    try:
        exposure_functions.clear_price_cache()
        a = _real_get_close("aapl", "2y")
        b = _real_get_close("AAPL", "2y")                # trúng cache, không tải lại
        assert calls == ["AAPL"] and a.equals(b)
        b.iloc[0] = -1                                    # sửa bản trả về không làm hỏng cache
        assert _real_get_close("AAPL", "2y").iloc[0] != -1
        _real_get_close("AAPL", "5y")                     # period khác -> tải mới
        assert calls == ["AAPL", "AAPL"]
        info = client.get("/market/cache").json()
        assert info["entries"] == 2 and "AAPL:2y" in info["keys"]
        assert client.delete("/market/cache").json()["cleared_entries"] == 2
        exposure_functions.CACHE_TTL_SECONDS = 0           # TTL = 0 -> tắt cache
        _real_get_close("AAPL", "2y"); _real_get_close("AAPL", "2y")
        assert len(calls) == 4
    finally:
        exposure_functions.CACHE_TTL_SECONDS = 300
        exposure_functions.yf.download = old
        exposure_functions.clear_price_cache()


def test_bad_weights_rejected():
    assert client.post("/market/factors", json={"weights": {"AAPL": 0.5}}).status_code == 400


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)
