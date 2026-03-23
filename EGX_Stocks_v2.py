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
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def create_chart(df, ticker, rsi_val):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    # السعر و VWAP
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'), row=1, col=1)
    # RSI وخط العتبة
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=rsi_val, line_dash="dash", line_color="red", row=2, col=1)
    fig.update_layout(height=500, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

# الدالة الآن تأخذ المتغيرات كمدخلات إجبارية
def check_strategy(ticker, r_len, r_thresh):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        if df.empty or len(df) < r_len + 5: return "⚠️ No Data", 0, 0, None

        df.columns = [str(c).capitalize() for c in df.columns]
        
        # حساب المؤشرات بناءً على البارامترات المختارة
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=r_len) # استخدام r_len هنا
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # شرط الاستراتيجية المربوط بالبارامترات
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
        
        status = "🎯 MATCH" if is_match else "❌ No Match"
        return status, round(last['Close'], 2), round(last['RSI'], 1), df
    except:
        return "Error", 0, 0, None

# --- UI ---
st.set_page_config(page_title="Strategy Sniper", layout="wide")

# القائمة الجانبية مع القيم
st.sidebar.header("⚙️ Strategy Settings")
p_rsi_len = st.sidebar.number_input("RSI Length (Period)", 2, 50, 14)
p_rsi_thresh = st.sidebar.slider("RSI Entry Threshold", 10, 90, 50)
p_interval = st.sidebar.selectbox("Refresh Every (Seconds)", [30, 60, 120, 300], index=2)

st.sidebar.markdown("---")
tickers_input = st.sidebar.text_area("Tickers:", "GC=F, NVDA, TSLA, COMI.CA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

if st.session_state.active:
    status_header = st.empty()
    table_placeholder = st.empty()
    charts_area = st.container()

    while True:
        status_header.warning(f"🔍 Active Scan | RSI: {p_rsi_len} | Threshold: > {p_rsi_thresh}")
        
        results = []
        for ticker in SCAN_LIST:
            # تمرير البارامترات المختارة للدالة
            status, price, rsi_now, df_full = check_strategy(ticker, p_rsi_len, p_rsi_thresh)
            
            results.append({"Ticker": ticker, "Status": status, "Price": price, "RSI": rsi_now})
            
            if status == "🎯 MATCH":
                with charts_area:
                    st.success(f"🚀 SIGNAL: {ticker} matched strategy!")
                    st.plotly_chart(create_chart(df_full, ticker, p_rsi_thresh))
                    send_alert(f"🎯 *MATCH!*\n{ticker} @ {price}\nRSI: {rsi_now}\nParams: RSI({p_rsi_len})>{p_rsi_thresh}")

        table_placeholder.table(pd.DataFrame(results))
        time.sleep(p_interval)
        st.rerun()
