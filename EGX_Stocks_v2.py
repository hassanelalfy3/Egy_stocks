import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import pytz

# --- إعدادات المنطقة الزمنية (القاهرة) ---
CAIRO_TZ = pytz.timezone('Africa/Cairo')

# --- إعدادات التلجرام ---
BOT_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
DEFAULT_CHAT_ID = "1978337209"

def get_cairo_now():
    return datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M:%S")

def send_alert(msg, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    except: pass

def create_chart(df, ticker, rsi_val, tf):
    df.index = df.index.tz_convert(CAIRO_TZ)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=(f'{ticker} ({tf}) - Cairo Time', 'RSI'), row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='yellow', width=2), name='VWAP'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=rsi_val, line_dash="dash", line_color="red", row=2, col=1)
    fig.update_layout(height=500, template='plotly_dark', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def check_strategy(ticker, r_len, r_thresh, tf):
    try:
        period_map = {"1m": "1d", "5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d"}
        df = yf.download(ticker, period=period_map.get(tf, "5d"), interval=tf, progress=False, multi_level_index=False)
        
        # Fallback للبيانات المفقودة
        if df.empty or len(df) < r_len:
            df = yf.download(ticker, period="60d", interval="1h", progress=False, multi_level_index=False)
            if df.empty: return "⚠️ No Data", 0.0, 0.0, None, None, "N/A"

        df.columns = [str(c).capitalize() for c in df.columns]
        df['VWAP'] = ta.vwap(high=df.High, low=df.Low, close=df.Close, volume=df.Volume)
        df['RSI'] = ta.rsi(close=df.Close, length=r_len)
        df.dropna(subset=['VWAP', 'RSI'], inplace=True)
        
        if df.empty: return "⚠️ Market Closed", 0.0, 0.0, None, None, "N/A"

        # توقيت القاهرة بصيغتين: واحدة للترتيب (Timestamp) وواحدة للعرض (String)
        raw_time = df.index[-1].astimezone(CAIRO_TZ)
        display_time = raw_time.strftime("%d/%m %H:%M")
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        is_match = (last['Close'] > last['VWAP']) and (prev['Close'] <= prev['VWAP']) and (last['RSI'] > r_thresh)
        status = "🎯 MATCH" if is_match else "❌ No Match"
        
        return status, round(float(last['Close']), 2), round(float(last['RSI']), 1), df, raw_time, display_time
    except:
        return "Error", 0.0, 0.0, None, None, "N/A"

# --- UI ---
st.set_page_config(page_title="Sorted Sniper Cairo", layout="wide")
st.title(f"🎯 Cairo Sniper | {get_cairo_now()}")

st.sidebar.header("📱 User Access")
active_id = st.sidebar.text_input("Telegram Chat ID:", value=DEFAULT_CHAT_ID)

st.sidebar.header("⚙️ Settings")
p_tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h"], index=1)
p_rsi_len = st.sidebar.number_input("RSI Length", 2, 50, 14)
p_rsi_thresh = st.sidebar.slider("RSI Threshold", 10, 90, 50)
p_interval = st.sidebar.select_slider("Refresh (Sec)", options=[30, 60, 120, 300], value=60)

st.sidebar.markdown("---")
tickers_input = st.sidebar.text_area("Tickers:", "GC=F, NVDA, BTC-USD, COMI.CA, FWRY.CA, ETH-USD, AAPL")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

if st.session_state.active:
    st.info("📊 Sorting by most recent data first...")
    table_placeholder = st.empty()
    charts_area = st.container()

    while True:
        results = []
        for ticker in SCAN_LIST:
            status, price, rsi_val, df_full, raw_ts, display_time = check_strategy(ticker, p_rsi_len, p_rsi_thresh, p_tf)
            
            results.append({
                "Ticker": ticker, 
                "Status": status, 
                "Price": price, 
                "RSI": rsi_val, 
                "Last Candle (Cairo)": display_time,
                "_internal_ts": raw_ts # حقل مخفي للترتيب فقط
            })
            
            if status == "🎯 MATCH":
                with charts_area:
                    st.plotly_chart(create_chart(df_full, ticker, p_rsi_thresh, p_tf), use_container_width=True)
                send_alert(f"🎯 *MATCH!*\nAsset: {ticker}\nPrice: {price}\nTime: {display_time} Cairo", active_id)

        # تحويل النتائج لـ DataFrame وترتيبها
        df_results = pd.DataFrame(results)
        
        # الترتيب: الأحدث أولاً (الأصول التي ليس لها وقت N/A تنزل للأسفل)
        df_results = df_results.sort_values(by="_internal_ts", ascending=False).drop(columns=["_internal_ts"])

        table_placeholder.table(df_results)
        time.sleep(p_interval)
        st.rerun()
