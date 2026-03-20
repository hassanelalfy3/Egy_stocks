import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(page_title="EGX Pro Advisor", layout="wide")

def add_indicators(df):
    # Fix multi-index columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Use pandas_ta for calculations
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Bollinger Bands (returns 3 columns: lower, mid, upper)
    bbands = ta.bbands(df['Close'], length=20, std=2)
    df['Lower_Band'] = bbands['BBL_20_2.0']
    df['SMA20'] = bbands['BBM_20_2.0']
    df['Upper_Band'] = bbands['BBU_20_2.0']
    
    return df

def get_recommendation(df):
    last = df.iloc[-1]
    price = float(last['Close'])
    rsi = float(last['RSI'])

    rec = {"action": "HOLD ⚪", "tp1": "-", "tp2": "-", "sl": "-", "reason": "السعر في منطقة محايدة حالياً."}

    # Buy Signal
    if rsi <= 35 or price <= last['Lower_Band']:
        rec["action"] = "BUY 🟢"
        rec["sl"] = round(price * 0.95, 2)
        rec["tp1"] = round(last['SMA20'], 2)
        rec["tp2"] = round(last['Upper_Band'], 2)
        rec["reason"] = "تشبع بيعي واضح (RSI منخفض) أو ملامسة دعم البولينجر السفلي."

    # Sell Signal
    elif rsi >= 70 or price >= last['Upper_Band']:
        rec["action"] = "SELL 🔴"
        rec["reason"] = "تشبع شرائي مرتفع أو ملامسة مقاومة البولينجر العلوية."

    return rec

# --- UI Interface ---
st.title("📊 مستشارك الذكي للبورصة المصرية")
st.markdown("---")

egx_list = ["COMI.CA", "FWRY.CA", "TMGH.CA", "EKHO.CA", "ABUK.CA", "SWDY.CA", "ETEL.CA", "AMOC.CA", "ORAS.CA", "PHDC.CA"]
selected_stock = st.sidebar.selectbox("اختر السهم لتحليله:", egx_list)
period = st.sidebar.selectbox("فترة عرض الشارت:", ["3mo", "6mo", "1y"], index=1)

with st.spinner('جاري تحديث بيانات السوق...'):
    df = yf.download(selected_stock, period="1y", interval="1d", progress=False)

if not df.empty and len(df) > 20:
    df = add_indicators(df)
    rec = get_recommendation(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("التوصية الحالية", rec["action"])
    c2.metric("الهدف الأول (TP1)", rec["tp1"])
    c3.metric("الهدف الثاني (TP2)", rec["tp2"])
    c4.metric("وقف الخسارة (SL)", rec["sl"])

    st.info(f"💡 **تحليل الخبير الآلي:** {rec['reason']}")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['Upper_Band'], name="مقاومة بولينجر",
                             line=dict(color='rgba(255,255,255,0.4)', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], name="دعم بولينجر",
                             line=dict(color='rgba(255,255,255,0.4)', dash='dot')), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='orange')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("بيانات غير كافية لتحليل هذا السهم حالياً.")
