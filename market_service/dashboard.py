import os
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Market Exposure & Regime', page_icon='📈', layout='wide')
API = os.getenv('MARKET_API_URL', 'http://127.0.0.1:8002').rstrip('/')

@st.cache_data(ttl=300, show_spinner=False)
def api_get(path, params=None):
    response = requests.get(f'{API}{path}', params=params, timeout=90)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=300, show_spinner=False)
def api_post(path, payload):
    response = requests.post(f'{API}{path}', json=payload, timeout=120)
    response.raise_for_status()
    return response.json()

def request_error(exc):
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get('detail', exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f'API trả về HTTP {exc.response.status_code}: {detail}')
    else:
        st.error(f'Không kết nối được API {API}: {exc}')
    st.stop()

st.title('📈 Market Exposure & Regime Dashboard')
st.caption('CAPM / Beta · Momentum · Moving Average · Bull/Bear | Dữ liệu qua FastAPI Market Service')

with st.sidebar:
    st.header('Thiết lập')
    benchmark = st.text_input('Benchmark', value='SPY').strip().upper()
    period = st.selectbox('Khoảng dữ liệu', ['2y', '5y', '1y'], index=0)
    risk_free = st.number_input('Lãi suất phi rủi ro (%/năm)', min_value=0.0, max_value=30.0, value=4.0, step=0.5) / 100
    st.subheader('Tỷ trọng danh mục (%)')
    defaults = {'AAPL': 30, 'MSFT': 30, 'NVDA': 20, 'GOOGL': 20}
    raw = {}
    for ticker, weight in defaults.items():
        raw[ticker] = st.number_input(ticker, min_value=0, max_value=100, value=weight, step=5)
    total = sum(raw.values())
    st.write(f'**Tổng tỷ trọng: {total}%**')
    analyze = st.button('🔍 Analyze Portfolio', type='primary', use_container_width=True)

if not benchmark:
    st.warning('Vui lòng nhập benchmark.')
    st.stop()
if total != 100:
    st.warning('Tổng tỷ trọng phải bằng 100%. Hãy chỉnh lại ở thanh bên trái.')
    st.stop()

# The button triggers a fresh analysis; Streamlit cache limits repeat network requests.
if not analyze and 'analysis_ready' not in st.session_state:
    st.info('Chọn tỷ trọng ở thanh bên trái rồi nhấn **Analyze Portfolio** để bắt đầu.')
    st.stop()
if analyze:
    st.session_state.analysis_ready = True

weights = {ticker: value / 100 for ticker, value in raw.items() if value > 0}
payload = {'weights': weights, 'benchmark': benchmark, 'period': period}

with st.spinner('Đang tải dữ liệu và tính toán...'):
    try:
        exposure = api_post('/market/exposure', payload)
        regime = api_get(f'/market/regime/{benchmark}', {'period': period})
    except requests.RequestException as exc:
        request_error(exc)

beta = float(exposure['portfolio_beta'])
regime_name = regime['regime']
market_label = exposure.get('market_sensitivity', 'N/A')
c1, c2, c3, c4 = st.columns(4)
c1.metric('Portfolio Beta', f'{beta:.3f}')
c2.metric('Market Regime', regime_name)
c3.metric('Market Sensitivity', market_label)
c4.metric('Số phiên lợi suất', exposure.get('observations', 'N/A'))

st.subheader('1. Beta danh mục và mức độ phụ thuộc thị trường')
components = pd.DataFrame(exposure['components'])
components['weight_pct'] = components['weight'] * 100
st.dataframe(components[['ticker', 'weight_pct', 'beta', 'weighted_beta']].rename(columns={
    'ticker': 'Mã', 'weight_pct': 'Tỷ trọng (%)', 'beta': 'Beta', 'weighted_beta': 'Đóng góp Beta'
}), use_container_width=True, hide_index=True)
fig_beta = go.Figure(go.Bar(x=components['ticker'], y=components['beta'], name='Beta'))
fig_beta.add_hline(y=1, line_dash='dash', annotation_text='Beta thị trường = 1')
fig_beta.update_layout(title='Beta từng cổ phiếu so với benchmark', yaxis_title='Beta', height=370)
st.plotly_chart(fig_beta, use_container_width=True)
st.info(f'Beta danh mục = {beta:.3f}. Theo mô hình Beta tuyến tính, nếu {benchmark} thay đổi 1%, danh mục có mức biến động ước tính khoảng {beta:.2f}% cùng chiều, không phải dự báo chắc chắn.')

st.subheader('1.1. Đóng góp Beta của từng cổ phiếu')
fig_contribution = go.Figure(go.Bar(
    x=components['ticker'], y=components['weighted_beta'],
    text=components['weighted_beta'].map(lambda x: f'{x:.3f}'), textposition='outside',
    name='Tỷ trọng × Beta'
))
fig_contribution.update_layout(
    title='Đóng góp vào Beta danh mục (Weight × Beta)',
    xaxis_title='Cổ phiếu', yaxis_title='Đóng góp Beta', height=370
)
st.plotly_chart(fig_contribution, use_container_width=True)
st.caption(f'Tổng đóng góp Beta = {components["weighted_beta"].sum():.3f}; Beta danh mục API = {beta:.3f}. Chênh lệch nhỏ có thể do làm tròn.')

