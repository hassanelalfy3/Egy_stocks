import streamlit as st
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

# --- Strategy Logic ---
def strategy_vwap_rsi(df, r_len, r_thresh):
    df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
    df['RSI'] = ta.rsi(close=df.Close, length=r_len)
    df.dropna(subset=['VWAP', 'RSI'], inplace=True)
    if df.empty or len(df) < 2: return False, "N/A"
    last, prev = df.iloc[-1], df.iloc[-2]
    match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
    return match, f"RSI: {round(last['RSI'], 1)}"

def strategy_ma_cross(df, fast_p, slow_p):
    df['Fast'] = ta.sma(df.Close, length=fast_p)
    df['Slow'] = ta.sma(df.Close, length=slow_p)
    df.dropna(subset=['Fast', 'Slow'], inplace=True)
    if df.empty or len(df) < 2: return False, "N/A"
    last, prev = df.iloc[-1], df.iloc[-2]
    match = (last['Fast'] > last['Slow']) and (prev['Fast'] <= prev['Slow'])
    return match, f"F:{round(last['Fast'],1)}/S:{round(last['Slow'],1)}"

def strategy_bollinger(df, b_len, b_std):
    bb_df = ta.bbands(df.Close, length=b_len, std=b_std)
    if bb_df is None or bb_df.empty: return False, "Error"
    df['L_Band'] = bb_df.iloc[:, 0]
    df['U_Band'] = bb_df.iloc[:, 2]
    df.dropna(subset=['L_Band'], inplace=True)
    if df.empty or len(df) < 2: return False, "N/A"
    last, prev = df.iloc[-1], df.iloc[-2]
    match = (last['Close'] > last['L_Band']) and (prev['Close'] <= prev['L_Band'])
    return match, f"P:{round(last['Close'],2)}"

# --- Data Fetching with History Fallback ---
def get_data_with_fallback(ticker, tf):
    period_map = {
        "1m": "1d", "5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d",
        "1d": "max", "5d": "max", "1M": "max", "3M": "max", "6M": "max", "YTD": "ytd"
    }
    yf_interval_map = {
        "1d": "1d", "5d": "1d", "1M": "1d", "3M": "1d", "6M": "1d", "YTD": "1d",
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h"
    }
    try:
        # Try requested TF
        df = yf.download(ticker, period=period_map.get(tf, "1d"), interval=yf_interval_map.get(tf, "1h"), progress=False, multi_level_index=False)
        # Fallback to Hourly/Daily if empty (Market Closed logic)
        if df.empty or len(df) < 5:
            df = yf.download(ticker, period="60d", interval="1h", progress=False, multi_level_index=False)
        if df.empty:
            df = yf.download(ticker, period="max", interval="1d", progress=False, multi_level_index=False)
            
        if not df.empty:
            df.columns = [str(c).capitalize() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- Plotting ---
def plot_chart(df, ticker, strategy_name, current_params):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    
    if strategy_name == "VWAP + RSI Breakout":
        if 'VWAP' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], name="VWAP", line=dict(color='orange', width=2)), row=1, col=1)
        if 'RSI' in df.columns: 
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=current_params.get('r_thresh', 50), line_dash="dash", line_color="red", row=2, col=1)
    elif strategy_name == "MA Golden Cross":
        if 'Fast' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['Fast'], name="Fast", line=dict(color='cyan')), row=1, col=1)
        if 'Slow' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['Slow'], name="Slow", line=dict(color='magenta')), row=1, col=1)
    elif strategy_name == "Bollinger Band Reversal":
        if 'U_Band' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['U_Band'], name="Upper", line=dict(color='gray')), row=1, col=1)
        if 'L_Band' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['L_Band'], name="Lower", line=dict(color='gray'), fill='tonexty'), row=1, col=1)
        
    fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, title=f"Analysis: {ticker}")
    return fig

# --- UI Setup ---
st.set_page_config(page_title="Sniper Engine Pro", layout="wide")
st.title(f"🎯 Sniper Engine | {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')}")

# SIDEBAR (Restored Telegram & Strategy Params)
st.sidebar.header("📡 Alerts & Connection")
active_id = st.sidebar.text_input("Telegram Chat ID", value=DEFAULT_CHAT_ID)

