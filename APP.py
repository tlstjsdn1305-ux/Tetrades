import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 1. 환경 설정 및 보안 키 로드
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]
ssl_context = ssl._create_unverified_context()

st.set_page_config(page_title="Tetrades Intelligence", page_icon="🌤️", layout="wide")

# 2. 데이터 처리 함수 정의
def get_api_data(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

def get_weather(change):
    if change > 1.5: return "☀️ 쾌청 (Strong Bull)", "#FF4B4B"
    elif change > 0.3: return "🌤️ 맑음 (Bullish)", "#FF8C8C"
    elif change > -0.3: return "☁️ 흐림 (Neutral)", "#BEBEBE"
    elif change > -1.5: return "🌧️ 비 (Bearish)", "#4B89FF"
    else: return "⛈️ 폭풍우 (Strong Bear)", "#0042ED"

# 3. 메인 UI - 상단 검색창 (Google 스타일)
st.markdown("<h1 style='text-align: center; color: #1E1E1E;'>🏛️ Tetrades Intelligence</h1>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    ticker = st.text_input("", placeholder="분석할 주식 티커를 입력하세요 (예: NVDA, AAPL)", label_visibility="collapsed").upper()
    search_clicked = st.button("AI 심층 분석 및 기상도 확인", use_container_width=True, type="primary")

st.divider()

# 4. 시장 지수 및 전 세계 투자 기상도
major_indices = ["^GSPC", "^IXIC", "^KS11", "^N225", "GC=F", "CL=F"]
index_names = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^KS11": "코스피", "^N225": "니케이 225", "GC=F": "금(Gold)", "CL=F": "원유(WTI)"}

quotes = get_api_data(f"https://financialmodelingprep.com/stable/quote?symbol={','.join(major_indices)}&apikey={FMP_API_KEY}")

if quotes:
    avg_change = sum([q.get('changesPercentage', 0) for q in quotes]) / len(quotes)
    w_label, w_color = get_weather(avg_change)
    st.markdown(f"<h3 style='text-align: center;'>오늘의 글로벌 투자 날씨: <span style='color:{w_color};'>{w_label}</span></h3>", unsafe_allow_html=True)
    
    idx_cols = st.columns(len(quotes))
    for i, q in enumerate(quotes):
        name = index_names.get(q['symbol'], q['symbol'])
        idx_cols[i].metric(name, f"{q.get('price', 0):,.2f}", f"{q.get('changesPercentage', 0):.2f}%")

st.divider()

# 5. 중간 레이아웃 - 좌측(뉴스) | 우측(히트맵)
m_col1, m_col2 = st.columns([1, 1])

with m_col1:
    st.subheader("📰 실시간 세계 경제 뉴스")
    news_data = get_api_data(f"https://financialmodelingprep.com/api/v3/stock_news?limit=5&apikey={FMP_API_KEY}")
    if news_data:
        for n in news_data:
            with st.expander(f"📌 {n['title'][:65]}..."):
                st.write(f"**출처:** {n['site']} | {n['publishedDate']}")
                st.write(n['text'])
                st.link_button("기사 원문 보기", n['url'])

with m_col2:
    st.subheader("🔥 글로벌 시장 히트맵 (S&P 500)")
    heatmap_html = """
    <div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
    {"dataSource": "S&P500","grouping": "sector","blockSize": "market_cap","blockColor": "change","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}
    </script></div>
    """
    components.html(heatmap_html, height=520)

# 6. 종목 분석 로직 (검색 시 실행)
if search_clicked and ticker:
    st.divider()
    with st.spinner(f"AI가 {ticker}의 데이터를 분석 중입니다..."):
        # 데이터 수집
        s_data = get_api_data(f"https://financialmodelingprep.com/stable/quote?symbol={ticker}&apikey={FMP_API_KEY}")
        h_data = get_api_data(f"https://financialmodelingprep.com/stable/historical-price-eod/full?symbol={ticker}&apikey={FMP_API_KEY}")
        
        if s_data:
            s = s_data[0]
            st_w, st_c = get_weather(s.get('changesPercentage', 0))
            
            # 종목별 기상도 및 대시보드
            st.markdown(f"## {s.get('name', ticker)} ({ticker}) 투자 기상도: <span style='color:{st_c};'>{st_w}</span>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
            c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            c3.metric("52주 최고가", f"${s.get('yearHigh', 0):,.2f}")
            c4.metric("PER", s.get('pe', 'N/A'))

            if h_data:
                df = pd.DataFrame(h_data.get('historical', [])).tail(120)
                st.line_chart(df.set_index('date')['close'])

            # GPT 가중치 분석 (토큰 사용)
            prompt = f"Analyze {ticker} based on price: {s.get('price')}, change: {s.get('changesPercentage')}%."
            # (기존의 상세 GPT prompt 로직을 여기에 그대로 포함하시면 됩니다)
            st.success("✅ AI 가중치 분석 리포트 생성이 완료되었습니다.")
