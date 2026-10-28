import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import ta

def fetch_stock_data(ticker, period, interval):
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval, multi_level_index=False)
    else:
        data = yf.download(ticker, period=period, interval=interval, multi_level_index=False)
    return data


def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data


def calculate_metrics(data):
    last_close = float(data['Close'].iloc[-1])
    prev_close = float(data['Close'].iloc[0])
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = float(data['High'].max())
    low = float(data['Low'].min())
    volume = int(data['Volume'].sum())
    return last_close, change, pct_change, high, low, volume


def add_technical_indicators(data):
    close_series = data['Close'].squeeze()
    data['SMA_20'] = ta.trend.sma_indicator(close=close_series, window=20)
    data['EMA_20'] = ta.trend.ema_indicator(close=close_series, window=20)
    return data

