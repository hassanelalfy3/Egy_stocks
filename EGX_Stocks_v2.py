import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import base64
from datetime import datetime

# --- إعدادات تلجرام ---
TELEGRAM_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
TELEGRAM_CHAT_ID = "1978337209"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

# --- وظيفة تشغيل الصوت ---
def play_sound():
    # صوت تنبيه بسيط (يمكنك استبدال الرابط برابط ملف mp3 مباشر)
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    html_string = f"""
        <audio autoplay>
          <source src="{sound_url}" type="audio/mp3">
        </audio>
    """
    sound_container = st.empty()
    sound_container.markdown(html_string, unsafe_allow_html=True)
    time.sleep(2)  # وقت قصير لضمان التشغيل
    sound_container.empty()

# --- منطق الاستراتيجية ---
def run_scalping_scan(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 30: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['VWAP'] = ta.vwap(df.High, df.Low, df.Close, df.Volume)
        df['RSI'] = ta.rsi(df.Close, length=14)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        cross_up_vwap = (last_row['Close'] > last_row['VWAP']) and (prev_row['Close'] <= prev_row['VWAP'])
        rsi_positive = last_row['RSI'] > 50
        
        if cross_up_vwap and rsi_positive:
            return {
                "Ticker": ticker.replace(".CA", ""),
                "Price": round(last_row['Close'], 2),
                "RSI": round(last_row['RSI'], 1),
                "Time": datetime.now().strftime("%H:%M")
            }
    except Exception as e:
        print(f"Error scanning {ticker}: {e}")
    return None

# --- واجهة Streamlit ---
st.set_page_config(page_title="EGX AI Sniper", page_icon="🎯")
st.title("EGX AI Sniper Scanner 🎯")

SCAN_LIST = ["COMI.CA", "FWRY.CA", "TMGH.CA", "SWDY.CA", "ESRS.CA", "ABUK.CA", "EKHO.CA", "ETEL.CA", "AMOC.CA", "PHDC.CA"]

if st.button("🚀 Start 5-Min Auto Scan"):
    st.warning("Scanner is running... Keep this page open and your sound ON.")
    
    # مكان مخصص لعرض النتائج والعداد
    status_placeholder = st.empty()
    countdown_placeholder = st.empty()
    results_placeholder = st.container()

    while True:
        hits = []
        status_placeholder.info("🔍 Scanning EGX for Scalping opportunities...")
        
        for t in SCAN_LIST:
            result = run_scalping_scan(t)
            if result:
                hits.append(result)
        
        if hits:
            play_sound()  # تشغيل الصوت عند وجود فرص
            alert_msg = "🎯 *EGX Scalping Alert!*\n\n"
            for h in hits:
                alert_msg += f"✅ *{h['Ticker']}*\nPrice: {h['Price']}\nRSI: {h['RSI']}\nTime: {h['Time']}\n---\n"
            
            send_telegram_msg(alert_msg)
            with results_placeholder:
                st.success(f"🚨 Found {len(hits)} signals at {datetime.now().strftime('%H:%M:%S')}")
                st.json(hits)
        else:
            status_placeholder.info(f"✅ Scan complete at {datetime.now().strftime('%H:%M:%S')} - No signals.")

        # --- العداد التنازلي ---
        for i in range(300, 0, -1):
            mins, secs = divmod(i, 60)
            countdown_placeholder.metric("Next Scan In", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
        
        st.rerun()
