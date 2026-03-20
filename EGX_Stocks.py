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
    
    /* FIX: High-contrast Scorecards (White background, Black text) */
    [data-testid="stMetric"] {
        background-color: #f0f2f6 !important; 
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
    
    .status-card { background: #161b22; padding: 20px; border-radius: 10px; border-left: 5px solid #238636; margin-bottom: 20px; }
    .news-card { font-size: 0.9rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Core Functions ---
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(ttl=600)
def get_analysis(ticker, target_profit, capital):
    try:
        # Fetching 6 months for indicator stability
        df = clean_df(yf.download(ticker, period="6mo", interval="1d", progress=False))
        if df.empty or len(df) < 20: return None

        # Technicals using pandas_ta
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)

        current_price = float(df['Close'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])

        # Goal Logic
        required_pct = target_profit / capital if capital > 0 else 0
        tp_price = current_price * (1 + required_pct)
        sl_price = current_price - (atr * 2)

        # Buy Range
        buy_low = current_price - (atr * 0.5)
        buy_high = current_price + (atr * 0.1)

        return {
            "df": df,
            "price": current_price,
            "rsi": df['RSI'].iloc[-1],
            "tp": tp_price,
            "sl": sl_price,
            "buy_range": (buy_low, buy_high),
            "change": ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        }
    except:
        return None

# --- 3. Sidebar & User Goals ---
st.sidebar.header("🎯 Investment Goals")
capital = st.sidebar.number_input("Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Target Gain (EGP)", value=10000)

TICKERS = ["COMI.CA", "FWRY.CA", "TMGH.CA", "ESRS.CA", "ABUK.CA", "SWDY.CA", "ETEL.CA", "AMOC.CA"]

# --- 4. Main UI ---
st.title("EGX Alpha Terminal 🛡️")

# --- NEW: MARKET INDICES SCORECARDS ---
st.subheader("Market Indices")
indices = {
    "EGX 30": "^EGX30",
    "EGX 70": "^EGX70EWI",
    "EGX 100": "^EGX100EWI",
    "EGX 33 (Shariah)": "SHARIAH.CA"
}

idx_cols = st.columns(4)
for i, (name, sym) in enumerate(indices.items()):
    try:
        idx_df = clean_df(yf.download(sym, period="2d", progress=False))
        if not idx_df.empty:
            curr = idx_df['Close'].iloc[-1]
            prev = idx_df['Close'].iloc[-2]
            chg = ((curr - prev) / prev) * 100
            idx_cols[i].metric(label=name, value=f"{curr:,.0f}", delta=f"{chg:+.2f}%")
    except:
        idx_cols[i].error(f"Error {name}")

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "⚖️ Portfolio Balancer"])

with tab1:
    st.subheader("Market Opportunities (Goal-Based)")
    market_list = []
    for t in TICKERS:
        s = get_analysis(t, target_gain, capital)
        if s:
            market_list.append({
                "Ticker": t, "Price": round(s['price'], 2), "RSI": round(s['rsi'], 1),
                "Buy Range": f"{s['buy_range'][0]:.2f}-{s['buy_range'][1]:.2f}",
                "Target TP": round(s['tp'], 2), "Safety SL": round(s['sl'], 2)
            })
    st.table(pd.DataFrame(market_list))

with tab2:
    selected = st.selectbox("Analyze Ticker", TICKERS)
    analysis = get_analysis(selected, target_gain, capital)

    if analysis:
        c1, c2 = st.columns([2, 1])
        with c1:
            df_plot = analysis['df'].tail(60)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name="EMA20", line=dict(color="#00ff88")), row=1, col=1)
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume", marker_color="#30363d"), row=2, col=1)
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown(f"""
            <div class="status-card">
                <h3>Trade Strategy</h3>
                <p><b>Required Move:</b> {(target_gain / capital) * 100:.1f}%</p>
                <hr>
                <p style='color:#00ff88'><b>Entry:</b> {analysis['buy_range'][0]:.2f}</p>
                <p style='color:#58a6ff'><b>Take Profit:</b> {analysis['tp']:.2f}</p>
                <p style='color:#f85149'><b>Stop Loss:</b> {analysis['sl']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("News Insights")
            ticker_obj = yf.Ticker(selected)
            news = ticker_obj.news[:3]
            for n in news:
                st.markdown(f"<div class='news-card'><b>{n['title']}</b><br><small>{datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}</small></div>", unsafe_allow_html=True)

with tab3:
    st.subheader("Smart Allocation")
    pf_data = []
    for t in TICKERS:
        s = get_analysis(t, target_gain, capital)
        if s:
            risk = (float(s['df']['ATR'].iloc[-1]) / s['price'])
            pf_data.append({"Ticker": t, "Risk": risk})

    if pf_data:
        df_pf = pd.DataFrame(pf_data)
        df_pf['Weight'] = (1 / df_pf['Risk'])
        df_pf['Allocation %'] = (df_pf['Weight'] / df_pf['Weight'].sum()) * 100
        st.dataframe(df_pf[['Ticker', 'Allocation %']].sort_values('Allocation %', ascending=False), use_container_width=True)

st.caption(f"v11.0 Pro | {datetime.now().strftime('%H:%M:%S')} UTC")
