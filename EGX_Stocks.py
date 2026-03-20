import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# --- 1. Page Configuration & Professional CSS ---
st.set_page_config(page_title="EGX Alpha Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    
    /* High-contrast Scorecards (Indices) */
    [data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 2px solid #238636;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] p {
        color: #1a1a1a !important; 
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important; 
    }
    
    /* UPDATED: Brighter Trade Strategy Card */
    .status-card { 
        background: #f8f9fa; 
        color: #1a1a1a;
        padding: 20px; 
        border-radius: 10px; 
        border-left: 8px solid #238636; 
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .status-card h3 { color: #0e1117 !important; margin-top:0; }
    .status-card p { font-size: 1.1rem; margin: 5px 0; }
    
    .news-card { font-size: 0.9rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Core Functions ---
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_risk_grade(rsi, atr, price):
    # Volatility ratio
    vol = (atr / price) * 100
    # Logic: High RSI (>70) or Extreme Volatility = Lower Grade
    score = 100
    if rsi > 70 or rsi < 30: score -= 20
    if vol > 4: score -= 20
    elif vol > 2: score -= 10
    
    if score >= 90: return "A (Safe)"
    elif score >= 80: return "B (Moderate)"
    elif score >= 70: return "C (Speculative)"
    else: return "F (High Risk)"

@st.cache_data(ttl=600)
def get_analysis(ticker, target_profit, capital):
    try:
        df = clean_df(yf.download(ticker, period="6mo", interval="1d", progress=False))
        if df.empty or len(df) < 20: return None

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)

        current_price = float(df['Close'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])
        rsi_val = float(df['RSI'].iloc[-1])

        required_pct = target_profit / capital if capital > 0 else 0
        tp_price = current_price * (1 + required_pct)
        sl_price = current_price - (atr * 2)

        return {
            "df": df, "price": current_price, "rsi": rsi_val, "atr": atr,
            "tp": tp_price, "sl": sl_price,
            "buy_range": (current_price - (atr * 0.5), current_price + (atr * 0.1)),
            "grade": calculate_risk_grade(rsi_val, atr, current_price),
            "change": ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        }
    except: return None

# --- 3. Sidebar ---
st.sidebar.header("🎯 Goals")
capital = st.sidebar.number_input("Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Target Gain (EGP)", value=10000)

# --- 4. Main UI ---
st.title("EGX Alpha Terminal 🛡️")

st.subheader("Market Indices")
indices = {"EGX 30": "^EGX30", "EGX 70": "^EGX70EWI", "EGX 100": "^EGX100EWI", "EGX 33": "SHARIAH.CA"}
idx_cols = st.columns(4)
for i, (name, sym) in enumerate(indices.items()):
    try:
        idx_df = clean_df(yf.download(sym, period="5d", progress=False))
        curr, prev = idx_df['Close'].iloc[-1], idx_df['Close'].iloc[-2]
        idx_cols[i].metric(label=name, value=f"{curr:,.0f}", delta=f"{((curr-prev)/prev)*100:+.2f}%")
    except: idx_cols[i].error(f"Error {name}")

st.divider()
tab1, tab2, tab3 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "⚖️ Portfolio"])

with tab1:
    # --- EGX 30 ---
    st.subheader("🔵 EGX 30 Blue Chips")
    egx30 = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA"]
    m30 = []
    for t in egx30:
        s = get_analysis(t, target_gain, capital)
        if s:
            m30.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m30), use_container_width=True, hide_index=True)

    # --- EGX 100 ---
    st.subheader("🟠 EGX 100 Growth")
    egx100 = ["FWRY.CA", "AMOC.CA", "EKHO.CA", "JUFO.CA", "MNHD.CA"]
    m100 = []
    for t in egx100:
        s = get_analysis(t, target_gain, capital)
        if s:
            m100.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m100), use_container_width=True, hide_index=True)

with tab2:
    selected = st.selectbox("Analyze Ticker", egx30 + egx100)
    analysis = get_analysis(selected, target_gain, capital)
    if analysis:
        c1, c2 = st.columns([2, 1])
        with c1:
            df_p = analysis['df'].tail(60)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA20'], name="EMA20", line=dict(color="#00ff88")), row=1, col=1)
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown(f"""
            <div class="status-card">
                <h3>Trade Strategy: {selected.replace(".CA","")}</h3>
                <p><b>Risk Grade:</b> {analysis['grade']}</p>
                <p><b>Required Move:</b> {(target_gain/capital)*100:.1f}%</p>
                <hr style="border: 0.5px solid #ccc">
                <p style='color:#238636'><b>Entry Range:</b> {analysis['buy_range'][0]:.2f} - {analysis['buy_range'][1]:.2f}</p>
                <p style='color:#0056b3'><b>Target Profit:</b> {analysis['tp']:.2f}</p>
                <p style='color:#d73a49'><b>Stop Loss:</b> {analysis['sl']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("Smart Allocation")
    # Portfolio logic remains the same...

st.caption(f"v12.0 Pro | {datetime.now().strftime('%H:%M:%S')} UTC")
