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

# --- Fixed TradingView Engine ---
def get_tv_analysis(symbol, interval_str):
    symbol = symbol.strip().upper()
    
    # 1. ROUTING: Matches the ticker to the right database
    if ".CA" in symbol:
        # Egyptian Market
        exchange = "EGX"
        screener = "egypt"
        tv_symbol = symbol.replace(".CA", "")
    elif symbol in ["GC=F", "GOLD", "XAUUSD"]:
        # Gold
        exchange = "COMEX"
        screener = "cfd"
        tv_symbol = "GC1!" 
    else:
        # US Market Fallback (NVDA, AMD, etc.)
        exchange = "NASDAQ"
        screener = "america"
        tv_symbol = symbol

    try:
        handler = TA_Handler(
            symbol=tv_symbol,
            exchange=exchange,
            screener=screener,
            interval=TV_INTERVALS.get(interval_str, Interval.INTERVAL_15_MINUTES),
            timeout=20
        )
        return handler.get_analysis()
    except Exception:
        return None

# --- UI Setup ---
st.set_page_config(page_title="Sniper Engine Pro", layout="wide")
st.title(f"🎯 Sniper Engine | {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')}")

st.sidebar.header("🎯 Strategy Settings")
selected_strat = st.sidebar.selectbox("Signal Logic", [
    "VWAP + RSI > 50 (Whale Logic)", 
    "TV Summary (Strong Buy)"
])

st.sidebar.header("📊 Market Settings")
p_tf = st.sidebar.selectbox("Timeframe", list(TV_INTERVALS.keys()), index=2)
tickers_input = st.sidebar.text_area("Tickers", "COMI.CA, FWRY.CA, ETEL.CA, NVDA, GC=F")
SCAN_LIST = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if "active" not in st.session_state: st.session_state.active = False
if st.sidebar.button("🚀 Start"): st.session_state.active = True
if st.sidebar.button("🛑 Stop"): st.session_state.active = False

# --- Main Engine ---
if st.session_state.active:
    st.info(f"🛰️ Scanning: {selected_strat}")
    table_placeholder = st.empty()

    while True:
        results = []
        for ticker in SCAN_LIST:
            analysis = get_tv_analysis(ticker, p_tf)
            
            if not analysis:
                results.append({"Ticker": ticker, "Status": "⚠️ Not Found", "Price": 0, "RSI": "N/A"})
                continue

            # Data Extraction
            price = analysis.indicators["close"]
            rsi = analysis.indicators["RSI"]
            vwap = analysis.indicators.get("VWAP", 0)
            rec = analysis.summary["RECOMMENDATION"]
            
            # Whale Logic: Price > VWAP and RSI > 50
            match = False
            if selected_strat == "VWAP + RSI > 50 (Whale Logic)":
                match = (price > vwap) and (rsi > 50)
            else:
                match = (rec == "STRONG_BUY")

            results.append({
                "Ticker": ticker,
                "Status": "🎯 MATCH" if match else "❌ " + rec.replace("_", " "),
                "Price": round(price, 4),
                "RSI": round(rsi, 2),
                "Update": datetime.now(CAIRO_TZ).strftime("%H:%M:%S")
            })

            if match:
                msg = f"🎯 *MATCH: {ticker}*\nPrice: {price}\nRSI: {round(rsi,2)}"
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                  json={"chat_id": DEFAULT_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
                except: pass

        table_placeholder.table(pd.DataFrame(results))
        time.sleep(60)
        st.rerun()
