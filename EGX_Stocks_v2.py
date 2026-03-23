import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# --- إعدادات تلجرام ---
TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
CHAT_ID = "1978337209"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

def create_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, subplot_titles=(f'{ticker} 5m - Price & VWAP', 'RSI'), 
                        row_heights=[0.7, 0.3])
    # الشموع
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    # VWAP
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='cyan', width=2), name='VWAP'), row=1, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="white", row=2, col=1)
    fig.update_layout(height=500, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def run_universal_scan(ticker):
    try:
        # جلب البيانات
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        if df.empty or len(df) < 30: return None, None

        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        # المؤشرات
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=14)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # استراتيجية الاختراق
        is_signal = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > 50)
        
        if is_signal:
            result = {"t": ticker, "p": round(float(last['Close']), 2), "rsi": round(last['RSI'], 1)}
            return result, df
    except:
        return None, None
    return None, None

# --- الواجهة ---
st.set_page_config(page_title="Universal Sniper", layout="wide")
st.title("🎯 Universal Sniper (Stocks & Gold)")

# مدخلات المستخدم للرموز
st.sidebar.header("Scan List")
st.sidebar.info("Gold: GC=F or XAUUSD=X\nEGX: COMI.CA, etc.")
user_tickers = st.sidebar.text_area("Enter Tickers (comma separated):", "GC=F, COMI.CA, FWRY.CA, TMGH.CA")
SCAN_LIST = [t.strip().upper() for t in user_tickers.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

if st.sidebar.button("🚀 Start Scan"): st.session_state.active = True
if st.sidebar.button("🛑 Stop"): st.session_state.active = False

if st.session_state.active:
    status = st.empty()
    chart_container = st.container()
    
    while True:
        status.info(f"🔍 Scanning {len(SCAN_LIST)} symbols at {datetime.now().strftime('%H:%M:%S')}")
        
        for ticker in SCAN_LIST:
            res, df_data = run_universal_scan(ticker)
            if res:
                with chart_container:
                    st.success(f"🎯 SIGNAL: {res['t']} at {res['p']}")
                    st.plotly_chart(create_chart(df_data, res['t']), use_container_width=True)
                send_alert(f"🎯 *Signal Found!*\nAsset: {res['t']}\nPrice: {res['p']}\nRSI: {res['rsi']}")
        
        time.sleep(120) # فحص كل دقيقتين
        st.rerun()
