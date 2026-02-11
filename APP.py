import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 1. 보안 설정 및 API 키 로드
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
except:
    st.error("🔑 Streamlit Secrets에 API 키가 설정되지 않았습니다.")
    st.stop()

ssl_context = ssl._create_unverified_context()

st.set_page_config(page_title="Tetrades Intelligence", page_icon="🌤️", layout="wide")

# 2. [핵심 수정] 데이터 캐싱 적용 (로딩 속도 개선)
# 한 번 불러온 데이터는 10분(600초) 동안 다시 불러오지 않고 즉시 보여줍니다.
@st.cache_data(ttl=600)
def get_api_data(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return None

def get_weather(change):
    if change is None: return "⚪ 알 수 없음", "#BEBEBE"
    if change > 1.5: return "☀️ 쾌청 (Strong Bull)", "#FF4B4B"
    elif change > 0.3: return "🌤️ 맑음 (Bullish)", "#FF8C8C"
    elif change > -0.3: return "☁️ 흐림 (Neutral)", "#BEBEBE"
    elif change > -1.5: return "🌧️ 비 (Bearish)", "#4B89FF"
    else: return "⛈️ 폭풍우 (Strong Bear)", "#0042ED"

# 3. GPT 분석 함수 (캐싱 제외 - 매번 새로운 분석 필요)
def ask_gpt_analysis(ticker, stock_info):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    prompt = f"Write a professional investment report for {ticker}. Data: {json.dumps(stock_info)}. Use Markdown."
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a Wall Street analyst."}, {"role": "user", "content": prompt}]
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except: return "AI 리포트 생성 중 오류가 발생했습니다."

# 4. 메인 화면 구성
st.markdown("<h1 style='text-align: center;'>🏛️ Tetrades Intelligence</h1>", unsafe_allow_html=True)

# 중앙 검색창
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    ticker_input = st.text_input("", placeholder="분석할 주식 티커(예: AAPL, TSLA)", key="main_ticker").upper()
    search_btn = st.button("AI 심층 분석 및 기상도 확인", use_container_width=True, type="primary")

st.divider()

# 지수 대시보드
major_indices = ["^GSPC", "^IXIC", "^KS11", "^N225", "GC=F", "CL=F"]
index_names = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^KS11": "KOSPI", "^N225": "Nikkei", "GC=F": "Gold", "CL=F": "Oil"}
quotes = get_api_data(f"https://financialmodelingprep.com/api/v3/quote/{','.join(major_indices)}?apikey={FMP_API_KEY}")

if quotes:
    valid_changes = [q.get('changesPercentage', 0) for q in quotes if q.get('changesPercentage') is not None]
    avg_change = sum(valid_changes) / len(valid_changes) if valid_changes else 0
    w_label, w_color = get_weather(avg_change)
    st.markdown(f"<h3 style='text-align: center;'>오늘의 글로벌 투자 날씨: <span style='color:{w_color};'>{w_label}</span></h3>", unsafe_allow_html=True)
    idx_cols = st.columns(len(quotes))
    for i, q in enumerate(quotes):
        idx_cols[i].metric(index_names.get(q['symbol'], q['symbol']), f"{q.get('price', 0):,.2f}", f"{q.get('changesPercentage', 0):.2f}%")

st.divider()

# 뉴스 및 히트맵
m1, m2 = st.columns([1.2, 1])
with m1:
    st.subheader("📰 실시간 세계 경제 뉴스")
    news = get_api_data(f"https://financialmodelingprep.com/api/v3/stock_news?limit=10&apikey={FMP_API_KEY}")
    if news:
        for n in news[:6]:
            with st.expander(f"📌 {n['title'][:60]}..."):
                st.write(f"**{n['site']}** | {n['publishedDate']}\n\n{n['text']}")
                st.link_button("원문 읽기", n['url'])
    else: st.info("뉴스를 불러오는 중입니다... (잠시만 기다려주세요)")

with m2:
    st.subheader("🔥 글로벌 시장 히트맵")
    heatmap_html = '<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","grouping": "sector","blockSize": "market_cap","blockColor": "change","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>'
    components.html(heatmap_html, height=520)

# 5. 종목 분석 (검색 시 실행)
if search_btn and ticker_input:
    st.divider()
    with st.spinner(f"{ticker_input} 데이터를 정밀 분석 중..."):
        # 실시간 시세 데이터
        s_data = get_api_data(f"https://financialmodelingprep.com/api/v3/quote/{ticker_input}?apikey={FMP_API_KEY}")
        # 차트 데이터
        h_raw = get_api_data(f"https://financialmodelingprep.com/api/v3/historical-price-eod/{ticker_input}?limit=120&apikey={FMP_API_KEY}")
        
        if s_data and len(s_data) > 0:
            s = s_data[0]
            st_w, st_c = get_weather(s.get('changesPercentage', 0))
            st.markdown(f"## {s.get('name', ticker_input)} 투자 기상도: <span style='color:{st_c};'>{st_w}</span>", unsafe_allow_html=True)
            
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
            sc2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            sc3.metric("52주 최고", f"${s.get('yearHigh', 0):,.2f}")
            sc4.metric("PER", s.get('pe', 'N/A'))

            if h_raw and isinstance(h_raw, dict) and 'historical' in h_raw:
                df = pd.DataFrame(h_raw['historical'])
                df['date'] = pd.to_datetime(df['date'])
                st.line_chart(df.set_index('date')['close'])
            else:
                st.warning("⚠️ 차트 데이터를 불러오는 데 실패했습니다.")

            st.subheader("📑 AI Deep Analyst Report")
            report = ask_gpt_analysis(ticker_input, s)
            st.markdown(report)
        else:
            st.error(f"❌ '{ticker_input}' 티커 정보를 찾을 수 없습니다. 정확한 기호(예: AAPL, TSLA)인지 확인해주세요.")
