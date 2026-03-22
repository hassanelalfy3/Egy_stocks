import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
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
    # صوت تنبيه قصير
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    html_string = f"""
        <audio autoplay>
          <source src="{sound_url}" type="audio/mp3">
        </audio>
    """
    # استخدام placeholder لضمان عدم بقاء الـ HTML في الصفحة
    sound_placeholder = st.empty()
    sound_placeholder.markdown(html_string, unsafe_allow_html=True)
    time.sleep(1)
    sound_placeholder.empty()

# --- منطق الاستراتيجية ---
def run_scalping_scan(ticker):
    try:
        # جلب بيانات 5 دقائق
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 30: return None
        
        # تنظيف البيانات
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # حساب المؤشرات
        df['VWAP'] = ta.vwap(df.High, df.Low, df.Close, df.Volume)
        df['RSI'] = ta.rsi(df.Close, length=14)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # الشروط: اختراق VWAP للأعلى و RSI > 50
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
        st.error(f"Error scanning {ticker}: {e}")
    return None

# --- واجهة Streamlit ---
st.set_page_config(page_title="EGX AI Sniper", page_icon="🎯", layout="wide")
st.title("EGX AI Sniper Scanner 🎯")

SCAN_LIST = ["COMI.CA", "FWRY.CA", "TMGH.CA", "SWDY.CA", "ESRS.CA", "ABUK.CA", "EKHO.CA", "ETEL.CA", "AMOC.CA", "PHDC.CA"]

# تهيئة حالة البرنامج (Session State)
if 'running' not in st.session_state:
    st.session_state.running = False

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🚀 Start Auto Scan"):
        st.session_state.running = True

if st.session_state.running:
    st.info("Scanner is active. Don't forget to keep this tab open.")
    
    # أماكن العرض
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    countdown_placeholder = st.empty()
    results_area = st.container()

    while True:
        with status_placeholder:
            st.info(f"🔍 Last Scan Started at: {datetime.now().strftime('%H:%M:%S')}")
        
        hits = []
        for t in SCAN_LIST:
            result = run_scalping_scan(t)
            if result:
                hits.append(result)
        
        if hits:
            play_sound()
            alert_msg = "🎯 *EGX Scalping Alert!*\n\n"
            for h in hits:
                alert_msg += f"✅ *{h['Ticker']}*\nPrice: {h['Price']}\nRSI: {h['RSI']}\nTime: {h['Time']}\n---\n"
            
            send_telegram_msg(alert_msg)
            with results_area:
                st.success(f"🚨 New Signals Found!")
                st.table(hits)
        else:
            with results_area:
                st.write(f"No signals at {datetime.now().strftime('%H:%M:%S')}. Waiting for next cycle...")

        # --- العداد التنازلي المرئي ---
        total_wait = 300 # 5 دقائق
        for i in range(total_wait, 0, -1):
            mins, secs = divmod(i, 60)
            countdown_placeholder.metric("⏳ Next Scan In", f"{mins:02d}:{secs:02d}")
            
            # تحديث شريط التقدم
            progress = (total_wait - i) / total_wait
            progress_bar.progress(progress)
            
            time.sleep(1)
            
        # إعادة تشغيل السكريبت لبدء دورة جديدة
        st.rerun()
