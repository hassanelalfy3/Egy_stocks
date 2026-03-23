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

# --- Robust Strategy Logic ---

def strategy_vwap_rsi(df, r_len, r_thresh):
    # حساب المؤشرات
    vwap_series = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
    rsi_series = ta.rsi(close=df.Close, length=r_len)
    
    # دمج وتنظيف
    df['VWAP'] = vwap_series
    df['RSI'] = rsi_series
    df.dropna(subset=['VWAP', 'RSI'], inplace=True)
    
    if len(df) < 2: return False, "N/A"
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # الشرط: اختراق VWAP للأعلى + RSI فوق العتبة
    match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
    return match, f"RSI: {round(last['RSI'], 1)}"

def strategy_ma_cross(df, fast_p, slow_p):
    fast_ma = ta.sma(df.Close, length=fast_p)
    slow_ma = ta.sma(df.Close, length=slow_p)
    
    df['Fast'] = fast_ma
    df['Slow'] = slow_ma
    df.dropna(subset=['Fast', 'Slow'], inplace=True)
    
    if len(df) < 2: return False, "N/A"
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # الشرط: المتوسط السريع يخترق البطيء للأعلى
    match = (last['Fast'] > last['Slow']) and (prev['Fast'] <= prev['Slow'])
    return match, f"F:{round(last['Fast'],1)} / S:{round(last['Slow'],1)}"

def strategy_bollinger(df, b_len, b_std):
    # حساب البولنجر (يعيد 3 أعمدة: Lower, Mid, Upper)
    bb_df = ta.bbands(df.Close, length=b_len, std=b_std)
    if bb_df is None or bb_df.empty: return False, "Err"
    
    # نأخذ اسم أول عمود (Lower Band) مهما كان اسمه
    l_band_col = bb_df.columns[0]
    
    df['L_Band'] = bb_df[l_band_col]
    df.dropna(subset=['L_Band'], inplace=True)
    
    if len(df) < 2: return False, "N/A"
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # الشرط: السعر يخترق النطاق السفلي للأعلى (ارتداد)
    match = (last['Close'] > last['L_Band']) and (prev['Close'] <= prev['L_Band'])
    return match, f"Price: {round(last['Close'], 2)}"

# --- Data Fetching ---

def get_data(ticker, tf):
    period_map = {"1m": "1d", "5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d"}
    try:
        df = yf.download(ticker, period=period_map.get(tf, "5d"), interval=tf, progress=False, multi_level_index=False)
        if df.empty or len(df) < 5:
            # Fallback لفاصل أكبر في حالة عدم وجود بيانات
            df = yf.download(ticker, period="60d", interval="1h", progress=False, multi_level_index=False)
            
        if not df.empty:
            df.columns = [str(c).capitalize() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- UI Setup ---
st.set_page_config(page_title="Stable Sniper Egypt", layout="wide")
st.title(f"🎯 Professional Sniper | Cairo: {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')}")

# Sidebar
st.sidebar.header("🎯 Strategy Selector")
selected_strat = st.sidebar.selectbox("Active Strategy:", 
    ["VWAP + RSI Breakout", "MA Golden Cross", "Bollinger Band Reversal"])

#st.sidebar.markdown("---")
st.sidebar.header("⚙️ Dynamic Parameters")

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

#st.sidebar.markdown("---")
p_tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h"], index=1)
p_interval = st.sidebar.select_slider("Refresh Rate", options=[30, 60, 120, 300], value=60)
active_id = st.sidebar.text_input("Telegram ID:", value=DEFAULT_CHAT_ID)

tickers_input = st.sidebar.text_area("Tickers (Separated by comma):", "GC=F, NVDA, BTC-USD, COMI.CA, FWRY.CA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start Engine"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# --- Logic Engine ---
if st.session_state.active:
    st.info(f"🛰️ Scanner Mode: {selected_strat} | Sorting by Last Update")
    table_placeholder = st.empty()

    while True:
        results = []
        for ticker in SCAN_LIST:
            df = get_data(ticker, p_tf)
            if df.empty: continue
            
            match, details = False, "N/A"
            
            # استدعاء الاستراتيجية المختارة
            if selected_strat == "VWAP + RSI Breakout":
                match, details = strategy_vwap_rsi(df, params['r_len'], params['r_thresh'])
            elif selected_strat == "MA Golden Cross":
                match, details = strategy_ma_cross(df, params['f_ma'], params['s_ma'])
            elif selected_strat == "Bollinger Band Reversal":
                match, details = strategy_bollinger(df, params['b_len'], params['b_std'])
            
            raw_ts = df.index[-1].astimezone(CAIRO_TZ)
            display_time = raw_ts.strftime("%d/%m %H:%M")
            
            results.append({
                "Ticker": ticker,
                "Status": "🎯 MATCH" if match else "❌ No Match",
                "Price": round(df.iloc[-1]['Close'], 2),
                "Indicator Info": details,
                "Last Seen (Cairo)": display_time,
                "_ts": raw_ts
            })
            
            if match:
                alert_msg = f"🎯 *{selected_strat} MATCH!*\nAsset: {ticker}\nPrice: {df.iloc[-1]['Close']}\nTime: {display_time} Cairo"
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                try: requests.post(url, json={"chat_id": active_id, "text": alert_msg, "parse_mode": "Markdown"})
                except: pass

        # ترتيب النتائج بالأحدث أولاً
        df_final = pd.DataFrame(results).sort_values(by="_ts", ascending=False).drop(columns=["_ts"])
        table_placeholder.table(df_final)
        
        time.sleep(p_interval)
        st.rerun()
