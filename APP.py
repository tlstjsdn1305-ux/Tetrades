import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------------------------------------
# API KEY (보안 금고에서 가져옴)
# ---------------------------------------------------------
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

ssl_context = ssl._create_unverified_context()

# ---------------------------------------------------------
# 1. 현재 주가 데이터 가져오기 (Quote)
# ---------------------------------------------------------
def get_stock_data(ticker):
    base_url = "https://financialmodelingprep.com/stable/quote"
    url = f"{base_url}?symbol={ticker}&apikey={FMP_API_KEY}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
    except Exception as e:
        print(f"현재가 에러: {e}")
        return None

# ---------------------------------------------------------
# 1-1. 과거 데이터 가져오기 (stable 엔드포인트)
# ---------------------------------------------------------
def get_historical_data(ticker):
    base_url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
    url = f"{base_url}?symbol={ticker}&apikey={FMP_API_KEY}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            hist_list = []
            if isinstance(data, dict) and "historical" in data:
                hist_list = data["historical"]
            elif isinstance(data, list):
                hist_list = data
                
            # [수정 완료] 오류가 났던 부분입니다! 끝에 > 0: 이 누락되지 않도록 수정했습니다.
            if hist_list and len(hist_list) > 0:
                hist_list.sort(key=lambda x: x.get('date', ''))
                return hist_list
            return []
    except Exception as e:
        print(f"과거 데이터 에러: {e}")
        return None

# ---------------------------------------------------------
# 2. GPT 가중치 분석 요청
# ---------------------------------------------------------
def ask_gpt_analysis(ticker, stock_info, history_summary):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    prompt = f"""
    **Subject**: Weighted Investment Analysis Report for {ticker}
    **Current Market Data**: {json.dumps(stock_info)}
    **Historical Performance Summary**: {history_summary}
    
    **ROLE**: Chief Equity Strategist at a top-tier Wall Street investment bank.
    **TASK**: Write a highly detailed, professional investment report in ENGLISH.
    
    **📈 WEIGHTED ANALYSIS GUIDELINE**:
    1. **Short-Term Momentum (Weight 50%)**: Current price, 50-day MA, volume.
    2. **Medium-Term Performance (Weight 30%)**: 3-Year return trend.
    3. **Long-Term Fundamentals (Weight 20%)**: 10-Year return and viability.
    
    **REPORT STRUCTURE**:
    1.  **Executive Summary**: High-level verdict.
    2.  **Trend Analysis (Short vs. Long)**: Detailed comparison.
    3.  **Risk & Volatility Assessment**: Analyze downside risks.
    4.  **Final Investment Verdict**: STRONG BUY / BUY / HOLD / SELL with justification.
    
    **Output Format**: Use Markdown, professional tone, very long paragraphs.
    """

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a senior financial analyst providing institutional-grade weighted analysis."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        return f"GPT Error: {e}"

# ---------------------------------------------------------
# 3. Streamlit 화면 
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="Pro Stock Analyst AI", page_icon="📊", layout="wide")

    st.title("🏛️ Institutional AI Equity Research (Weighted)")
    st.markdown("**Multi-Timeframe Analysis:** Combines Real-time Data (50%), 3-Year History (30%), and 10-Year History (20%) for a balanced investment verdict.")

    with st.sidebar:
        st.header("🔎 Ticker Search")
        ticker = st.text_input("Enter Symbol (e.g., AAPL, NVDA)", value="AAPL").upper()
        run_btn = st.button("Generate Deep Report", type="primary")

    if run_btn:
        if not ticker:
            st.warning("Please enter a valid ticker symbol.")
            return

        with st.spinner(f"Fetching data for {ticker} and running AI analysis..."):
            stock_data = get_stock_data(ticker)
            historical_data = get_historical_data(ticker)

            if stock_data is None:
                st.error("❌ 현재가(Quote) 데이터를 가져오는데 실패했습니다. 티커가 정확한지 확인하세요.")
            elif historical_data is None or len(historical_data) == 0:
                st.error("❌ 과거 장기(Historical) 데이터를 가져오는데 실패했습니다.")
            else:
                df = pd.DataFrame(historical_data)
                df['date'] = pd.to_datetime(df['date'])
                
                latest_price = df.iloc[-1]['close'] if 'close' in df.columns else stock_data.get('price', 0)
                latest_date = df.iloc[-1]['date']
                
                date_3y = latest_date - timedelta(days=365*3)
                date_10y = latest_date - timedelta(days=365*10)
                
                row_3y = df.iloc[(df['date'] - date_3y).abs().argsort()[:1]]
                row_10y = df.iloc[(df['date'] - date_10y).abs().argsort()[:1]]
                
                price_3y = row_3y['close'].values[0] if not row_3y.empty else None
                price_10y = row_10y['close'].values[0] if not row_10y.empty else None
                
                return_3y = ((latest_price - price_3y) / price_3y * 100) if price_3y else 0
                return_10y = ((latest_price - price_10y) / price_10y * 100) if price_10y else 0
                
                history_summary = f"""
                - Current Price: ${latest_price}
                - Price 3 Years Ago: ${price_3y} (Return: {return_3y:.2f}%)
                - Price 10 Years Ago: ${price_10y} (Return: {return_10y:.2f}%)
                """

                st.subheader(f"📊 Market Data Dashboard: {ticker}")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price", f"${stock_data.get('price', 0):,.2f}", f"{stock_data.get('changesPercentage', 0)}%")
                col2.metric("Market Cap", f"${stock_data.get('marketCap', 0):,}")
                col3.metric("52W High", f"${stock_data.get('yearHigh', 0):,.2f}")
                col4.metric("PE Ratio", stock_data.get('pe', 'N/A'))

                col5, col6, col7 = st.columns(3)
                col5.metric("📅 3-Year Return", f"{return_3y:,.2f}%")
                col6.metric("📅 10-Year Return", f"{return_10y:,.2f}%")
                col7.metric("Data Period", f"{len(df)} Trading Days")

                st.divider()

                st.subheader("📈 1-Year Price Trend")
                df_1y = df.tail(250).set_index("date")
                if 'close' in df_1y.columns:
                    st.line_chart(df_1y['close'], color="#00FF00")

                st.divider()

                st.subheader(f"📑 Weighted AI Analyst Report")
                with st.container():
                    analysis_result = ask_gpt_analysis(ticker, stock_data, history_summary)
                    st.markdown(analysis_result)
                    st.success("Analysis complete.")

if __name__ == "__main__":
    main()
