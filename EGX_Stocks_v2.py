import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# --- إعدادات التلجرام ---
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
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, subplot_titles=(f'{ticker} 5m - Price & VWAP', 'RSI'), 
                        row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='cyan', width=2), name='VWAP'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="white", row=2, col=1)
    fig.update_layout(height=400, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def check_strategy(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        if df.empty or len(df) < 25: 
            return "No Data", 0, 0, None

        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=14)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > 50)
        status = "🎯 MATCH" if is_match else "❌ No Match"
        return status, round(last['Close'], 2), round(last['RSI'], 1), df if is_match else None
    except:
        return "Error", 0, 0, None

# --- واجهة Streamlit ---
st.set_page_config(page_title="Universal Sniper", layout="wide")
st.title("🎯 Universal Sniper Board")

# --- القائمة الجانبية (Sidebar) ---
st.sidebar.header("🛠 Control Panel")

# زر اختبار التلجرام
if st.sidebar.button("🔔 Test Telegram Alert"):
    test_msg = "🚨 *Test Alert*\n\nYour bot is connected! Everything is working correctly. 🎯"
    if send_alert(test_msg):
        st.sidebar.success("✅ Test message sent!")
    else:
        st.sidebar.error("❌ Failed to send. Check Token/Chat ID.")

st.sidebar.markdown("---")
user_input = st.sidebar.text_area("Tickers (comma separated):", "GC=F, XAUUSD=X, COMI.CA, FWRY.CA")
SCAN_LIST = [t.strip().upper() for t in user_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("🚀 Start"): st.session_state.active = True
if col_btn2.button("🛑 Stop"): 
    st.session_state.active = False
    st.rerun()

# --- محرك البحث (Main Logic) ---
if st.session_state.active:
    status_header = st.empty()
    table_placeholder = st.empty()
    chart_container = st.container()

    while True:
        status_header.info(f"🔄 Scanning... Last Update: {datetime.now().strftime('%H:%M:%S')}")
        scan_results = []
        
        for ticker in SCAN_LIST:
            status, price, rsi, df_match = check_strategy(ticker)
            scan_results.append({
                "Ticker": ticker,
                "Status": status,
                "Last Price": price,
                "RSI": rsi,
                "Time": datetime.now().strftime("%H:%M:%S")
            })
            
            if "🎯" in status:
                with chart_container:
                    st.success(f"🚀 SIGNAL: {ticker} at {price}")
                    st.plotly_chart(create_chart(df_match, ticker), use_container_width=True)
                send_alert(f"🎯 *Signal Found!*\nAsset: {ticker}\nPrice: {price}\nRSI: {rsi}")

        df_display = pd.DataFrame(scan_results)
        table_placeholder.table(df_display)
        
        time.sleep(120) 
        st.rerun()
