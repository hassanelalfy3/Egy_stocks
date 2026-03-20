import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# --- 1. Page Configuration & Professional CSS ---
st.set_page_config(page_title="EGX Alpha Pro 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 2px solid #238636;
        padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] p { color: #1a1a1a !important; font-size: 1.1rem !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; }
    
    .status-card { 
        background: #f8f9fa; color: #1a1a1a; padding: 20px; 
        border-radius: 10px; border-left: 8px solid #238636; 
        margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .status-card h2 { color: #0e1117 !important; margin-top:0; }
    .news-card { font-size: 0.85rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
    .sentiment-tag { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Core Functions ---
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def get_sentiment(news_list):
    if not news_list: return "Neutral ⚪", "#6c757d"
    score = 0
    bullish_words = ['growth', 'profit', 'increase', 'up', 'buy', 'positive', 'gain', 'dividend', 'expand']
    bearish_words = ['drop', 'loss', 'decrease', 'down', 'sell', 'negative', 'risk', 'inflation', 'debt']
    for n in news_list:
        title = n['title'].lower()
        score += sum(1 for word in bullish_words if word in title)
        score -= sum(1 for word in bearish_words if word in title)
    if score > 0: return "Bullish 🟢", "#238636"
    if score < 0: return "Bearish 🔴", "#d73a49"
    return "Neutral ⚪", "#6c757d"

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
        curr, atr, rsi_val = float(df['Close'].iloc[-1]), float(df['ATR'].iloc[-1]), float(df['RSI'].iloc[-1])
        tp = curr * (1 + (target_profit / capital))
        sl = curr - (atr * 2)
        est_days = (tp - curr) / (atr * 0.7) if atr > 0 else 0
        rr = (tp - curr) / (curr - sl) if (curr - sl) > 0 else 0
        return {
            "df": df, "price": curr, "rsi": rsi_val, "tp": tp, "sl": sl, 
            "est_days": int(est_days), "rr_ratio": round(rr, 1),
            "buy_range": (curr - (atr * 0.5), curr + (atr * 0.1)),
            "grade": calculate_risk_grade(rsi_val, atr, curr)
        }
    except: return None

# --- 3. Sidebar & Ticker Lists ---
st.sidebar.title("🎯 Goal Settings")
capital = st.sidebar.number_input("Total Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Target Profit (EGP)", value=10000)

egx30_list = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA", "ORAS.CA", "HRHO.CA"]
egx100_list = ["FWRY.CA", "AMOC.CA", "EKHO.CA", "JUFO.CA", "MNHD.CA", "HELI.CA", "PHDC.CA", "ISPH.CA"]

# --- 4. Main UI Header ---
st.title("EGX Alpha Terminal 🛡️")
indices = {"EGX 30": "^EGX30", "EGX 70": "^EGX70EWI", "EGX 100": "^EGX100EWI", "EGX 33": "SHARIAH.CA"}
idx_cols = st.columns(4)
for i, (name, sym) in enumerate(indices.items()):
    try:
        idx_df = clean_df(yf.download(sym, period="5d", progress=False))
        curr, prev = idx_df['Close'].iloc[-1], idx_df['Close'].iloc[-2]
        idx_cols[i].metric(label=name, value=f"{curr:,.0f}", delta=f"{((curr-prev)/prev)*100:+.2f}%")
    except: pass

st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "⚖️ Portfolio", "🗓️ Macro"])

# --- TAB 1: MARKET PULSE (EGX 30 & 100) ---
with tab1:
    st.subheader("🔵 EGX 30 Blue Chips")
    m30 = []
    for t in egx30_list:
        s = get_analysis(t, target_gain, capital)
        if s: m30.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m30), use_container_width=True, hide_index=True)

    st.subheader("🟠 EGX 100 Growth & Mid-Caps")
    m100 = []
    for t in egx100_list:
        s = get_analysis(t, target_gain, capital)
        if s: m100.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m100), use_container_width=True, hide_index=True)

