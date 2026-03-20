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
    .status-card h3 { color: #0e1117 !important; margin: 0; }
    .news-card { font-size: 0.85rem; padding: 10px; border-bottom: 1px solid #30363d; color: #e6edf3; }
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
        return {
            "df": df, "price": curr, "rsi": rsi_val, "atr": atr, "tp": tp, "sl": sl, 
            "rr_ratio": round((tp-curr)/(curr-sl), 1) if (curr-sl) != 0 else 0,
            "buy_range": (curr - (atr * 0.5), curr + (atr * 0.1))
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
            target, stop = entry_p * (1 + tp_pct) , entry_p - (sl_mult * curr_atr)
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
st.sidebar.title("🤖 Terminal Control")
capital = st.sidebar.number_input("Global Capital (EGP)", value=100000)
target_gain = st.sidebar.number_input("Profit Target (EGP)", value=10000)
sl_slider = st.sidebar.slider("ATR SL Multiplier", 1.5, 4.0, 2.0)

egx_list = ["COMI.CA", "TMGH.CA", "SWDY.CA", "ETEL.CA", "ABUK.CA", "ORAS.CA", "FWRY.CA", "PHDC.CA"]

st.sidebar.divider()
bot_on = st.sidebar.toggle("Activate Signal Bot")
bot_tick = st.sidebar.selectbox("Bot Monitoring", egx_list)
if bot_on:
    b = get_analysis(bot_tick, target_gain, capital, sl_slider)
    if b and b['buy_range'][0] <= b['price'] <= b['buy_range'][1] and b['rsi'] < 60:
        st.sidebar.success(f"🔥 SIGNAL: Buy {bot_tick} @ {b['price']:.2f}")
        st.toast(f"Buy Alert: {bot_tick}!", icon="💰")
    else: st.sidebar.warning("⏳ Tracking Markets...")

# --- 4. Main App Tabs ---
st.title("EGX Alpha Terminal 🛡️")
t1, t2, t3, t4, t5 = st.tabs(["📊 Market Pulse", "🔍 Deep Insight", "🧪 Backtest", "⚖️ Portfolio Tracker", "🗓️ Macro Calendar"])

# TAB 1: PULSE
with t1:
    st.subheader("Live Market Scanner")
    m_data = []
    for t in egx_list:
        s = get_analysis(t, target_gain, capital, sl_slider)
        if s: m_data.append({"Ticker": t.replace(".CA",""), "Price": round(s['price'],2), "RSI": round(s['rsi'],1), "TP": round(s['tp'],2), "SL": round(s['sl'],2)})
    st.dataframe(pd.DataFrame(m_data), use_container_width=True, hide_index=True)

# TAB 2: INSIGHT
with t2:
    sel = st.selectbox("Detailed Analysis", egx_list)
    an = get_analysis(sel, target_gain, capital, sl_slider)
    if an:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure(data=[go.Candlestick(x=an['df'].index[-60:], open=an['df']['Open'][-60:], high=an['df']['High'][-60:], low=an['df']['Low'][-60:], close=an['df']['Close'][-60:])])
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown(f"""<div class='status-card'><h3>{sel.replace(".CA","")}</h3><b>Price: {an['price']:.2f} EGP</b><hr>🟢 Entry: {an['buy_range'][0]:.2f}<br>🔵 Target: {an['tp']:.2f}<br>🔴 Stop: {an['sl']:.2f}</div>""", unsafe_allow_html=True)

# TAB 3: BACKTEST
with t3:
    st.subheader("🧪 Strategy Backtest Simulator")
    bc1, bc2, bc3 = st.columns(3)
    bt_tk = bc1.selectbox("Simulate Ticker", egx_list, key="bt_main")
    bt_inv = bc2.number_input("Investment (EGP)", value=20000)
    bt_rsi = bc3.slider("Buy RSI Threshold", 20, 50, 30)

    if st.button("🚀 Run Simulation"):
        logs, f_bal = run_backtest(bt_tk, bt_inv, (target_gain/capital), bt_rsi, sl_slider)
        if not logs.empty:
            st.metric("Final Balance", f"{f_bal:,.2f} EGP", f"{((f_bal-bt_inv)/bt_inv)*100:+.2f}%")
            st.dataframe(logs, use_container_width=True, hide_index=True)
            sell_data = logs[logs['Action']=="SELL"]
            if not sell_data.empty:
                fig_bt = go.Figure(data=[go.Scatter(x=sell_data['Date'], y=sell_data['Balance'], mode='lines+markers', line=dict(color='#238636'))])
                fig_bt.update_layout(title="Backtest Equity Curve", template="plotly_dark", height=300)
                st.plotly_chart(fig_bt, use_container_width=True)
        else: st.error("No trades triggered. Try a higher RSI threshold.")

# TAB 4: PORTFOLIO TRACKER (RESTORED)
with t4:
    st.subheader("💼 Active Holdings Tracker")
    p_ticker = st.selectbox("Ticker Owned", egx_list, key="port_select")
    p_cols = st.columns(3)
    buy_p = p_cols[0].number_input("Average Buy Price", value=0.0, step=0.1)
    qty = p_cols[1].number_input("Quantity Owned", value=0, step=1)
    
    p_analysis = get_analysis(p_ticker, target_gain, capital, sl_slider)
    if p_analysis and buy_p > 0 and qty > 0:
        current_val = p_analysis['price'] * qty
        initial_inv = buy_p * qty
        live_pnl = current_val - initial_inv
        p_cols[2].metric("Live P&L", f"{live_pnl:,.2f} EGP", f"{(live_pnl/initial_inv)*100:+.2f}%")
        
        # Portfolio Risk Check
        if p_analysis['price'] <= p_analysis['sl']:
            st.error(f"⚠️ EXIT ALERT: {p_ticker} has dropped below your calculated Stop Loss ({p_analysis['sl']:.2f})!")
        elif p_analysis['price'] >= p_analysis['tp']:
            st.success(f"💰 TARGET HIT: {p_ticker} has reached your Take Profit goal ({p_analysis['tp']:.2f})!")
        else:
            st.info(f"Hold {p_ticker}. Current Price is within the safe range.")

# TAB 5: MACRO
with t5:
    st.subheader("CBE Interest Rate Calendar")
    st.info("The CBE currently maintains a 19% deposit rate. Next update scheduled April 2026.")
    st.table(pd.DataFrame([{"Event": "MPC Meeting", "Date": "2026-04-02"}, {"Event": "MPC Meeting", "Date": "2026-05-21"}]))

st.caption(f"EGX Alpha v19.0 | Sync: {datetime.now().strftime('%H:%M:%S')}")
