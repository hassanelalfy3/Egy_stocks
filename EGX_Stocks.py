import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(page_title="EGX Alpha Pro 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetric"] { background-color: #ffffff !important; border: 2px solid #238636; padding: 15px; border-radius: 12px; }
    [data-testid="stMetricLabel"] p { color: #1a1a1a !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; }
    .status-card { background: #f8f9fa; color: #1a1a1a; padding: 20px; border-radius: 10px; border-left: 8px solid #238636; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .news-card { font-size: 0.85rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
    .sentiment-tag { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Core Logic Functions ---
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(ttl=300)
def get_analysis(ticker, target_profit, capital, sl_mult=2.0):
    try:
        df = clean_df(yf.download(ticker, period="6mo", interval="1d", progress=False))
        if df.empty or len(df) < 20: return None
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        curr, atr, rsi_val = float(df['Close'].iloc[-1]), float(df['ATR'].iloc[-1]), float(df['RSI'].iloc[-1])
        tp = curr * (1 + (target_profit / capital))
        sl = curr - (atr * sl_mult)
        days = (tp - curr) / (atr * 0.7) if atr > 0 else 0
        return {
            "df": df, "price": curr, "rsi": rsi_val, "atr": atr, "tp": tp, "sl": sl, 
            "est_days": int(days), "rr_ratio": round((tp-curr)/(curr-sl), 1),
            "buy_range": (curr - (atr * 0.5), curr + (atr * 0.1)),
            "change": ((curr - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        }
    except: return None

def run_backtest(ticker, start_inv, tp_pct, rsi_lvl, sl_mult):
    df = clean_df(yf.download(ticker, period="1y", interval="1d", progress=False))
    if df.empty: return pd.DataFrame(), start_inv
    df['RSI'] = ta.rsi(df['Close'], length=14); df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df = df.dropna()
    balance, position, entry_p, logs = start_inv, 0, 0, []

    for i in range(len(df)):
        curr_p, curr_rsi, curr_atr, date = df['Close'].iloc[i], df['RSI'].iloc[i], df['ATR'].iloc[i], df.index[i]
        if position > 0:
            target, stop = entry_p * (1 + tp_pct), entry_p - (sl_mult * curr_atr)
            if curr_p >= target or curr_p <= stop:
                balance = position * curr_p
                res = "PROFIT ✅" if curr_p >= target else "LOSS ❌"
                logs.append({"Date": date.strftime('%Y-%m-%d'), "Action": "SELL", "Price": round(curr_p, 2), "Result": res, "Balance": round(balance, 2)})
                position = 0
        elif curr_rsi <= rsi_lvl and balance > 0:
            entry_p = curr_p; position = balance / entry_p
            logs.append({"Date": date.strftime('%Y-%m-%d'), "Action": "BUY", "Price": round(curr_p, 2), "Result": "-", "Balance": round(balance, 2)})
    final = balance if position == 0 else position * df['Close'].iloc[-1]
    return pd.DataFrame(logs), final

# --- 3. Sidebar & Signal Bot ---
st.sidebar.title("🎯 Settings & Bot")
capital = st.sidebar.number_input("Global Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Profit Target (EGP)", value=10000)
sl_slider = st.sidebar.slider("Stop Loss (ATR Multiplier)", 1.5, 4.0, 2.0, 0.5)

egx30 = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA", "ORAS.CA"]
egx100 = ["FWRY.CA", "AMOC.CA", "EKHO.CA", "JUFO.CA", "PHDC.CA", "HELI.CA"]

st.sidebar.divider()
bot_on = st.sidebar.toggle("🤖 Activate Signal Bot")
bot_tick = st.sidebar.selectbox("Bot Target", egx30 + egx100)
if bot_on:
    b_data = get_analysis(bot_tick, target_gain, capital, sl_slider)
    if b_data:
        if b_data['buy_range'][0] <= b_data['price'] <= b_data['buy_range'][1] and b_data['rsi'] < 60:
            st.sidebar.success(f"🚀 BUY SIGNAL: {bot_tick}")
            st.toast(f"Bot Signal: Buy {bot_tick}!", icon="💰")
        else: st.sidebar.warning("⏳ Monitoring Price Action...")

# --- 4. Main Interface ---
st.title("EGX Alpha Pro 🛡️")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Pulse", "🔍 Insight", "🧪 Backtest", "⚖️ Portfolio", "🗓️ Macro"])

# Tab 1: Pulse
with tab1:
    st.subheader("Market Heat")
    m_data = []
    for t in egx30 + egx100:
        s = get_analysis(t, target_gain, capital, sl_slider)
        if s: m_data.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m_data), use_container_width=True, hide_index=True)

# Tab 2: Insight (Detailed View)
with tab2:
    sel = st.selectbox("Detailed Analysis", egx30 + egx100)
    an = get_analysis(sel, target_gain, capital, sl_slider)
    if an:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure(data=[go.Candlestick(x=an['df'].index[-60:], open=an['df']['Open'][-60:], high=an['df']['High'][-60:], low=an['df']['Low'][-60:], close=an['df']['Close'][-60:])])
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown(f"""<div class='status-card'><h3>{sel.replace(".CA","")}</h3><b>Price: {an['price']:.2f} EGP</b><br>RSI: {an['rsi']:.1f} | R/R: {an['rr_ratio']}<hr>🟢 Entry: {an['buy_range'][0]:.2f}<br>🔵 Target: {an['tp']:.2f}<br>🔴 Stop: {an['sl']:.2f}</div>""", unsafe_allow_html=True)

# Tab 3: Backtest (The Simulator)
with tab3:
    st.subheader("🧪 Historical Strategy Simulator")
    bc1, bc2, bc3 = st.columns(3)
    bt_tk = bc1.selectbox("Stock", egx30 + egx100, key="bt_tk")
    bt_inv = bc2.number_input("Investment (EGP)", value=20000)
    bt_rsi = bc3.slider("Buy RSI Threshold", 20, 50, 30)
    
    if st.button("Run 1-Year Backtest"):
        logs, f_bal = run_backtest(bt_tk, bt_inv, (target_gain/capital), bt_rsi, sl_slider)
        if not logs.empty:
            st.metric("Final Balance", f"{f_bal:,.2f} EGP", f"{((f_bal-bt_inv)/bt_inv)*100:+.2f}%")
            st.dataframe(logs, use_container_width=True)
            fig_bt = go.Figure(data=[go.Scatter(x=logs[logs['Action']=="SELL"]['Date'], y=logs[logs['Action']=="SELL"]['Balance'], mode='lines+markers', line=dict(color='#238636'))])
            fig_bt.update_layout(title="Equity Growth", template="plotly_dark", height=300)
            st.plotly_chart(fig_bt, use_container_width=True)
        else: st.error("No trades triggered. Try increasing the RSI Threshold.")

# Tab 4: Portfolio
with tab3:
    st.write("Current allocation logic based on global capital settings.")

# Tab 5: Macro
with tab5:
    st.subheader("Monetary Policy Tracker")
    st.info("Next CBE Meeting: April 2, 2026. Expected Bias: Dovish (Rate Cut).")

st.caption(f"Terminal v17.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
