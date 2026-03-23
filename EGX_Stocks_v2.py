import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# --- Telegram Config ---
TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
CHAT_ID = "1978337209"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

def run_scalping_scan(ticker):
    try:
        # Fetching 2 days of 5m data
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        
        if df.empty or len(df) < 25:
            return None

        # Clean columns for pandas_ta
        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        # Indicators
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=14)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Strategy: VWAP Cross-Up + RSI > 50
        if (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > 50):
            return {"t": ticker.replace(".CA", ""), "p": round(float(last['Close']), 2), "rsi": round(last['RSI'], 1)}
    except:
        return None
    return None

# --- Streamlit UI ---
st.set_page_config(page_title="EGX Custom Sniper", layout="wide")
st.title("🎯 EGX Custom Sniper")

# --- SIDEBAR: TICKER SELECTION ---
st.sidebar.header("Scan Settings")
default_tickers = "COMI.CA, FWRY.CA, TMGH.CA, SWDY.CA"
user_input = st.sidebar.text_area("Enter Tickers (separated by commas):", value=default_tickers)

# Convert input string to a clean list
SCAN_LIST = [t.strip().upper() for t in user_input.split(",") if t.strip()]

if "active" not in st.session_state:
    st.session_state.active = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Start Scanning Selected"):
        st.session_state.active = True
with col2:
    if st.button("🛑 Stop"):
        st.session_state.active = False
        st.experimental_rerun()

if st.session_state.active:
    st.info(f"Scanning: {', '.join(SCAN_LIST)}")
    status = st.empty()
    timer = st.empty()
    
    while True:
        status.write(f"🔍 Last scan at: {datetime.now().strftime('%H:%M:%S')}")
        
        hits = []
        for ticker in SCAN_LIST:
            res = run_scalping_scan(ticker)
            if res:
                hits.append(res)
        
        if hits:
            st.success(f"Signals Found: {len(hits)}")
            alert_text = "🚀 *Custom Sniper Alert!*\n\n"
            for h in hits:
                alert_text += f"✅ *{h['t']}*\nPrice: {h['p']}\nRSI: {h['rsi']}\n---\n"
            send_alert(alert_text)
            st.table(hits)
        
        # 5 Minute Countdown
        for i in range(300, 0, -1):
            timer.metric("Next Scan In", f"{i//60:02d}:{i%60:02d}")
            time.sleep(1)
        
        st.rerun()
