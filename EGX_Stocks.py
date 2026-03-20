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
    
    /* Brighter Trade Strategy Card */
    .status-card { 
        background: #f8f9fa; 
        color: #1a1a1a;
        padding: 20px; 
        border-radius: 10px; 
        border-left: 8px solid #238636; 
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .status-card h2, .status-card h3 { color: #0e1117 !important; margin-top:0; }
    
    .news-card { font-size: 0.9rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Core Functions ---
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_risk_grade(rsi, atr, price):
    vol = (atr / price) * 100
    score = 100
    if rsi > 70 or rsi < 30: score -= 20
    if vol > 4: score -= 20
    elif vol > 2: score -= 10
    
    if score >= 90: return "A (Safe)"
    elif score >= 80: return "B (Moderate)"
    elif score >= 70: return "C (Speculative)"
    else: return "F (High Risk)"

@st.cache_data(ttl=300)
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
            "tp": tp_price, "sl": sl_price, "profit_egp": target_profit,
            "buy_range": (current_price - (atr * 0.5), current_price + (atr * 0.1)),
            "grade": calculate_risk_grade(rsi_val, atr, current_price),
            "change": ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        }
    except: return None

# --- 3. Sidebar ---
st.sidebar.header("🎯 Investment Goals")
capital = st.sidebar.number_input("Starting Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Target Profit (EGP)", value=10000)

# --- 4. Main UI ---
st.title("EGX Alpha Terminal 🛡️")

# --- Market Indices Scorecards ---
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
tab1, tab2, tab3 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "⚖️ Portfolio Balancer"])

with tab1:
    # --- EGX 30 ---
    st.subheader("🔵 EGX 30 Blue Chips")
    egx30_list = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA", "ORAS.CA"]
    m30 = []
    for t in egx30_list:
        s = get_analysis(t, target_gain, capital)
        if s:
            m30.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m30), use_container_width=True, hide_index=True)

    # --- EGX 100 ---
    st.subheader("🟠 EGX 100 Growth")
    egx100_list = ["FWRY.CA", "AMOC.CA", "EKHO.CA", "JUFO.CA", "MNHD.CA", "HELI.CA"]
    m100 = []
    for t in egx100_list:
        s = get_analysis(t, target_gain, capital)
        if s:
            m100.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m100), use_container_width=True, hide_index=True)

with tab2:
    selected = st.selectbox("Analyze Ticker", egx30_list + egx100_list)
    analysis = get_analysis(selected, target_gain, capital)
    if analysis:
        c1, c2 = st.columns([2, 1])
        with c1:
            df_p = analysis['df'].tail(60)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA20'], name="EMA20", line=dict(color="#00ff88")), row=1, col=1)
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown(f"""
            <div class="status-card">
                <h2 style="margin-bottom: 5px;">{selected.replace(".CA","")}</h2>
                <p style="font-size: 1.5rem; font-weight: bold; color: #0e1117;">Current: {analysis['price']:.2f} EGP</p>
                
                <div style="background-color: #e9ecef; padding: 12px; border-radius: 8px; margin: 15px 0;">
                    <p><b>Risk Grade:</b> {analysis['grade']}</p>
                    <p><b>Required Move:</b> {(target_gain/capital)*100:.1f}%</p>
                    <p style="color: #238636; font-weight: bold;">Potential Profit: +{analysis['profit_egp']:,} EGP</p>
                </div>
                
                <hr style="border: 0.5px solid #ccc; margin: 15px 0;">
                <p style='color:#1e7e34; font-weight: bold;'>🟢 Entry Range: {analysis['buy_range'][0]:.2f} - {analysis['buy_range'][1]:.2f}</p>
                <p style='color:#0056b3; font-weight: bold;'>🔵 Target Price: {analysis['tp']:.2f}</p>
                <p style='color:#d73a49; font-weight: bold;'>🔴 Stop Loss: {analysis['sl']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("⚖️ Smart Portfolio Balancer")
    
    # Projected Portfolio Value Card
    projected_total = capital + target_gain
    c1, c2 = st.columns(2)
    c1.metric("Current Capital", f"{capital:,.0f} EGP")
    c2.metric("Projected Goal", f"{projected_total:,.0f} EGP", f"+{target_gain:,.0f}")
    
    st.divider()
    st.write("Allocation to keep risk equal across your portfolio (Inverse Volatility):")

    pf_data = []
    for t in (egx30_list + egx100_list):
        s = get_analysis(t, target_gain, capital)
        if s:
            risk = (float(s['atr']) / s['price'])
            pf_data.append({"Ticker": t.replace(".CA",""), "Risk": risk})
    
    if pf_data:
        df_pf = pd.DataFrame(pf_data)
        df_pf['Weight'] = (1 / df_pf['Risk'])
        df_pf['Allocation %'] = (df_pf['Weight'] / df_pf['Weight'].sum()) * 100
        df_pf['EGP Amount'] = (df_pf['Allocation %'] / 100) * capital
        
        st.dataframe(
            df_pf[['Ticker', 'Allocation %', 'EGP Amount']].sort_values('Allocation %', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )

st.caption(f"v14.0 Pro | {datetime.now().strftime('%H:%M:%S')} UTC")
