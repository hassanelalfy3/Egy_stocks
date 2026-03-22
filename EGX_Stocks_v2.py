import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# --- إعدادات تلجرام (يجب ملؤها) ---
TELEGRAM_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
TELEGRAM_CHAT_ID = "1978337209"

def send_telegram_msg(message):
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN": return # تخطي إذا لم يتم الضبط
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

# --- منطق الاستراتيجية (Scalper 5m) ---
def run_scalping_scan(ticker):
    try:
        # جلب بيانات فاصل 5 دقائق لآخر يومين
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 30: return None
        
        # تنظيف الأعمدة (Flatten MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # حساب المؤشرات باستخدام pandas_ta
        df['VWAP'] = ta.vwap(df.High, df.Low, df.Close, df.Volume)
        df['RSI'] = ta.rsi(df.Close, length=14)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # شروط الاستراتيجية:
        # 1. السعر يخترق VWAP للأعلى (السعر الحالي > VWAP والسعر السابق كان < VWAP)
        # 2. RSI حالياً فوق 50
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
st.title("EGX AI Sniper Scanner 🎯")

# قائمة الأسهم للمسح (يمكنك إضافة كل أسهم السوق)
SCAN_LIST = ["COMI.CA", "FWRY.CA", "TMGH.CA", "SWDY.CA", "ESRS.CA", "ABUK.CA", "EKHO.CA", "ETEL.CA", "AMOC.CA", "PHDC.CA"]

if st.button("🚀 Start 5-Min Auto Scan"):
    st.warning("Scanner is running... keep this page open.")
    placeholder = st.empty()
    
    while True:
        hits = []
        with st.spinner("Scanning EGX for Scalping opportunities..."):
            for t in SCAN_LIST:
                result = run_scalping_scan(t)
                if result:
                    hits.append(result)
        
        if hits:
            alert_msg = "🎯 *EGX Scalping Alert!*\n\n"
            for h in hits:
                alert_msg += f"✅ *{h['Ticker']}*\nPrice: {h['Price']}\nRSI: {h['RSI']}\nTime: {h['Time']}\n---\n"
            
            send_telegram_msg(alert_msg)
            st.success(f"Alert sent for: {[h['Ticker'] for h in hits]}")
        else:
            st.info(f"Scan complete at {datetime.now().strftime('%H:%M:%S')} - No signals found.")
            
        # الانتظار لمدة 5 دقائق (300 ثانية)
        time.sleep(300)
        st.rerun()
