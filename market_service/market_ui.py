"""Giao diện Streamlit cho market_service.

Chạy (khi API đang chạy ở cổng 8003):
    cd market_service
    streamlit run market_ui.py --server.port 8503

Biến môi trường MARKET_API_URL đổi địa chỉ API (mặc định http://127.0.0.1:8003;
trong Docker Compose dùng http://market-service:8003).
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

DEFAULT_API = os.getenv("MARKET_API_URL", "http://127.0.0.1:8003").rstrip("/")

st.set_page_config(page_title="Market Service Dashboard", page_icon="📈", layout="wide")
st.title("📈 Market Service Dashboard")
st.caption("Factor analytics · Risk regime · Regime-switching backtest — gọi tới market_service (FastAPI)")


# ------------------------------------------------------------------ API helpers
def call_api(method: str, path: str, *, params=None, payload=None):
    url = f"{api_url}{path}"
    try:
        if method == "GET":
            r = requests.get(url, params=params, timeout=120)
        else:
            r = requests.post(url, json=payload, timeout=180)
    except requests.RequestException as exc:
        st.error(f"Không kết nối được tới market_service ({url}). Service đã chạy chưa?\n\n{exc}")
        return None
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        st.error(f"API trả lỗi {r.status_code}: {detail}")
        return None
    return r.json()


def pct(x, digits=2):
    return "n/a" if x is None else f"{x * 100:.{digits}f}%"


def num(x, digits=2):
    return "n/a" if x is None else f"{x:.{digits}f}"


# ------------------------------------------------------------------ Sidebar
with st.sidebar:
    st.header("Portfolio Builder")
    api_url = st.text_input("API URL", DEFAULT_API).rstrip("/")
    tickers_text = st.text_input("Tickers (cách nhau bởi dấu phẩy)", "AAPL, MSFT, NVDA")
    tickers = list(dict.fromkeys(t.strip().upper() for t in tickers_text.split(",") if t.strip()))
    period = st.selectbox("Period", ["1y", "2y", "5y", "10y"], index=1,
                          help="Cần ít nhất ~1 năm để tính MA200.")
    rf = st.number_input("Risk-free rate (năm)", 0.0, 0.2, 0.0, 0.005, format="%.3f",
                         help="Bài gốc dùng 0.")

    st.subheader("Weights")
    raw = [st.slider(t, 0.0, 1.0, 1.0 / max(len(tickers), 1), 0.05, key=f"w_{t}") for t in tickers]
    total = sum(raw)
    weights = {t: (w / total if total > 0 else 1.0 / len(tickers)) for t, w in zip(tickers, raw)}
    if tickers:
        st.caption("Chuẩn hoá để tổng = 100%: " + ", ".join(f"{t} {w:.0%}" for t, w in weights.items()))
    run = st.button("▶ Run analysis", type="primary", use_container_width=True)

if not tickers:
    st.info("Nhập ít nhất một ticker ở thanh bên.")
    st.stop()

# ------------------------------------------------------------------ Fetch
if run:
    with st.spinner("Đang lấy dữ liệu thị trường…"):
        st.session_state["factors"] = call_api(
            "POST", "/market/factors",
            payload={"weights": weights, "period": period, "risk_free_rate": rf})
        st.session_state["regime"] = call_api(
            "GET", "/market/risk-regime", params={"period": period})
        st.session_state["exposure"] = call_api(
            "POST", "/market/exposure", payload={"weights": weights, "period": period})
        st.session_state["bench"] = call_api(
            "POST", "/market/benchmark", payload={"weights": weights, "period": period})
        st.session_state["hist"] = call_api(
            "POST", "/market/historical-regime", payload={"weights": weights, "period": period})
        st.session_state.pop("backtest", None)

tab_p, tab_f, tab_r, tab_h, tab_b = st.tabs(
    ["📊 Benchmark vs SPY", "🧮 Factors", "🚦 Risk Regime", "🗓 Historical Regime", "🔁 Regime Backtest"])

# ------------------------------------------------------------------ Tab 0: Benchmark
with tab_p:
    bm = st.session_state.get("bench")
    if not bm:
        st.info("Bấm **Run analysis** ở thanh bên để bắt đầu.")
    else:
        c = st.columns(4)
        c[0].metric("Portfolio Return", f"{bm['portfolio_total_return_pct']:.2f}%")
        c[1].metric(f"{bm['benchmark']} Return", f"{bm['benchmark_total_return_pct']:.2f}%")
        c[2].metric(f"Alpha vs {bm['benchmark']}", f"{bm['alpha_vs_benchmark_pct']:.2f}%")
        c[3].metric("Max Drawdown (P / B)",
                    f"{bm['portfolio_max_drawdown_pct']:.1f}% / {bm['benchmark_max_drawdown_pct']:.1f}%")
        st.caption("Alpha ở đây = lợi suất tích lũy danh mục − lợi suất tích lũy benchmark (điểm %), như bài gốc.")

        def two_lines(rows, title, ytitle):
            df = pd.DataFrame(rows).melt(id_vars="date", var_name="series", value_name=ytitle)
            df["series"] = df["series"].map({"portfolio": "Portfolio", "benchmark": bm["benchmark"]})
            return px.line(df, x="date", y=ytitle, color="series", title=title)

        st.plotly_chart(two_lines(bm["cumulative"], "Growth of $1: Portfolio vs benchmark", "growth of $1"),
                        use_container_width=True)
        l, r_ = st.columns(2)
        with l:
            st.plotly_chart(two_lines(bm["drawdown"], "Drawdown comparison", "drawdown"), use_container_width=True)
        with r_:
            st.plotly_chart(two_lines(bm["rolling_vol_20d"], "Rolling volatility (20D, annualized)", "volatility"),
                            use_container_width=True)

# ------------------------------------------------------------------ Tab 1: Factors
with tab_f:
    f = st.session_state.get("factors")
    e = st.session_state.get("exposure")
    if not f:
        st.info("Bấm **Run analysis** ở thanh bên để bắt đầu.")
    else:
        fb = f["factor_betas"]
        c = st.columns(4)
        c[0].metric("SPY Beta", num(fb["SPY"]))
        c[1].metric("QQQ Beta", num(fb["QQQ"]))
        c[2].metric("IWM Beta", num(fb["IWM"]))
        c[3].metric("VIX Beta", num(fb["^VIX"]))
        c = st.columns(5)
        c[0].metric("CAPM Alpha (năm)", pct(f["capm_alpha"]))
        c[1].metric("Treynor Ratio", num(f["treynor"]))
        c[2].metric(f"Rolling Beta ({f['rolling_window']}D)", num(f["rolling_beta_latest"]))
        c[3].metric("Momentum Exposure", num(f["momentum_exposure_latest"]))
        if f.get("rolling_alpha_latest") is not None:
            st.caption(f"Rolling alpha mới nhất ({f['rolling_window']}D, quy ra năm): "
                       f"{f['rolling_alpha_latest'] * 100:.2f}%")
        c[4].metric("Market Regime", (st.session_state.get("regime") or {}).get("risk_regime", "n/a"))
        st.caption(f"{f['observations']} phiên giao dịch · beta/alpha là thống kê lịch sử, không phải dự báo.")

        left, right = st.columns(2)
        with left:
            bdf = pd.DataFrame({"Factor": list(f["factor_betas"]), "Beta": list(f["factor_betas"].values())})
            fig = px.bar(bdf, x="Factor", y="Beta", text=bdf["Beta"].round(2), title="Portfolio factor betas")
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        with right:
            if e:
                comp = pd.DataFrame(e["components"])
                st.markdown(f"**Portfolio beta vs {e['benchmark']}: {e['portfolio_beta']:.2f}** — "
                            f"market sensitivity: **{e['market_sensitivity']}**")
                st.dataframe(comp.rename(columns={"weighted_beta": "weighted beta"}),
                             use_container_width=True, hide_index=True)

        rb = pd.DataFrame(f["rolling_beta"])
        if not rb.empty:
            fig = px.line(rb, x="date", y="beta", title=f"Rolling beta vs SPY ({f['rolling_window']}D)")
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        ra = pd.DataFrame(f.get("rolling_alpha", []))
        if not ra.empty:
            ra["alpha %"] = ra["alpha"] * 100
            fig = px.line(ra, x="date", y="alpha %", title=f"Rolling alpha vs SPY ({f['rolling_window']}D, annualized %)")
            fig.add_hline(y=0.0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        me = pd.DataFrame(f["momentum_exposure"])
        if not me.empty:
            fig = px.line(me, x="date", y="correlation", title="Momentum factor exposure (rolling correlation)")
            fig.add_hline(y=0.0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        st.caption("Beta > 1: mạnh hơn thị trường · < 1: phòng thủ hơn · < 0: ngược chiều. "
                   "Momentum exposure > 0: danh mục theo xu hướng; < 0: nghịch xu hướng.")

        st.divider()
        st.subheader(f"Rolling Beta Heatmap vs SPY ({f['beta_matrix_window']}D)")
        bmx = pd.DataFrame(f["beta_matrix"])
        if not bmx.empty:
            bmx = bmx.set_index("date")
            st.plotly_chart(px.imshow(bmx.T, aspect="auto", color_continuous_scale="RdBu_r",
                                      color_continuous_midpoint=1.0, labels={"color": "beta"}),
                            use_container_width=True)
        else:
            st.info("Chưa đủ dữ liệu cho heatmap (cần thêm lịch sử).")

        st.subheader("Active Return Attribution vs SPY")
        at_ = f["attribution"]
        a = st.columns(3)
        a[0].metric("Active return (năm)", pct(at_["mean_active_return_annual"]))
        a[1].metric("Tracking error", pct(at_["tracking_error"]))
        a[2].metric("Information ratio", num(at_["information_ratio"]))
        l, r_ = st.columns(2)
        with l:
            ca = pd.DataFrame(at_["cumulative_active"])
            fig = px.line(ca, x="date", y="value", title="Portfolio outperformance vs SPY")
            fig.update_layout(yaxis_title="Cumulative active return")
            st.plotly_chart(fig, use_container_width=True)
        with r_:
            ar = pd.DataFrame(at_["active_returns"])
            st.plotly_chart(px.histogram(ar, x="value", nbins=50, title="Active return distribution vs SPY"),
                            use_container_width=True)

        st.divider()
        st.subheader("Factor Summary")
        st.dataframe(pd.DataFrame({"Factor": list(fb), "Beta": [round(v, 4) for v in fb.values()]}),
                     use_container_width=True, hide_index=True)
        h1, h2 = st.columns(2)
        with h1:
            st.markdown("**Highest Beta Names**")
            st.dataframe(pd.DataFrame(f["highest_beta"]), use_container_width=True, hide_index=True)
        with h2:
            st.markdown("**Lowest Beta Names**")
            st.dataframe(pd.DataFrame(f["lowest_beta"]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ Tab 2: Risk regime
with tab_r:
    r = st.session_state.get("regime")
    if not r:
        st.info("Bấm **Run analysis** ở thanh bên để bắt đầu.")
    else:
        c = st.columns(3)
        c[0].metric("Market regime", r["risk_regime"])
        c[1].metric("Regime score (SPY)", r["score_regime"], f"score {r['score']:.2f}")
        c[2].metric("VIX", num(r["latest"]["vix"]), f"ngưỡng {r['vix_threshold']:.0f}", delta_color="off")
        ck = r["checks"]
        st.markdown(
            f"- SPY trên MA200: **{'✅' if ck['spy_above_ma200'] else '❌'}**\n"
            f"- QQQ trên MA200: **{'✅' if ck['qqq_above_ma200'] else '❌'}**\n"
            f"- VIX dưới {r['vix_threshold']:.0f}: **{'✅' if ck['vix_below_threshold'] else '❌'}**\n\n"
            "RISK ON khi cả 3 điều kiện đều đúng.")
        h = pd.DataFrame(r["history"])
        if not h.empty:
            colors = {"BULL": "#2e9e5b", "NEUTRAL": "#e0a100", "BEAR": "#d64545"}
            fig = px.scatter(h, x="date", y="score", color="regime", color_discrete_map=colors,
                             title="Regime score (trend + momentum + volatility)")
            fig.add_hline(y=0.66, line_dash="dash", line_color="gray")
            fig.add_hline(y=0.33, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(h.tail(20), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ Tab 3: Historical regime
with tab_h:
    d = st.session_state.get("hist")
    if not d:
        st.info("Bấm **Run analysis** ở thanh bên để bắt đầu.")
    else:
        st.metric(f"Current regime ({d['benchmark']})", d["current_regime"])
        summ = pd.DataFrame(d["summary"])
        st.dataframe(summ, use_container_width=True, hide_index=True)
        hist = pd.DataFrame(d["history"])
        if not hist.empty:
            colors = {"Bull": "#2e9e5b", "Sideways": "#e0a100", "Bear": "#d64545"}
            fig = px.scatter(hist, x="date", y="close", color="regime", color_discrete_map=colors,
                             title=f"{d['benchmark']} price by regime")
            fig.add_trace(go.Scatter(x=hist["date"], y=hist["sma50"], name="SMA50", mode="lines"))
            fig.add_trace(go.Scatter(x=hist["date"], y=hist["sma200"], name="SMA200", mode="lines"))
            st.plotly_chart(fig, use_container_width=True)
        if not summ.empty:
            m = summ.melt(id_vars="regime", value_vars=["avg_portfolio_return_pct", "avg_benchmark_return_pct"],
                          var_name="series", value_name="avg daily return %")
            st.plotly_chart(px.bar(m, x="regime", y="avg daily return %", color="series", barmode="group",
                                   title="Average daily return by regime"), use_container_width=True)

# ------------------------------------------------------------------ Tab 4: Backtest
with tab_b:
    st.subheader("A. Regime-switching theo bài (BULL = Max Sharpe · NEUTRAL = equal weight · BEAR = cash)")
    ca = st.columns(3)
    max_w = ca[0].slider("Max weight / mã (Max Sharpe)", 0.1, 1.0, 0.5, 0.05)
    lag = ca[1].selectbox("Độ trễ tín hiệu", [1, 0], format_func=lambda x: "1 phiên (tránh look-ahead)" if x else "0 (giống code bài)")
    if st.button("Run article strategy"):
        with st.spinner("Đang tối ưu Max Sharpe và chạy backtest…"):
            st.session_state["article"] = call_api("POST", "/market/regime-strategy", payload={
                "weights": weights, "period": period, "max_weight": max_w, "lag": lag})
    a = st.session_state.get("article")
    if a:
        c4 = st.columns(3)
        for col, k in zip(c4, ("BULL", "NEUTRAL", "BEAR")):
            col.metric(f"% phiên {k}", f"{a['state_share_pct'][k]:.1f}%")
        mta = pd.DataFrame(a["metrics"]).T.rename(index={
            "strategy": "Regime strategy", "static": "Static portfolio", "spy": "SPY"})
        mta.columns = ["Total return %", "Annualized vol %", "Sharpe", "Max drawdown %"]
        st.dataframe(mta, use_container_width=True)
        ha = pd.DataFrame(a["history"])
        ea = ha.melt(id_vars="date", value_vars=["strategy_equity", "static_equity", "spy_equity"],
                     var_name="series", value_name="growth of $1")
        ea["series"] = ea["series"].map({"strategy_equity": "Regime strategy",
                                         "static_equity": "Static portfolio", "spy_equity": "SPY"})
        st.plotly_chart(px.line(ea, x="date", y="growth of $1", color="series",
                                title="Bull/Bear regime switching vs static vs SPY"), use_container_width=True)
        st.caption("Max Sharpe weights: " + ", ".join(f"{k} {v:.0%}" for k, v in a["max_sharpe_weights"].items())
                   + " — " + a["assumptions"])
    st.divider()
    st.subheader("B. Regime theo exposure (Bull/Sideways/Bear scale cổ phiếu, phần còn lại là tiền mặt)")
    st.markdown("Chiến lược: nhìn regime của phiên **trước** để chọn tỷ lệ cổ phiếu cho phiên sau "
                "(tránh look-ahead), phần còn lại giữ tiền mặt.")
    c = st.columns(4)
    bull = c[0].slider("Bull exposure", 0.0, 1.0, 1.0, 0.05)
    side = c[1].slider("Sideways exposure", 0.0, 1.0, 0.6, 0.05)
    bear = c[2].slider("Bear exposure", 0.0, 1.0, 0.25, 0.05)
    cost = c[3].number_input("Cost (bps)", 0.0, 100.0, 5.0, 1.0)
    if st.button("Run backtest"):
        with st.spinner("Đang chạy backtest…"):
            st.session_state["backtest"] = call_api("POST", "/market/regime-backtest", payload={
                "weights": weights, "period": period, "bull_exposure": bull,
                "bear_exposure": bear, "sideways_exposure": side, "cost_bps": cost})
    b = st.session_state.get("backtest")
    if b:
        mt = pd.DataFrame(b["metrics"]).T.rename(index={
            "base": "Original portfolio", "strategy": "Regime strategy", "benchmark": b["benchmark"]})
        mt.columns = ["Total return %", "Annualized vol %", "Max drawdown %"]
        st.dataframe(mt, use_container_width=True)
        hist = pd.DataFrame(b["history"])
        eq = hist.melt(id_vars="date", value_vars=["base_equity", "strategy_equity", "benchmark_equity"],
                       var_name="series", value_name="growth of $1")
        eq["series"] = eq["series"].map({"base_equity": "Original portfolio",
                                         "strategy_equity": "Regime strategy",
                                         "benchmark_equity": b["benchmark"]})
        st.plotly_chart(px.line(eq, x="date", y="growth of $1", color="series",
                                title="Equity curves"), use_container_width=True)
        st.caption(b["assumptions"])
        with st.expander("Regime & exposure theo ngày (20 dòng cuối)"):
            st.dataframe(hist[["date", "regime", "exposure"]].tail(20), use_container_width=True, hide_index=True)
