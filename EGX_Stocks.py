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
    bullish_words = ['growth', 'profit', 'increase', 'up', 'buy', 'positive', 'gain', 'dividend', 'expand', 'bullish']
    bearish_words = ['drop', 'loss', 'decrease', 'down', 'sell', 'negative', 'risk', 'inflation', 'debt', 'bearish']
    
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
        
        curr = float(df['Close'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])
        rsi_val = float(df['RSI'].iloc[-1])
        
        tp = curr * (1 + (target_profit / capital))
        sl = curr - (atr * 2)
        est_days = (tp - curr) / (atr * 0.7) if atr > 0 else 0
        rr = (tp - curr) / (curr - sl) if (curr - sl) > 0 else 0
        
        return {
            "df": df, "price": curr, "rsi": rsi_val, "atr": atr, "tp": tp, "sl": sl, 
            "est_days": int(est_days), "rr_ratio": round(rr, 1),
            "buy_range": (curr - (atr * 0.5), curr + (atr * 0.1)),
            "grade": calculate_risk_grade(rsi_val, atr, curr)
        }
    except: return None

# --- 3. Sidebar Configuration ---
st.sidebar.title("Configuration")
capital = st.sidebar.number_input("Portfolio Capital (EGP)", value=100000, step=5000)
target_gain = st.sidebar.number_input("Desired Profit (EGP)", value=10000, step=1000)

# --- 4. Market Tickers ---
egx30_list = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA", "ORAS.CA", "HRHO.CA"]
egx100_list = ["FWRY.CA", "AMOC.CA", "EKHO.CA", "JUFO.CA", "MNHD.CA", "HELI.CA", "PHDC.CA"]

# --- 5. App Layout ---
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "⚖️ Portfolio Balancer", "🗓️ Macro Calendar"])

# --- Tab 1: Market Pulse ---
with tab1:
    st.subheader("🔵 Blue Chip Opportunities")
    m30 = []
    for t in egx30_list:
        s = get_analysis(t, target_gain, capital)
        if s: m30.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "Grade": s['grade'], "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m30), use_container_width=True, hide_index=True)

# --- Tab 2: Deep Insight ---
with tab2:
    selected = st.selectbox("Select Asset for Analysis", egx30_list + egx100_list)
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
            
            st.subheader("Latest Headlines")
            for n in news[:3]:
                st.markdown(f"<div class='news-card'><b>{n['title']}</b><br><small>{n['publisher']} | {datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}</small></div>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="status-card">
                <h2 style="margin-bottom:0;">{selected.replace(".CA","")}</h2>
                <span class="sentiment-tag" style="background:{sent_color}; color:white;">Sentiment: {sent_text}</span>
                <p style="font-size: 1.5rem; font-weight: bold; margin-top:10px;">{analysis['price']:.2f} EGP</p>
                <div style="background:#e9ecef; padding:12px; border-radius:8px; margin:10px 0;">
                    <p><b>Risk Grade:</b> {analysis['grade']}</p>
                    <p><b>R/R Ratio:</b> 1 : {analysis['rr_ratio']}</p>
                    <p><b>Est. Time:</b> ~{analysis['est_days']} Trading Days</p>
                </div>
                <p style='color:#1e7e34; font-weight: bold;'>🟢 Buy Zone: {analysis['buy_range'][0]:.2f}-{analysis['buy_range'][1]:.2f}</p>
                <p style='color:#0056b3; font-weight: bold;'>🔵 Target Price: {analysis['tp']:.2f}</p>
                <p style='color:#d73a49; font-weight: bold;'>🔴 Stop Loss: {analysis['sl']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            report = pd.DataFrame([{"Ticker": selected, "Price": analysis['price'], "Sentiment": sent_text, "Grade": analysis['grade'], "Target": round(analysis['tp'],2), "Stop": round(analysis['sl'],2)}])
            st.download_button("📥 Download Trade Sheet", report.to_csv(index=False).encode('utf-8'), f"{selected}_Report.csv", "text/csv", use_container_width=True)

# --- Tab 3: Portfolio Balancer & Heatmap ---
with tab3:
    st.subheader("🔥 Sector Heatmap & Smart Money Flows")
    sectors = {
        "Real Estate": {"Perf": 4.8, "Flow": "Strong Inflow 🌊", "Note": "TMGH, PHDC leading"},
        "Banking": {"Perf": 1.2, "Flow": "Stable ⚖️", "Note": "CIB yields healthy"},
        "Fintech": {"Perf": 3.5, "Flow": "Momentum Buy 🚀", "Note": "Fawry high volume"},
        "Resources": {"Perf": -2.1, "Flow": "Outflow 📉", "Note": "AMOC cooling"},
        "Industrials": {"Perf": 2.9, "Flow": "Value Play 🏗️", "Note": "SWDY growing"}
    }
    cols = st.columns(len(sectors))
    for i, (name, d) in enumerate(sectors.items()):
        color = "#238636" if d['Perf'] > 0 else "#d73a49"
        cols[i].markdown(f"<div style='background:{color}; padding:10px; border-radius:8px; text-align:center; color:white;'><b>{name}</b><br>{d['Perf']:+.1f}%<br><small>{d['Flow']}</small></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("⚖️ Optimized Allocation")
    # Risk-based weighting logic
    pf_data = []
    for t in egx30_list[:5]:
        s = get_analysis(t, target_gain, capital)
        if s: pf_data.append({"Ticker": t.replace(".CA",""), "Risk": (s['atr']/s['price'])})
    if pf_data:
        df_pf = pd.DataFrame(pf_data)
        df_pf['Allocation %'] = ( (1/df_pf['Risk']) / (1/df_pf['Risk']).sum() ) * 100
        df_pf['EGP Buy Amount'] = (df_pf['Allocation %']/100) * capital
        st.dataframe(df_pf[['Ticker', 'Allocation %', 'EGP Buy Amount']].sort_values('Allocation %', ascending=False), hide_index=True)

# --- Tab 4: Macro Calendar & Simulator ---
with tab4:
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("🗓️ CBE MPC Calendar 2026")
        mpc = pd.DataFrame([
            {"Meeting": "MPC Meeting 2", "Date": "2026-04-02", "Prob. Cut": "70%"},
            {"Meeting": "MPC Meeting 3", "Date": "2026-05-21", "Prob. Cut": "50%"},
            {"Meeting": "MPC Meeting 4", "Date": "2026-07-09", "Prob. Cut": "Scheduled"}
        ])
        st.table(mpc)
    
    with col_r:
        st.subheader("🚀 Rate Cut Simulator")
        sim_cut = st.select_slider("Simulated cut in April (bps)", options=[0, 50, 100, 150, 200], value=100)
        boost = (sim_cut / 100) * 0.04 
        st.write(f"A **{sim_cut}bps** cut could boost equity valuations by approx **{boost*100:.1f}%**.")
        if st.button("Apply to Targets"):
            st.success(f"New Target for {selected}: {analysis['tp']*(1+boost):.2f} EGP")

st.caption(f"Terminal Version 15.0 | Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data: Yahoo Finance")
