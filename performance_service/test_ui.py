import streamlit as st
import requests
import pandas as pd
import numpy as np
import altair as alt


# =========================================================
# CONFIG
# =========================================================
API_BASE = "http://localhost:8002"

ANALYZE_URL = (
    f"{API_BASE}/analyze"
)

STRESS_URL = (
    f"{API_BASE}/stress-test"
)

REBALANCE_URL = (
    f"{API_BASE}/rebalance-risk"
)


st.set_page_config(
    page_title="Portfolio Risk Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>

    .block-container {
        max-width: 1450px;
        padding-top: 1.4rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e5e7eb;
    }

    [data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    div.stButton > button {
        border-radius: 10px;
        height: 3rem;
        font-weight: 650;
    }

    div.stButton > button[kind="primary"] {
        background-color: #0f172a;
        border-color: #0f172a;
    }

    .hero-title {
        font-size: 2.65rem;
        font-weight: 760;
        color: #0f172a;
        margin-bottom: 3px;
    }

    .hero-subtitle {
        color: #64748b;
        font-size: 1rem;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 720;
        color: #0f172a;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    .risk-low {
        padding: 16px;
        border-radius: 14px;
        background: #dcfce7;
        color: #166534;
        font-size: 1.4rem;
        font-weight: 750;
        text-align: center;
    }

    .risk-medium {
        padding: 16px;
        border-radius: 14px;
        background: #fef3c7;
        color: #92400e;
        font-size: 1.4rem;
        font-weight: 750;
        text-align: center;
    }

    .risk-high {
        padding: 16px;
        border-radius: 14px;
        background: #fee2e2;
        color: #991b1b;
        font-size: 1.4rem;
        font-weight: 750;
        text-align: center;
    }

    .risk-na {
        padding: 16px;
        border-radius: 14px;
        background: #e2e8f0;
        color: #475569;
        font-size: 1.2rem;
        font-weight: 700;
        text-align: center;
    }

    .insight-card {
        padding: 16px 18px;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        background: #f8fafc;
        min-height: 110px;
    }

    .api-online {
        color: #166534;
        background: #dcfce7;
        padding: 8px 10px;
        border-radius: 8px;
        font-weight: 650;
    }

    .api-offline {
        color: #991b1b;
        background: #fee2e2;
        padding: 8px 10px;
        border-radius: 8px;
        font-weight: 650;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION
# =========================================================
if "result" not in st.session_state:
    st.session_state.result = None

if "returns_df" not in st.session_state:
    st.session_state.returns_df = None


# =========================================================
# HELPERS
# =========================================================
def api_online():

    try:

        response = requests.get(
            API_BASE,
            timeout=2
        )

        return (
            response.status_code
            == 200
        )

    except requests.RequestException:

        return False


def pct(value):

    return (
        f"{value * 100:.2f}%"
    )


def parse_float_list(text):

    return [
        float(value.strip())
        for value in text.split(",")
        if value.strip()
    ]


def parse_ticker_list(text):

    return [
        value.strip().upper()
        for value in text.split(",")
        if value.strip()
    ]


def create_time_x(df):

    converted = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    if converted.notna().all():

        df = df.copy()

        df["Date"] = converted

        x = alt.X(
            "Date:T",
            title=None,
            axis=alt.Axis(
                format="%d %b"
            )
        )

        return df, x

    return (
        df,
        alt.X(
            "Date:N",
            title=None,
            sort=None
        )
    )


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title(
    "Portfolio Input"
)


if api_online():

    st.sidebar.markdown(
        '<div class="api-online">'
        '● Performance API Online'
        '</div>',
        unsafe_allow_html=True
    )

else:

    st.sidebar.markdown(
        '<div class="api-offline">'
        '● Performance API Offline'
        '</div>',
        unsafe_allow_html=True
    )


st.sidebar.divider()


data_source = st.sidebar.radio(
    "Data source",
    [
        "Sample Data",
        "Manual Input",
        "Upload CSV"
    ]
)


returns = []
dates = []


# =========================================================
# SAMPLE DATA
# =========================================================
if data_source == "Sample Data":

    rng = np.random.default_rng(
        42
    )

    returns = (
        rng.normal(
            loc=0.0005,
            scale=0.012,
            size=300
        )
        .tolist()
    )

    dates = (
        pd.bdate_range(
            end="2026-10-27",
            periods=300
        )
        .strftime("%Y-%m-%d")
        .tolist()
    )

    st.sidebar.info(
        "300 illustrative daily observations loaded."
    )


# =========================================================
# MANUAL
# =========================================================
elif data_source == "Manual Input":

    manual = st.sidebar.text_area(
        "Daily Returns",
        value=(
            "0.01,-0.005,0.012,0.003,"
            "-0.008,0.015,0.004,-0.002"
        )
    )

    try:

        returns = parse_float_list(
            manual
        )

        dates = [
            f"Day {i + 1}"
            for i in range(
                len(returns)
            )
        ]

    except ValueError:

        st.sidebar.error(
            "Invalid return values."
        )


# =========================================================
# CSV
# =========================================================
else:

    uploaded = (
        st.sidebar.file_uploader(
            "Upload CSV",
            type=["csv"]
        )
    )

    if uploaded is not None:

        csv_df = pd.read_csv(
            uploaded
        )

        if "return" not in csv_df.columns:

            st.sidebar.error(
                "CSV must contain "
                "a 'return' column."
            )

        else:

            csv_df["return"] = (
                pd.to_numeric(
                    csv_df["return"],
                    errors="coerce"
                )
            )

            csv_df = (
                csv_df.dropna(
                    subset=["return"]
                )
            )

            returns = (
                csv_df["return"]
                .tolist()
            )

            if "date" in csv_df.columns:

                dates = (
                    csv_df["date"]
                    .astype(str)
                    .tolist()
                )

            else:

                dates = [
                    f"Day {i + 1}"
                    for i in range(
                        len(returns)
                    )
                ]


# =========================================================
# PORTFOLIO STRUCTURE
# =========================================================
st.sidebar.divider()

st.sidebar.subheader(
    "Portfolio Structure"
)


ticker_text = (
    st.sidebar.text_input(
        "Tickers",
        "AAPL,MSFT,NVDA,GOOGL"
    )
)


weight_text = (
    st.sidebar.text_input(
        "Weights",
        "0.20,0.20,0.45,0.15"
    )
)


position_limit = (
    st.sidebar.slider(
        "Maximum position limit",
        min_value=0.10,
        max_value=1.00,
        value=0.35,
        step=0.05
    )
)


alert_percentile = (
    st.sidebar.slider(
        "Risk alert percentile",
        min_value=0.70,
        max_value=0.99,
        value=0.90,
        step=0.01
    )
)


try:

    tickers = parse_ticker_list(
        ticker_text
    )

    weights = parse_float_list(
        weight_text
    )

except ValueError:

    tickers = []
    weights = []


# =========================================================
# HERO
# =========================================================
st.markdown(
    """
    <div class="hero-title">
        Portfolio Performance & Risk Intelligence
    </div>

    <div class="hero-subtitle">
        Performance analytics, explainable risk diagnostics,
        concentration monitoring, stress testing
        and risk-based rebalancing
    </div>
    """,
    unsafe_allow_html=True
)


st.divider()


# =========================================================
# ANALYZE BUTTON
# =========================================================
top1, top2, top3 = st.columns(
    [1, 1, 2]
)


with top1:

    st.metric(
        "Observations",
        len(returns)
    )


with top2:

    if returns:

        st.metric(
            "Average Daily Return",
            f"{np.mean(returns) * 100:.3f}%"
        )

    else:

        st.metric(
            "Average Daily Return",
            "-"
        )


with top3:

    analyze = st.button(
        "Analyze Portfolio",
        type="primary",
        use_container_width=True
    )


# =========================================================
# API ANALYSIS
# =========================================================
if analyze:

    if len(returns) < 2:

        st.error(
            "At least 2 observations "
            "are required."
        )

        st.stop()


    payload = {
        "returns":
            returns,

        "dates":
            dates,

        "tickers":
            tickers,

        "weights":
            weights,

        "position_limit":
            position_limit,

        "alert_percentile":
            alert_percentile
    }


    try:

        response = requests.post(
            ANALYZE_URL,
            json=payload,
            timeout=15
        )


        if response.status_code != 200:

            st.error(
                f"API error "
                f"{response.status_code}"
            )

            st.code(
                response.text
            )

            st.stop()


        st.session_state.result = (
            response.json()
        )

        st.session_state.returns_df = (
            pd.DataFrame({
                "Date": dates,
                "Return": returns
            })
        )


    except requests.RequestException as error:

        st.error(
            str(error)
        )

        st.stop()


# =========================================================
# RESULT
# =========================================================
result = (
    st.session_state.result
)

returns_df = (
    st.session_state.returns_df
)


if (
    result is not None
    and
    returns_df is not None
):

    st.divider()

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================
    st.markdown(
        '<div class="section-title">'
        'Executive Summary'
        '</div>',
        unsafe_allow_html=True
    )


    m1, m2, m3, m4, m5 = (
        st.columns(5)
    )


    with m1:

        st.metric(
            "Total Return",
            pct(
                result["total_return"]
            )
        )


    with m2:

        st.metric(
            "Annualized Return",
            pct(
                result["annual_return"]
            )
        )


    with m3:

        st.metric(
            "Annualized Volatility",
            pct(
                result["volatility"]
            )
        )


    with m4:

        st.metric(
            "Sharpe Ratio",
            f"{result['sharpe']:.2f}"
        )


    with m5:

        st.metric(
            "Maximum Drawdown",
            pct(
                result["max_drawdown"]
            )
        )


    if result["observation_count"] < 252:

        st.warning(
            "Annualized metrics are extrapolated "
            "from fewer than 252 daily observations."
        )


    # =====================================================
    # RISK INTELLIGENCE
    # =====================================================
    st.markdown(
        '<div class="section-title">'
        'Risk Intelligence'
        '</div>',
        unsafe_allow_html=True
    )


    risk = result[
        "risk_assessment"
    ]

    health = result[
        "portfolio_health"
    ]


    r1, r2, r3 = st.columns(
        [1, 1, 2]
    )


    with r1:

        level = risk[
            "risk_level"
        ]

        if level == "LOW":

            css_class = (
                "risk-low"
            )

        elif level == "MEDIUM":

            css_class = (
                "risk-medium"
            )

        elif level == "HIGH":

            css_class = (
                "risk-high"
            )

        else:

            css_class = (
                "risk-na"
            )

        st.caption(
            "Relative Risk Level"
        )

        st.markdown(
            f'<div class="{css_class}">'
            f'{level}'
            '</div>',
            unsafe_allow_html=True
        )


    with r2:

        st.caption(
            "Portfolio Health"
        )

        if health["score"] is None:

            st.metric(
                "Internal Score",
                "N/A"
            )

        else:

            st.metric(
                "Internal Score",
                f"{health['score']:.1f} / 100"
            )


    with r3:

        st.caption(
            "Methodology"
        )

        st.info(
            risk["methodology"]
        )


    # =====================================================
    # ALERTS
    # =====================================================
    st.subheader(
        "Risk Alerts"
    )


    for alert in result["alerts"]:

        if (
            alert["severity"]
            == "WARNING"
        ):

            st.warning(
                alert["message"]
            )

        elif (
            alert["severity"]
            == "OK"
        ):

            st.success(
                alert["message"]
            )

        else:

            st.info(
                alert["message"]
            )


    # Concentration alerts
    concentration = result[
        "concentration"
    ]

    if concentration:

        for alert in (
            concentration["alerts"]
        ):

            st.warning(
                alert["message"]
            )


    # =====================================================
    # EXPLANATION
    # =====================================================
    st.subheader(
        "Explainable Assessment"
    )


    for explanation in (
        result["explanation"]
    ):

        st.write(
            f"• {explanation}"
        )


    # =====================================================
    # TABS
    # =====================================================
    tab1, tab2, tab3, tab4, tab5 = (
        st.tabs([
            "Performance",
            "Risk",
            "Concentration & Rebalance",
            "Stress Test",
            "Data & API"
        ])
    )


    # =====================================================
    # TAB 1 PERFORMANCE
    # =====================================================
    with tab1:

        st.subheader(
            "Cumulative Performance"
        )


        perf_df = pd.DataFrame({
            "Date":
                returns_df["Date"],

            "Portfolio Index":
                [
                    value * 100
                    for value
                    in result[
                        "cumulative_performance"
                    ]
                ]
        })


        perf_df, perf_x = (
            create_time_x(
                perf_df
            )
        )


        chart = (
            alt.Chart(
                perf_df
            )
            .mark_line(
                point=False,
                strokeWidth=2.5
            )
            .encode(
                x=perf_x,

                y=alt.Y(
                    "Portfolio Index:Q",
                    title="Growth Index",
                    scale=alt.Scale(
                        zero=False
                    )
                ),

                tooltip=[
                    "Date",
                    alt.Tooltip(
                        "Portfolio Index:Q",
                        format=".2f"
                    )
                ]
            )
            .properties(
                height=400
            )
            .interactive()
        )


        st.altair_chart(
            chart,
            use_container_width=True
        )


        st.caption(
            "Portfolio index starts near 100. "
            "Values above 100 indicate growth."
        )


        st.subheader(
            "Daily Returns"
        )


        daily_df = (
            returns_df.copy()
        )

        daily_df[
            "Return (%)"
        ] = (
            daily_df["Return"]
            * 100
        )


        daily_df, daily_x = (
            create_time_x(
                daily_df
            )
        )


        daily_chart = (
            alt.Chart(
                daily_df
            )
            .mark_bar()
            .encode(
                x=daily_x,

                y=alt.Y(
                    "Return (%):Q",
                    title="Daily Return (%)"
                ),

                tooltip=[
                    "Date",
                    alt.Tooltip(
                        "Return (%):Q",
                        format=".2f"
                    )
                ]
            )
            .properties(
                height=300
            )
        )


        st.altair_chart(
            daily_chart,
            use_container_width=True
        )


    # =====================================================
    # TAB 2 RISK
    # =====================================================
    with tab2:

        st.subheader(
            "Drawdown"
        )


        dd_df = pd.DataFrame({
            "Date":
                returns_df["Date"],

            "Drawdown (%)":
                [
                    value * 100
                    for value
                    in result[
                        "drawdown_series"
                    ]
                ]
        })


        dd_df, dd_x = (
            create_time_x(
                dd_df
            )
        )


        dd_area = (
            alt.Chart(
                dd_df
            )
            .mark_area(
                opacity=0.2
            )
            .encode(
                x=dd_x,

                y=alt.Y(
                    "Drawdown (%):Q",
                    title="Drawdown (%)"
                )
            )
        )


        dd_line = (
            alt.Chart(
                dd_df
            )
            .mark_line(
                strokeWidth=2
            )
            .encode(
                x=dd_x,

                y="Drawdown (%):Q",

                tooltip=[
                    "Date",
                    alt.Tooltip(
                        "Drawdown (%):Q",
                        format=".2f"
                    )
                ]
            )
        )


        st.altair_chart(
            dd_area + dd_line,
            use_container_width=True
        )


        st.subheader(
            "Return Distribution"
        )


        hist_df = (
            returns_df.copy()
        )

        hist_df[
            "Return (%)"
        ] = (
            hist_df["Return"]
            * 100
        )


        histogram = (
            alt.Chart(
                hist_df
            )
            .mark_bar()
            .encode(
                x=alt.X(
                    "Return (%):Q",
                    bin=alt.Bin(
                        maxbins=30
                    ),
                    title="Daily Return (%)"
                ),

                y=alt.Y(
                    "count()",
                    title="Frequency"
                )
            )
            .properties(
                height=300
            )
        )


        st.altair_chart(
            histogram,
            use_container_width=True
        )


        # Health Score Components
        st.subheader(
            "Portfolio Health Components"
        )


        if (
            health["components"]
            is not None
        ):

            components = (
                health["components"]
            )


            h1, h2, h3, h4 = (
                st.columns(4)
            )


            with h1:

                st.metric(
                    "Stability",
                    (
                        f"{components['stability']:.1f}"
                    )
                )


            with h2:

                st.metric(
                    "Drawdown Resilience",
                    (
                        f"{components['drawdown_resilience']:.1f}"
                    )
                )


            with h3:

                st.metric(
                    "Return Consistency",
                    (
                        f"{components['return_consistency']:.1f}"
                    )
                )


            with h4:

                st.metric(
                    "Risk-adjusted Performance",
                    (
                        f"{components['risk_adjusted_performance']:.1f}"
                    )
                )


            st.caption(
                health[
                    "methodology"
                ]
            )

        else:

            st.info(
                health[
                    "methodology"
                ]
            )


    # =====================================================
    # TAB 3 CONCENTRATION + REBALANCE
    # =====================================================
    with tab3:

        if concentration is None:

            st.info(
                "Provide portfolio tickers "
                "and weights to enable "
                "concentration analysis."
            )

        else:

            st.subheader(
                "Concentration Analysis"
            )


            c1, c2, c3, c4 = (
                st.columns(4)
            )


            largest = (
                concentration[
                    "largest_position"
                ]
            )


            with c1:

                st.metric(
                    "Largest Position",
                    largest[
                        "ticker"
                    ],
                    (
                        f"{largest['weight'] * 100:.1f}%"
                    )
                )


            with c2:

                st.metric(
                    "Top 3 Weight",
                    (
                        f"{concentration['top3_weight'] * 100:.1f}%"
                    )
                )


            with c3:

                st.metric(
                    "HHI",
                    (
                        f"{concentration['hhi']:.3f}"
                    )
                )


            with c4:

                st.metric(
                    "Effective Assets",
                    (
                        f"{concentration['effective_number_of_assets']:.2f}"
                    )
                )


            allocation_df = (
                pd.DataFrame({
                    "Ticker":
                        tickers,

                    "Weight (%)":
                        [
                            weight * 100
                            for weight
                            in weights
                        ]
                })
            )


            allocation_chart = (
                alt.Chart(
                    allocation_df
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Ticker:N",
                        title=None
                    ),

                    y=alt.Y(
                        "Weight (%):Q",
                        title="Weight (%)"
                    ),

                    tooltip=[
                        "Ticker",
                        alt.Tooltip(
                            "Weight (%):Q",
                            format=".2f"
                        )
                    ]
                )
                .properties(
                    height=300
                )
            )


            st.altair_chart(
                allocation_chart,
                use_container_width=True
            )


            st.subheader(
                "Risk-based Rebalancing"
            )


            st.caption(
                "This rule-based recommendation "
                "only enforces the user-defined "
                "position limit. It is not "
                "Max-Sharpe optimization."
            )


            if st.button(
                "Generate Risk-based Rebalance",
                use_container_width=True
            ):

                rebalance_payload = {
                    "tickers":
                        tickers,

                    "weights":
                        weights,

                    "position_limit":
                        position_limit
                }


                try:

                    response = requests.post(
                        REBALANCE_URL,
                        json=rebalance_payload,
                        timeout=10
                    )


                    if response.status_code != 200:

                        st.error(
                            response.text
                        )

                    else:

                        rebalance = (
                            response.json()
                        )


                        st.info(
                            rebalance[
                                "message"
                            ]
                        )


                        rebalance_df = (
                            pd.DataFrame({
                                "Ticker":
                                    tickers,

                                "Current (%)":
                                    [
                                        rebalance[
                                            "original_weights"
                                        ][ticker]
                                        * 100
                                        for ticker
                                        in tickers
                                    ],

                                "Suggested (%)":
                                    [
                                        rebalance[
                                            "suggested_weights"
                                        ][ticker]
                                        * 100
                                        for ticker
                                        in tickers
                                    ],

                                "Change (pp)":
                                    [
                                        rebalance[
                                            "changes"
                                        ][ticker]
                                        * 100
                                        for ticker
                                        in tickers
                                    ]
                            })
                        )


                        st.dataframe(
                            rebalance_df,
                            use_container_width=True,
                            hide_index=True
                        )


                except requests.RequestException as error:

                    st.error(
                        str(error)
                    )


    # =====================================================
    # TAB 4 STRESS TEST
    # =====================================================
    with tab4:

        st.subheader(
            "Scenario Stress Test"
        )


        portfolio_value = (
            st.number_input(
                "Portfolio Value",
                min_value=1.0,
                value=100000000.0,
                step=1000000.0
            )
        )


        shock_text = (
            st.text_input(
                "Market / Portfolio Shocks",
                "-0.05,-0.10,-0.20"
            )
        )


        use_beta = (
            st.checkbox(
                "Use beta-adjusted market shocks"
            )
        )


        beta = None


        if use_beta:

            beta = st.number_input(
                "Portfolio Beta",
                value=1.0,
                step=0.05
            )


        if st.button(
            "Run Stress Test",
            use_container_width=True
        ):

            try:

                shocks = parse_float_list(
                    shock_text
                )


                payload = {
                    "portfolio_value":
                        portfolio_value,

                    "scenario_shocks":
                        shocks,

                    "beta":
                        beta
                }


                response = requests.post(
                    STRESS_URL,
                    json=payload,
                    timeout=10
                )


                if response.status_code != 200:

                    st.error(
                        response.text
                    )

                else:

                    stress = (
                        response.json()
                    )


                    rows = []


                    for scenario in (
                        stress["scenarios"]
                    ):

                        rows.append({
                            "Market Shock (%)":
                                scenario[
                                    "market_shock"
                                ] * 100,

                            "Estimated Portfolio Shock (%)":
                                scenario[
                                    "portfolio_shock"
                                ] * 100,

                            "Estimated Gain/Loss":
                                scenario[
                                    "estimated_loss_or_gain"
                                ],

                            "Estimated Portfolio Value":
                                scenario[
                                    "estimated_portfolio_value"
                                ]
                        })


                    stress_df = (
                        pd.DataFrame(
                            rows
                        )
                    )


                    st.dataframe(
                        stress_df,
                        use_container_width=True,
                        hide_index=True
                    )


                    st.caption(
                        stress[
                            "methodology"
                        ]
                    )


            except ValueError:

                st.error(
                    "Invalid scenario shocks."
                )


            except requests.RequestException as error:

                st.error(
                    str(error)
                )


    # =====================================================
    # TAB 5 DATA/API
    # =====================================================
    with tab5:

        st.subheader(
            "Raw Portfolio Data"
        )


        display_df = (
            returns_df.copy()
        )

        display_df[
            "Return (%)"
        ] = (
            display_df[
                "Return"
            ] * 100
        )


        st.dataframe(
            display_df[
                [
                    "Date",
                    "Return (%)"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


        with st.expander(
            "View API Response"
        ):

            st.json(
                result
            )