# --- TAB 2: DEEP INSIGHT ---
with tab2:
    selected = st.selectbox("Analyze Asset", egx30_list + egx100_list)
    analysis = get_analysis(selected, target_gain, capital)
    ticker_obj = yf.Ticker(selected)
    news = ticker_obj.news[:5]
    sent_text, sent_color = get_sentiment(news)

    if analysis:
        c1, c2 = st.columns([2, 1])
        with c1:
            df_p = analysis['df'].tail(60)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price"), row=1, col=1)
            fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            for n in news[:2]:
                st.markdown(f"<div class='news-card'><b>{n['title']}</b><br><small>{datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}</small></div>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="status-card">
                <h2 style="margin-bottom:0;">{selected.replace(".CA","")}</h2>
                <span class="sentiment-tag" style="background:{sent_color}; color:white;">Sentiment: {sent_text}</span>
                <p style="font-size: 1.5rem; font-weight: bold; margin-top:10px;">{analysis['price']:.2f} EGP</p>
                <div style="background:#e9ecef; padding:12px; border-radius:8px; margin:10px 0;">
                    <p><b>Risk Grade:</b> {analysis['grade']}</p>
                    <p><b>R/R Ratio:</b> 1 : {analysis['rr_ratio']}</p>
                    <p><b>Est. Time:</b> ~{analysis['est_days']} Days</p>
                </div>
                <p style='color:#1e7e34; font-weight: bold;'>🟢 Entry: {analysis['buy_range'][0]:.2f}-{analysis['buy_range'][1]:.2f}</p>
                <p style='color:#0056b3; font-weight: bold;'>🔵 Target: {analysis['tp']:.2f}</p>
                <p style='color:#d73a49; font-weight: bold;'>🔴 Stop: {analysis['sl']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
            report = pd.DataFrame([{"Ticker": selected, "Price": analysis['price'], "Target": round(analysis['tp'],2)}])
            st.download_button("📥 Trade Sheet", report.to_csv(index=False).encode('utf-8'), f"{selected}.csv", "text/csv", use_container_width=True)

# --- TAB 3: PORTFOLIO & HEATMAP ---
with tab3:
    st.subheader("🔥 Sector Heatmap")
    hcols = st.columns(5)
    sects = [("Real Estate", 4.8, "🌊"), ("Banking", 1.2, "⚖️"), ("Fintech", 3.5, "🚀"), ("Resources", -2.1, "📉"), ("Industrials", 2.9, "🏗️")]
    for i, (n, p, e) in enumerate(sects):
        c = "#238636" if p > 0 else "#d73a49"
        hcols[i].markdown(f"<div style='background:{c}; padding:10px; border-radius:8px; text-align:center; color:white;'><b>{n}</b><br>{p:+.1f}% {e}</div>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("💼 Live Portfolio Tracker")
    p_ticker = st.selectbox("Select Owned Ticker", egx30_list + egx100_list)
    p_cols = st.columns(3)
    buy_p = p_cols[0].number_input("Avg Buy Price", value=0.0)
    qty = p_cols[1].number_input("Quantity", value=0)
    p_data = get_analysis(p_ticker, target_gain, capital)
    if p_data and buy_p > 0:
        gain = (p_data['price'] - buy_p) * qty
        p_cols[2].metric("Live P/L", f"{gain:,.2f} EGP", f"{(gain/(buy_p*qty))*100:+.2f}%" if (buy_p*qty)>0 else "0%")

# --- TAB 4: MACRO & CALENDAR ---
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🗓️ CBE MPC Meetings")
        st.table(pd.DataFrame([{"Meeting": "MPC 2", "Date": "2026-04-02"}, {"Meeting": "MPC 3", "Date": "2026-05-21"}]))
    with c2:
        st.subheader("🚀 Rate Cut Simulator")
        sim = st.slider("Simulated Cut (bps)", 0, 200, 100)
        st.info(f"A {sim}bps cut targets a ~{ (sim/100)*4 :.1f}% market valuation boost.")

st.caption(f"EGX Alpha Pro v16.0 | Sync: {datetime.now().strftime('%H:%M:%S')}")
