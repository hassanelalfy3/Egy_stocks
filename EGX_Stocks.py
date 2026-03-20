import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Config
st.set_page_config(page_title="EGX Advisor", layout="wide")

def add_indicators(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # RSI Manual Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands Manual Calculation
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['StdDev'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['SMA20'] + (df['StdDev'] * 2)
    df['Lower_Band'] = df['SMA20'] - (df['StdDev'] * 2)
    return df

st.title("📊 مستشارك الذكي للبورصة المصرية")

egx_list = ["COMI.CA", "FWRY.CA", "TMGH.CA", "SWDY.CA"]
selected_stock = st.sidebar.selectbox("اختر السهم:", egx_list)

df = yf.download(selected_stock, period="1y", interval="1d", progress=False)

if not df.empty and len(df) > 20:
    df = add_indicators(df)
    
    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='orange')), row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No data found or connection error.")
