# Real-Time-Stock-Analysis-Dashboard-using-Streamlit 📊

![image](https://github.com/user-attachments/assets/ddbcd241-6021-41bc-9733-636008e96a94)



## Overview

This **Real-Time Stock Analysis Dashboard** allows users to analyze and visualize stock data with various time periods and technical indicators. Built with **Streamlit**, **Plotly**, and **Yahoo Finance (yfinance)**, this dashboard provides a simple interface to explore stock trends, visualize price data, and analyze technical indicators like Simple Moving Averages (SMA) and Exponential Moving Averages (EMA).

## Deployed App Link
🧷 https://real-time-stock-analysis-dashboard-using-app-8w6emdmwat3j66ld3.streamlit.app

## Features

- **Real-Time Stock Prices**: View live stock data for multiple stock symbols (e.g., AAPL, GOOGL, AMZN, MSFT).
- **Dynamic Time Period Selection**: Analyze stock data for different time periods including daily, weekly, monthly, yearly, and maximum data.
- **Customizable Chart Types**: Choose between **Candlestick** or **Line** chart for visualizing stock prices.
- **Technical Indicators**: Add **SMA 20** and **EMA 20** to the chart to assess stock performance trends.
- **Comprehensive Overview**: View key metrics including last price, price change, percentage change, high/low prices, and trading volume.

## Requirements

1. Python 3.x
2. Streamlit
3. Plotly
4. Pandas
5. Yahoo Finance (yfinance)
6. TA-Lib (ta)

## Usage

- **Stock Ticker Input**: Enter the stock symbol (e.g., `AAPL`, `GOOGL`) in the sidebar input box.
- **Time Period**: Choose the time period for the stock data analysis from the available options (`1d`, `1wk`, `1mo`, `1y`, `max`).
- **Chart Type**: Select the chart type for stock visualization (`Candlestick` or `Line`).
- **Technical Indicators**: Add SMA 20 and EMA 20 to the chart by selecting the options in the sidebar.
- **Real-Time Stock Prices**: View the latest stock data for multiple stock symbols in the sidebar.
- **Update Dashboard**: Click the “Update Dashboard” button to refresh and load the stock data with the selected parameters.

## Features Breakdown

### Stock Overview 📈
Displays:
- **Last Price**: The current closing price of the stock.
- **Price Change**: Difference between the most recent and previous close price.
- **Percentage Change**: Percentage change between the latest and previous closing price.
- **High, Low, Volume**: The highest and lowest prices during the selected period and the total trading volume.

### Historical Data 📜
Shows:
- A table of stock data including `Datetime`, `Open`, `High`, `Low`, `Close`, and `Volume` for the selected time period.

### Technical Indicators 📊
Shows:
- **SMA 20**: Simple Moving Average (20-period).
- **EMA 20**: Exponential Moving Average (20-period).

### Real-Time Data 📡
For a list of predefined stock symbols (e.g., `AAPL`, `GOOGL`, `AMZN`, `MSFT`), view:
- The latest price and the change in price.


## Screenshots
![image](https://github.com/user-attachments/assets/56d3b2a5-fc40-42e8-84cf-4622950f7fa6)
![image](https://github.com/user-attachments/assets/517f1fa1-969a-405b-870c-9e6d6ad1cabc)
![image](https://github.com/user-attachments/assets/3f4d635d-50ac-4916-828b-9799fbae3016)

