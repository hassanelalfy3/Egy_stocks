import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# --- Telegram Config ---
TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
CHAT_ID = "1978337209"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        return response.status_code == 200
    except:
        return False

def create_chart(df, ticker):
    # رسم بياني احترافي
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{ticker} - Price/VWAP', 'RSI (14)'), 
                        row_heights=[0.7, 0.3])
    
    # الشموع
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    # VWAP
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="red", row=2, col=1)

    fig.update_layout(height=600, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def check_strategy(ticker):
    try:
        # جلب البيانات (تأكد من كتابة الرمز بشكل صحيح)
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        
        if df.empty or len(df) < 25: 
            return "⚠️ No Data", 0, 0, None

        # تنظيف البيانات
        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        # المؤشرات
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=14)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # الاستراتيجية
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > 50)
        
        status = "🎯 MATCH" if is_match else "❌ No Match"
        return status, round(last['Close'], 2), round(last['RSI'], 1), df
    except Exception as e:
        return f"Error: {str(e)}", 0, 0, None

# --- UI Layout ---
st.set_page_config(page_title="Scanner Pro", layout="wide")
st.title("🎯 Strategy Monitor: VWAP Crossover & RSI")

# Sidebar
st.sidebar.header("Settings")
if st.sidebar.button("🔔 Test Telegram"):
    send_alert("🔔 Telegram Connection Test: OK!")

tickers_input = st.sidebar.text_area("Tickers:", "GC=F, COMI.CA, FWRY.CA, TMGH.CA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# Main Execution
if st.session_state.active:
    status_text = st.empty()
    table_area = st.empty() # منطقة جدول الحالة
    charts_area = st.container() # منطقة الشارتات

    while True:
        status_text.info(f"🔄 Last Scan: {datetime.now().strftime('%H:%M:%S')}")
        
        all_results = []
        signals_found = []

        for ticker in SCAN_LIST:
            status, price, rsi, df_full = check_strategy(ticker)
            
            # تخزين النتيجة للجدول
            all_results.append({
                "Ticker": ticker,
                "Status": status,
                "Price": price,
                "RSI": rsi,
                "Time": datetime.now().strftime("%H:%M:%S")
            })
            
            # إذا تحقق الشرط، نخزن الداتا لعرض الشارت
            if status == "🎯 MATCH":
                signals_found.append((ticker, price, rsi, df_full))

        # عرض جدول الحالة (سواء كان هناك Match أو لا)
        table_area.table(pd.DataFrame(all_results))

        # عرض الشارتات في منطقة الشارتات
        with charts_area:
            if signals_found:
                for ticker, price, rsi, df_data in signals_found:
                    st.success(f"🚀 Signal Found for {ticker} at {price}!")
                    st.plotly_chart(create_chart(df_data, ticker), use_container_width=True)
                    send_alert(f"🎯 *Signal Found!*\nAsset: {ticker}\nPrice: {price}\nRSI: {rsi}")
            else:
                st.write("⏳ Waiting for a strategy match to show charts...")

        time.sleep(120) 
        st.rerun()
