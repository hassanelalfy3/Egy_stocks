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
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

def create_chart(df, ticker):
    # Create figure with secondary y-axis for RSI
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, subplot_titles=(f'{ticker} 5m - Price & VWAP', 'RSI'), 
                        row_heights=[0.7, 0.3])

    # 1. Candlestick Chart
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)

    # 2. VWAP Line
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='blue', width=2), name='VWAP'), row=1, col=1)

    # 3. RSI Line
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=2), name='RSI'), row=2, col=1)

    # 4. RSI Thresholds (50 line)
    fig.add_hline(y=50, line_dash="dash", line_color="red", row=2, col=1)

    fig.update_layout(height=600, template='plotly_dark', showlegend=False, 
                      xaxis_rangeslider_visible=False)
    return fig

def run_scalping_scan(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        if df.empty or len(df) < 30: return None, None

        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=14)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Strategy Logic
        is_signal = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > 50)
        
        if is_signal:
            result = {"t": ticker, "p": round(float(last['Close']), 2), "rsi": round(last['RSI'], 1)}
            return result, df
    except:
        return None, None
    return None, None

# --- Streamlit UI ---
st.set_page_config(page_title="EGX Chart Sniper", layout="wide", page_icon="📈")
st.title("📈 EGX Sniper with Interactive Charts")

SCAN_LIST = st.sidebar.text_area("Tickers:", "COMI.CA, FWRY.CA, TMGH.CA, SWDY.CA").split(",")
SCAN_LIST = [t.strip().upper() for t in SCAN_LIST if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

if st.sidebar.button("🚀 Start Scan"): st.session_state.active = True
if st.sidebar.button("🛑 Stop"): st.session_state.active = False

if st.session_state.active:
    status = st.empty()
    chart_container = st.container()
    
    while True:
        status.info(f"🔍 Scanning at {datetime.now().strftime('%H:%M:%S')}")
        
        for ticker in SCAN_LIST:
            res, df_data = run_scalping_scan(ticker)
            if res:
                with chart_container:
                    st.success(f"🎯 SIGNAL FOUND: {res['t']} at {res['p']}")
                    # Display the interactive chart
                    st.plotly_chart(create_chart(df_data, res['t']), use_container_width=True)
                    
                send_alert(f"🎯 *Signal Found!*\nStock: {res['t']}\nPrice: {res['p']}\nRSI: {res['rsi']}")
        
        time.sleep(300)
        st.rerun()