st.subheader('1.2. Market Stress Test — Mô phỏng biến động thị trường')
st.write('Mô phỏng tuyến tính dựa trên Beta danh mục: **Lợi suất danh mục ước tính ≈ Beta × Lợi suất benchmark**.')
scenario_moves = [-20, -10, -5, 5, 10, 20]
scenario_df = pd.DataFrame({
    f'{benchmark} biến động (%)': scenario_moves,
    'Danh mục ước tính (%)': [beta * move for move in scenario_moves],
})
st.dataframe(scenario_df.style.format({
    f'{benchmark} biến động (%)': '{:+.1f}%',
    'Danh mục ước tính (%)': '{:+.2f}%'
}), hide_index=True, use_container_width=True)
fig_stress = go.Figure()
fig_stress.add_trace(go.Bar(x=[f'{v:+d}%' for v in scenario_moves],
                            y=[beta * v for v in scenario_moves],
                            text=[f'{beta * v:+.2f}%' for v in scenario_moves],
                            textposition='outside', name='Danh mục'))
fig_stress.update_layout(title='Tác động ước tính lên danh mục theo từng kịch bản',
                         xaxis_title=f'Biến động {benchmark}', yaxis_title='Lợi suất danh mục (%)', height=380)
st.plotly_chart(fig_stress, use_container_width=True)

scenario = st.slider(f'Tự chọn biến động của {benchmark} (%)',
                     min_value=-30, max_value=30, value=-10, step=1)
impact = beta * scenario
sc1, sc2 = st.columns(2)
sc1.metric(f'{benchmark} giả định', f'{scenario:+d}%')
sc2.metric('Danh mục ước tính', f'{impact:+.2f}%')

st.subheader('1.3. Nhận xét tự động về Market Exposure')
most_exposed = components.loc[components['weighted_beta'].idxmax()]
sensitivity = ('nhạy hơn' if beta > 1.05 else 'ít nhạy hơn' if beta < 0.95 else 'gần tương đương')
st.write(
    f'- **Mức độ nhạy cảm:** Beta = **{beta:.3f}**, danh mục {sensitivity} benchmark {benchmark} '
    f'(so sánh với Beta = 1).\n'
    f'- **Đóng góp Beta lớn nhất:** **{most_exposed["ticker"]}**, '
    f'đóng góp **{most_exposed["weighted_beta"]:.3f}** vào Beta danh mục.\n'
    f'- **Kịch bản đang chọn:** Nếu {benchmark} biến động **{scenario:+d}%**, '
    f'danh mục có mức biến động mô hình **{impact:+.2f}%**.'
)
st.caption('Stress Test chỉ dùng Beta lịch sử, giả định quan hệ tuyến tính và Beta không đổi; '
           'không bao gồm alpha, biến động riêng từng mã, chi phí giao dịch hay sự thay đổi tương quan khi khủng hoảng. '
           'Không phải dự báo hoặc mức lỗ tối đa.')


st.subheader('2. Market Regime: Bull / Bear / Sideways')
r1, r2, r3, r4 = st.columns(4)
r1.metric('Giá cuối', f"{regime['last_close']:.2f}")
r2.metric('SMA50', f"{regime['SMA_50']:.2f}")
r3.metric('SMA200', f"{regime['SMA_200']:.2f}")
r4.metric('Momentum 20 phiên', f"{regime['momentum_20d_pct']:.2f}%")
st.write(f"**Phân loại: {regime_name}** — {regime.get('rule', '')}")

st.subheader('3. Biểu đồ giá và Moving Average')
chart_ticker = st.selectbox('Mã để vẽ biểu đồ', [benchmark] + [t for t in weights if t != benchmark])
try:
    history = api_get(f'/market/history/{chart_ticker}', {'period': period, 'interval': '1d'})
except requests.RequestException as exc:
    request_error(exc)
df = pd.DataFrame(history.get('data', []))
if df.empty or 'Close' not in df.columns:
    st.warning('Không đủ dữ liệu lịch sử để vẽ biểu đồ.')
else:
    date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
    df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=[date_col, 'Close']).sort_values(date_col)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[date_col], y=df['Close'], name='Close', mode='lines'))
    for window in [20, 50, 200]:
        if len(df) >= window:
            fig.add_trace(go.Scatter(x=df[date_col], y=df['Close'].rolling(window).mean(),
                                     name=f'SMA{window}', mode='lines'))
    fig.update_layout(title=f'{chart_ticker} — Close, SMA20, SMA50, SMA200',
                      xaxis_title='Ngày', yaxis_title='Giá (USD)', height=480)
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Các SMA được tính từ dữ liệu Close do API lịch sử trả về. Nếu API lịch sử dùng giá chưa điều chỉnh, các đường này có thể khác SMA của API regime (giá điều chỉnh).')

st.subheader('4. Momentum và CAPM theo từng cổ phiếu')
selected = st.selectbox('Chọn cổ phiếu để phân tích', list(weights))
try:
    momentum = api_get(f'/market/momentum/{selected}', {'period': '1y', 'lookback': 20})
    capm = api_get(f'/market/beta/{selected}', {'benchmark': benchmark, 'period': period, 'risk_free_rate': risk_free})
except requests.RequestException as exc:
    request_error(exc)
m1, m2, m3 = st.columns(3)
m1.metric('Momentum 20 phiên', f"{momentum['momentum_pct']:.2f}%")
m2.metric('Beta cổ phiếu', f"{capm['beta']:.3f}")
m3.metric('CAPM Expected Return', f"{capm['capm_expected_return'] * 100:.2f}%")
st.write(f"Tín hiệu Momentum: **{momentum['signal']}**")
st.caption('CAPM sử dụng lãi suất phi rủi ro nhập ở thanh bên trái và lợi suất thị trường lịch sử quy đổi năm. Đây là ước lượng mô hình, không phải cam kết lợi nhuận.')
st.caption('Dữ liệu Yahoo Finance có thể chậm hoặc thay đổi. Dashboard này phục vụ học tập và demo, không phải khuyến nghị đầu tư.')
