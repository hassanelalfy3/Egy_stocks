import streamlit as st
from tradingview_ta import TA_Handler, Interval
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import pytz

# --- Configuration ---
CAIRO_TZ = pytz.timezone('Africa/Cairo')
BOT_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
DEFAULT_CHAT_ID = "1978337209"

TV_INTERVALS = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "1d": Interval.INTERVAL_1_DAY
}

# --- Data Engines ---
def get_tv_analysis(symbol, interval_str):
    """ Fast Alerts from TradingView """
    if ".CA" in symbol:
        exch, scr, sym = "EGX", "egypt", symbol.replace(".CA", "")
    elif "GC=F" in symbol:
        exch, scr, sym = "COMEX", "cfd", "GC1!"
    else:
        exch, scr, sym = "NASDAQ", "america", symbol

    try:
        handler = TA_Handler(symbol=sym, exchange=exch, screener=scr, 
                             interval=TV_INTERVALS.get(interval_str), timeout=10)
        return handler.get_analysis()
    except: return None

def get_chart_data(ticker, tf):
    """ Historical Data for Charting Only """
    interval_map = {"1m":"1m", "5m":"5m", "15m":"15m", "1h":"1h", "1d":"1d"}
    period_map = {"1m":"1d", "5m":"5d", "15m":"7d", "1h":"60d", "1d":"max"}
    try:
        df = yf.download(ticker, period=period_map.get(tf, "7d"), 
                         interval=interval_map.get(tf, "15m"), progress=False, multi_level_index=False)
        if not df.empty:
            df.columns = [str(c).capitalize() for c in df.columns]
            # Calculate Indicators for the Chart
            df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
            df['RSI'] = ta.rsi(close=df.Close, length=14)
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- Plotting (Your Custom Logic Added Here) ---
def plot_chart(df, ticker, strategy_name, current_params):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    
    # YOUR STRATEGY VISUALIZATION LOGIC
    if strategy_name == "VWAP + RSI Breakout":
        if 'VWAP' in df.columns: 
            fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name="VWAP", 
                                     line=dict(color='orange', width=2)), row=1, col=1)
        if 'RSI' in df.columns: 
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", 
                                     line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=current_params.get('r_thresh', 50), 
                          line_dash="dash", line_color="red", row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, title=f"Sniper View: {ticker}")
    return fig

# --- UI Setup ---
st.set_page_config(page_title="Sniper TV Pro", layout="wide")
st.sidebar.header("🎯 Strategy Settings")
selected_strat = st.sidebar.selectbox("Signal Logic", ["VWAP + RSI Breakout", "TV Strong Buy"])

params = {}
if selected_strat == "VWAP + RSI Breakout":
    params['r_thresh'] = st.sidebar.slider("RSI Entry Threshold", 10, 90, 50)

p_tf = st.sidebar.selectbox("Timeframe", list(TV_INTERVALS.keys()), index=2)
tickers_input = st.sidebar.text_area("Tickers", "GC=F, COMI.CA, FWRY.CA, NVDA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
if st.sidebar.button("🚀 Start Engine"): st.session_state.active = True
if st.sidebar.button("🛑 Stop"): st.session_state.active = False

# --- Main Engine ---
if st.session_state.active:
    table_placeholder = st.empty()
    chart_container = st.container()

    while True:
        results = []
        matched_tickers = []

        for ticker in SCAN_LIST:
            analysis = get_tv_analysis(ticker, p_tf)
            if not analysis: continue

            # Get values from TradingView
            price = analysis.indicators["close"]
            rsi = analysis.indicators["RSI"]
            vwap = analysis.indicators["VWAP"]
            
            # Logic: Price > VWAP and RSI > Threshold
            match = (price > vwap) and (rsi > params.get('r_thresh', 50))
            
            results.append({
                "Ticker": ticker,
                "Status": "🎯 MATCH" if match else "❌ Wait",
                "Price": round(price, 2),
                "RSI": round(rsi, 1),
                "VWAP": round(vwap, 2)
            })
            if match: matched_tickers.append(ticker)

        # Update Table
        table_placeholder.table(pd.DataFrame(results))

        # Update Charts for Matches
        with chart_container:
            chart_container.empty()
            for t in matched_tickers:
                df_chart = get_chart_data(t, p_tf)
                if not df_chart.empty:
                    st.plotly_chart(plot_chart(df_chart, t, "VWAP + RSI Breakout", params), use_container_width=True)

        time.sleep(60)
        st.rerun()
