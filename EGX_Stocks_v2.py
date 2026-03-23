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

# --- Config ---
CAIRO_TZ = pytz.timezone('Africa/Cairo')
BOT_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
DEFAULT_CHAT_ID = "1978337209"

# --- Strategy Logic ---

def strategy_vwap_rsi(df, r_len, r_thresh):
    df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
    df['RSI'] = ta.rsi(close=df.Close, length=r_len)
    df.dropna(inplace=True)
    if len(df) < 2: return False, 0
    last, prev = df.iloc[-1], df.iloc[-2]
    match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
    return match, f"RSI:{round(last['RSI'], 1)}"

def strategy_ma_cross(df, fast_p, slow_p):
    df['Fast'] = ta.sma(df.Close, length=fast_p)
    df['Slow'] = ta.sma(df.Close, length=slow_p)
    df.dropna(inplace=True)
    if len(df) < 2: return False, 0
    last, prev = df.iloc[-1], df.iloc[-2]
    match = (last['Fast'] > last['Slow']) and (prev['Fast'] <= prev['Slow'])
    return match, f"F:{round(last['Fast'],1)}/S:{round(last['Slow'],1)}"

def strategy_bollinger(df, b_len, b_std):
    bb = ta.bbands(df.Close, length=b_len, std=b_std)
    df = pd.concat([df, bb], axis=1)
    df.dropna(inplace=True)
    if len(df) < 2: return False, 0
    last, prev = df.iloc[-1], df.iloc[-2]
    # شراء عند اختراق السعر للنطاق السفلي لأعلى
    match = (last['Close'] > df.iloc[-1][f'BBL_{b_len}_{b_std}.0']) and (prev['Close'] <= df.iloc[-2][f'BBL_{b_len}_{b_std}.0'])
    return match, f"Price > Lower Band"

# --- Helper Functions ---

def send_alert(msg, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    except: pass

def get_data(ticker, tf):
    period_map = {"1m": "1d", "5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d"}
    df = yf.download(ticker, period=period_map.get(tf, "5d"), interval=tf, progress=False, multi_level_index=False)
    if not df.empty: df.columns = [str(c).capitalize() for c in df.columns]
    return df

# --- UI Layout ---
st.set_page_config(page_title="Dynamic Strategy Sniper", layout="wide")
st.title(f"🚀 Multi-Strategy Engine | {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')}")

# --- SIDEBAR: DYNAMIC PARAMETERS ---
st.sidebar.header("🎯 Strategy Selection")
selected_strat = st.sidebar.selectbox("Active Strategy:", 
    ["VWAP + RSI Breakout", "MA Golden Cross", "Bollinger Band Reversal"])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Parameters")

# مدخلات ديناميكية بناءً على الاختيار
params = {}
if selected_strat == "VWAP + RSI Breakout":
    params['rsi_len'] = st.sidebar.number_input("RSI Period", 2, 50, 14)
    params['rsi_thresh'] = st.sidebar.slider("RSI Entry Threshold", 10, 90, 50)
elif selected_strat == "MA Golden Cross":
    params['fast_ma'] = st.sidebar.number_input("Fast MA Period", 2, 50, 9)
    params['slow_ma'] = st.sidebar.number_input("Slow MA Period", 10, 200, 21)
elif selected_strat == "Bollinger Band Reversal":
    params['bb_len'] = st.sidebar.number_input("BB Period", 5, 50, 20)
    params['bb_std'] = st.sidebar.slider("Standard Deviation", 1.0, 4.0, 2.0, 0.5)

st.sidebar.markdown("---")
p_tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h"], index=1)
p_interval = st.sidebar.select_slider("Refresh Interval (Sec)", options=[30, 60, 120, 300], value=60)
active_id = st.sidebar.text_input("Telegram ID:", value=DEFAULT_CHAT_ID)

tickers_input = st.sidebar.text_area("Tickers:", "GC=F, NVDA, BTC-USD, COMI.CA, ETH-USD")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start Engine"): st.session_state.active = True
if c2.button("🛑 Stop Engine"): st.session_state.active = False

# --- ENGINE LOGIC ---
if st.session_state.active:
    st.info(f"🛰️ Scanner Active: **{selected_strat}** | Cairo Time Sorting")
    table_placeholder = st.empty()

    while True:
        results = []
        for ticker in SCAN_LIST:
            df = get_data(ticker, p_tf)
            if df.empty: continue
            
            match, indicator_info = False, "N/A"
            
            # تنفيذ الاستراتيجية مع البارامترات الخاصة بها
            if selected_strat == "VWAP + RSI Breakout":
                match, indicator_info = strategy_vwap_rsi(df, params['rsi_len'], params['rsi_thresh'])
            elif selected_strat == "MA Golden Cross":
                match, indicator_info = strategy_ma_cross(df, params['fast_ma'], params['slow_ma'])
            elif selected_strat == "Bollinger Band Reversal":
                match, indicator_info = strategy_bollinger(df, params['bb_len'], params['bb_std'])
            
            raw_ts = df.index[-1].astimezone(CAIRO_TZ)
            display_time = raw_ts.strftime("%d/%m %H:%M")
            
            results.append({
                "Ticker": ticker,
                "Status": "🎯 MATCH" if match else "❌ No Match",
                "Price": round(df.iloc[-1]['Close'], 2),
                "Details": indicator_info,
                "Last Update (Cairo)": display_time,
                "_ts": raw_ts
            })
            
            if match:
                send_alert(f"🎯 *{selected_strat} MATCH!*\nAsset: {ticker}\nPrice: {df.iloc[-1]['Close']}\nTime: {display_time} Cairo", active_id)

        df_res = pd.DataFrame(results).sort_values(by="_ts", ascending=False).drop(columns=["_ts"])
        table_placeholder.table(df_res)
        time.sleep(p_interval)
        st.rerun()
