import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# --- إعدادات التلجرام الثابتة (البوت) ---
BOT_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
DEFAULT_CHAT_ID = "1978337209"  # معرفك الافتراضي

def send_alert(msg, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    except: pass

def create_chart(df, ticker, rsi_val, tf):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=(f'{ticker} ({tf})', 'RSI'), row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=rsi_val, line_dash="dash", line_color="red", row=2, col=1)
    fig.update_layout(height=500, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def check_strategy(ticker, r_len, r_thresh, tf):
    try:
        period_map = {"1m": "1d", "5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d"}
        fetch_period = period_map.get(tf, "5d")
        
        df = yf.download(ticker, period=fetch_period, interval=tf, progress=False, multi_level_index=False)
        
        if df.empty or len(df) < r_len:
            return "⚠️ No Data", 0, 0, None, "N/A"

        df.columns = [str(c).capitalize() for c in df.columns]
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=r_len)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        if df.empty: return "⚠️ Calculation Error", 0, 0, None, "N/A"

        last = df.iloc[-1]
        prev = df.iloc[-2]
        last_time = df.index[-1].strftime("%H:%M")
        
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
        status = "🎯 MATCH" if is_match else "❌ No Match"
        
        return status, round(last['Close'], 2), round(last['RSI'], 1), df, last_time
    except:
        return "Error", 0, 0, None, "N/A"

# --- UI Layout ---
st.set_page_config(page_title="Multi-User Sniper", layout="wide")
st.title("🎯 Strategy Sniper (Public & Private)")

# --- Sidebar Configuration ---
st.sidebar.header("📱 Notification Settings")

# الخيار الافتراضي مع إمكانية التغيير
active_chat_id = st.sidebar.text_input(
    "Telegram Chat ID:", 
    value=DEFAULT_CHAT_ID, 
    help="Default is your ID. Others can enter theirs to receive alerts."
)

if st.sidebar.button("🔔 Test Connection"):
    send_alert(f"✅ Test Successful! Receiving alerts on: {active_chat_id}", active_chat_id)
    st.sidebar.success(f"Sent to {active_chat_id}")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Settings")
p_tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h"], index=1)
p_rsi_len = st.sidebar.number_input("RSI Length", 2, 50, 14)
p_rsi_thresh = st.sidebar.slider("RSI Threshold", 10, 90, 50)
p_interval = st.sidebar.select_slider("Refresh (Sec)", options=[30, 60, 120, 300], value=60)

st.sidebar.markdown("---")
tickers_input = st.sidebar.text_area("Tickers:", "GC=F, NVDA, TSLA, BTC-USD")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# --- Main Logic ---
if st.session_state.active:
    st.info(f"🛰️ Scanner Active | Target ID: {active_chat_id} | TF: {p_tf}")
    table_placeholder = st.empty()
    charts_area = st.container()

    while True:
        results = []
        for ticker in SCAN_LIST:
            status, price, rsi_now, df_full, last_time = check_strategy(ticker, p_rsi_len, p_rsi_thresh, p_tf)
            results.append({"Ticker": ticker, "Status": status, "Price": price, "RSI": rsi_now, "Last Seen": last_time})
            
            if status == "🎯 MATCH":
                with charts_area:
                    st.plotly_chart(create_chart(df_full, ticker, p_rsi_thresh, p_tf), use_container_width=True)
                send_alert(f"🎯 *MATCH!*\nAsset: {ticker}\nPrice: {price}\nTF: {p_tf}\nTime: {last_time}", active_chat_id)

        table_placeholder.table(pd.DataFrame(results))
        time.sleep(p_interval)
        st.rerun()
