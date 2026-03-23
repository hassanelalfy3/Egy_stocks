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
    except: pass

def create_chart(df, ticker, rsi_level):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{ticker} - Price/VWAP', f'RSI'), 
                        row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=2), name='RSI'), row=2, col=1)
    # خط المستوى الذي اخترته للـ RSI
    fig.add_hline(y=rsi_level, line_dash="dash", line_color="red", row=2, col=1)

    fig.update_layout(height=500, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def check_strategy(ticker, rsi_len, rsi_val):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False, multi_level_index=False)
        if df.empty or len(df) < rsi_len + 5: return "⚠️ No Data", 0, 0, None

        df.columns = [str(c).capitalize() for c in df.columns]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=rsi_len)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # استخدام البارامترات المدخلة
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > rsi_val)
        
        status = "🎯 MATCH" if is_match else "❌ No Match"
        return status, round(last['Close'], 2), round(last['RSI'], 1), df
    except:
        return "Error", 0, 0, None

# --- UI Layout ---
st.set_page_config(page_title="Custom Strategy Sniper", layout="wide")
st.title("🎯 Pro Scanner with Strategy Inputs")

# --- SIDEBAR: STRATEGY PARAMETERS ---
st.sidebar.header("⚙️ Strategy Parameters")
rsi_length = st.sidebar.number_input("RSI Length", min_value=2, max_value=50, value=14)
rsi_threshold = st.sidebar.slider("RSI Threshold (Greater Than)", min_value=10, max_value=90, value=50)
scan_interval = st.sidebar.select_slider("Scan Interval (Seconds)", options=[30, 60, 120, 300], value=120)

st.sidebar.markdown("---")
st.sidebar.header("🔍 Assets")
tickers_input = st.sidebar.text_area("Tickers:", "GC=F, XAUUSD=X, COMI.CA, FWRY.CA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False

c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# --- Main Logic ---
if st.session_state.active:
    status_msg = st.empty()
    table_area = st.empty()
    charts_area = st.container()

    while True:
        status_msg.info(f"🔄 Scanning with RSI({rsi_length}) > {rsi_threshold} | Last: {datetime.now().strftime('%H:%M:%S')}")
        
        all_results = []
        signals = []

        for ticker in SCAN_LIST:
            status, price, rsi_now, df_full = check_strategy(ticker, rsi_length, rsi_threshold)
            
            all_results.append({
                "Ticker": ticker, "Status": status, "Price": price, "RSI": rsi_now, "Time": datetime.now().strftime("%H:%M:%S")
            })
            
            if status == "🎯 MATCH":
                signals.append((ticker, price, rsi_now, df_full))

        table_area.table(pd.DataFrame(all_results))

        with charts_area:
            if signals:
                for t, p, r, d in signals:
                    st.success(f"🚀 Signal: {t} at {p}")
                    st.plotly_chart(create_chart(d, t, rsi_threshold), use_container_width=True)
                    send_alert(f"🎯 *Strategy Match!*\nAsset: {t}\nPrice: {p}\nRSI: {r}\nSettings: RSI({rsi_length}) > {rsi_threshold}")
            else:
                st.write("⏳ Searching for matches...")

        time.sleep(scan_interval) 
        st.rerun()
