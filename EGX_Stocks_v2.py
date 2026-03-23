import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# --- Settings ---
TELEGRAM_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
TELEGRAM_CHAT_ID = "1978337209"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def play_sound():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    html_string = f'<audio autoplay><source src="{sound_url}" type="audio/mp3"></audio>'
    st.components.v1.html(html_string, height=0)

def run_scalping_scan(ticker):
    try:
        # FIX 1: Force non-multi-index columns
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        
        if df.empty or len(df) < 20:
            return None

        # FIX 2: Flatten columns if they are MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # FIX 3: Ensure data is numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate Indicators
        df['VWAP'] = ta.vwap(df.High, df.Low, df.Close, df.Volume)
        df['RSI'] = ta.rsi(df.Close, length=14)
        
        # Drop rows where indicators couldn't calculate yet
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        if len(df) < 2: return None

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Strategy
        cross_up_vwap = (last_row['Close'] > last_row['VWAP']) and (prev_row['Close'] <= prev_row['VWAP'])
        rsi_positive = last_row['RSI'] > 50
        
        if cross_up_vwap and rsi_positive:
            return {
                "Ticker": ticker.replace(".CA", ""),
                "Price": round(float(last_row['Close']), 2),
                "RSI": round(float(last_row['RSI']), 1),
                "Time": datetime.now().strftime("%H:%M:%S")
            }
    except Exception as e:
        st.error(f"Error in {ticker}: {e}") # This will show the error on screen!
    return None

# --- UI ---
st.set_page_config(page_title="EGX AI Sniper", layout="wide")
st.title("EGX AI Sniper Scanner 🎯")

SCAN_LIST = ["COMI.CA", "FWRY.CA", "TMGH.CA", "SWDY.CA", "ESRS.CA", "ABUK.CA", "EKHO.CA", "ETEL.CA", "AMOC.CA", "PHDC.CA"]

if "running" not in st.session_state:
    st.session_state.running = False

if st.button("🚀 Start Auto Scan"):
    st.session_state.running = True

if st.session_state.running:
    status_msg = st.empty()
    progress_bar = st.progress(0)
    timer_text = st.empty()
    results_area = st.container()

    while True:
        status_msg.info(f"🔍 Scanning symbols at {datetime.now().strftime('%H:%M:%S')}...")
        
        all_hits = []
        for ticker in SCAN_LIST:
            res = run_scalping_scan(ticker)
            if res:
                all_hits.append(res)
        
        with results_area:
            if all_hits:
                play_sound()
                st.success(f"🚨 Found {len(all_hits)} signals!")
                st.table(all_hits)
                msg = "🎯 *EGX Alert!*\n" + "\n".join([f"✅ {h['Ticker']}: {h['Price']}" for h in all_hits])
                send_telegram_msg(msg)
            else:
                st.write(f"No signals at {datetime.now().strftime('%H:%M:%S')}. Waiting...")

        # --- Countdown ---
        wait_time = 300
        for i in range(wait_time, 0, -1):
            timer_text.metric("Next Scan In", f"{i // 60:02d}:{i % 60:02d}")
            progress_bar.progress((wait_time - i) / wait_time)
            time.sleep(1)
        
        # Handle different Streamlit versions for rerun
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
