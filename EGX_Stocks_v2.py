import streamlit as st
from tradingview_ta import TA_Handler, Interval
import pandas as pd
import requests
import time
from datetime import datetime
import pytz

# --- Configuration ---
CAIRO_TZ = pytz.timezone('Africa/Cairo')
BOT_TOKEN = "8707488971:AAHtuqNQ5nmI5muwFsRMGNssKR_b9kDchaU"
DEFAULT_CHAT_ID = "1978337209"

TV_INTERVALS = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "1d": Interval.INTERVAL_1_DAY
}

# --- TradingView Engine (Fixed Screener Logic) ---
def get_tv_analysis(symbol, interval_str):
    """
    Automatically detects the correct Screener and Exchange 
    to prevent the 'Error' status in the table.
    """
    if ".CA" in symbol:
        exchange = "EGX"
        screener = "egypt"
        tv_symbol = symbol.replace(".CA", "")
    elif symbol in ["GC=F", "GOLD"]:
        exchange = "COMEX"
        screener = "cfd"
        tv_symbol = "GC1!" # Gold Futures
    else:
        # Default for US Stocks (AMD, NVDA, etc.)
        exchange = "NASDAQ"
        screener = "america"
        tv_symbol = symbol

    try:
        handler = TA_Handler(
            symbol=tv_symbol,
            exchange=exchange,
            screener=screener,
            interval=TV_INTERVALS.get(interval_str, Interval.INTERVAL_15_MINUTES),
            timeout=15
        )
        return handler.get_analysis()
    except:
        return None

# --- UI Setup ---
st.set_page_config(page_title="Sniper Engine Pro", layout="wide")
st.title(f"🎯 Sniper Engine | {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')}")

# SIDEBAR
st.sidebar.header("📡 Alerts & Connection")
active_id = st.sidebar.text_input("Telegram Chat ID", value=DEFAULT_CHAT_ID)

st.sidebar.header("🎯 Strategy Settings")
selected_strat = st.sidebar.selectbox("Signal Logic", [
    "VWAP + RSI > 50 (Whale Logic)", 
    "TV Summary (Strong Buy)", 
    "RSI Threshold"
])

if selected_strat == "VWAP + RSI > 50 (Whale Logic)":
    st.sidebar.success("✅ Condition: Price > VWAP AND RSI > 50")

st.sidebar.header("📊 Market Settings")
p_tf = st.sidebar.selectbox("Timeframe", list(TV_INTERVALS.keys()), index=2)
tickers_input = st.sidebar.text_area("Tickers", "GC=F, COMI.CA, FWRY.CA, AMD, NVDA")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
p_interval = st.sidebar.select_slider("Refresh (Sec)", options=[30, 60, 120], value=60)

if "active" not in st.session_state: st.session_state.active = False
c1, c2 = st.sidebar.columns(2)
if c1.button("🚀 Start"): st.session_state.active = True
if c2.button("🛑 Stop"): st.session_state.active = False

# --- Main Engine ---
if st.session_state.active:
    st.info(f"🛰️ Active Strategy: {selected_strat}")
    table_placeholder = st.empty()

    while True:
        results = []
        for ticker in SCAN_LIST:
            analysis = get_tv_analysis(ticker, p_tf)
            
            if not analysis:
                results.append({"Ticker": ticker, "Status": "⚠️ Error", "Price": 0, "Signal": "N/A", "RSI": "N/A"})
                continue

            price = analysis.indicators["close"]
            rsi = analysis.indicators["RSI"]
            vwap = analysis.indicators.get("VWAP", 0)
            summary = analysis.summary["RECOMMENDATION"]
            
            # --- Strategy Logic ---
            match = False
            if selected_strat == "VWAP + RSI > 50 (Whale Logic)":
                match = (price > vwap) and (rsi > 50)
            elif selected_strat == "TV Summary (Strong Buy)":
                match = (summary == "STRONG_BUY")
            elif selected_strat == "RSI Threshold":
                match = (rsi >= 70)

            results.append({
                "Ticker": ticker,
                "Status": "🎯 MATCH" if match else "❌ " + summary.replace("_", " "),
                "Price": round(price, 4),
                "RSI": round(rsi, 2),
                "Last Update": datetime.now(CAIRO_TZ).strftime("%H:%M:%S")
            })

            if match:
                msg = f"🎯 *SNIPER MATCH: {ticker}*\nPrice: {price}\nSignal: {selected_strat}\nRSI: {round(rsi,2)}"
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": active_id, "text": msg, "parse_mode": "Markdown"})
                except: pass

        if results:
            df_table = pd.DataFrame(results)
            table_placeholder.table(df_table)
        
        time.sleep(p_interval)
        st.rerun()