st.sidebar.header("🎯 Strategy Settings")
selected_strat = st.sidebar.selectbox("Strategy", ["VWAP + RSI Breakout", "MA Golden Cross", "Bollinger Band Reversal"])

params = {}
if selected_strat == "VWAP + RSI Breakout":
    params['r_len'] = st.sidebar.number_input("RSI Period", 2, 50, 14)
    params['r_thresh'] = st.sidebar.slider("RSI Threshold", 10, 90, 50)
elif selected_strat == "MA Golden Cross":
    params['f_ma'] = st.sidebar.number_input("Fast MA", 2, 50, 9)
    params['s_ma'] = st.sidebar.number_input("Slow MA", 10, 200, 21)
elif selected_strat == "Bollinger Band Reversal":
    params['b_len'] = st.sidebar.number_input("BB Period", 5, 50, 20)
    params['b_std'] = st.sidebar.slider("Std Dev", 1.0, 4.0, 2.0, 0.5)

st.sidebar.header("📊 Market Settings")
p_tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d", "5d", "1M", "3M", "6M", "YTD"], index=5)
tickers_input = st.sidebar.text_area("Tickers", "GC=F, COMI.CA, TMGH.CA, HRHO.CA, FWRY.CA, EAST.CA, ETEL.CA, ABUK.CA, ADIB.CA, EFIH.CA, ATLC.CA,AMD")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
p_interval = st.sidebar.select_slider("Refresh (Sec)", options=[30, 60, 120, 300], value=60)

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# --- Main Engine ---
if st.session_state.active:
    st.info(f"🛰️ Active: {selected_strat} | TF: {p_tf}")
    table_placeholder = st.empty()
    chart_container = st.container()

    while True:
        results = []
        matched_data = {}

        for ticker in SCAN_LIST:
            df = get_data_with_fallback(ticker, p_tf)
            if df.empty:
                results.append({"Ticker": ticker, "Status": "⚠️ Invalid", "Price": 0, "Details": "N/A", "Last Update": "N/A", "_ts": pd.Timestamp(0).tz_localize(CAIRO_TZ)})
                continue

            # Run Strategy with restored Params
            match, details = False, "N/A"
            if selected_strat == "VWAP + RSI Breakout":
                match, details = strategy_vwap_rsi(df, params['r_len'], params['r_thresh'])
            elif selected_strat == "MA Golden Cross":
                match, details = strategy_ma_cross(df, params['f_ma'], params['s_ma'])
            elif selected_strat == "Bollinger Band Reversal":
                match, details = strategy_bollinger(df, params['b_len'], params['b_std'])

            if df.empty: continue
            
            raw_ts = df.index[-1]
            if raw_ts.tz is None: raw_ts = raw_ts.tz_localize('UTC').astimezone(CAIRO_TZ)
            else: raw_ts = raw_ts.astimezone(CAIRO_TZ)
            
            if match: matched_data[ticker] = df.copy()

            results.append({
                "Ticker": ticker, "Status": "🎯 MATCH" if match else "❌ No Match",
                "Price": round(float(df.iloc[-1]['Close']), 2), "Details": details,
                "Last Update": raw_ts.strftime("%d/%m %H:%M"), "_ts": raw_ts
            })

            if match:
                msg = f"🎯 *{selected_strat} MATCH!*\nAsset: {ticker}\nPrice: {df.iloc[-1]['Close']}\nTF: {p_tf}\nDetails: {details}"
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": active_id, "text": msg, "parse_mode": "Markdown"})
                except: pass

        # UI Updates
        if results:
            df_table = pd.DataFrame(results).sort_values(by="_ts", ascending=False).drop(columns=["_ts"])
            table_placeholder.table(df_table)

        with chart_container:
            chart_container.empty()
            if not matched_data: st.write("🔭 Scanning for signals...")
            else:
                for t, data in matched_data.items():
                    st.plotly_chart(plot_chart(data, t, selected_strat, params), use_container_width=True, key=f"chart_{t}")
        
        time.sleep(p_interval)
        st.rerun()
