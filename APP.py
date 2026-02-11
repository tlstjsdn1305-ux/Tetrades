import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
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

# 2. 데이터 처리 함수 (Stable 버전 최적화)
@st.cache_data(ttl=600)
def get_stable_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

# 3. [개편] AI 분석 기반 날씨 결정 로직
def get_ai_weather(verdict):
    verdict = verdict.upper()
    if "STRONG BUY" in verdict or "BUY" in verdict:
        return "☀️ 쾌청 (매수 추천)", "#FF4B4B"
    elif "SELL" in verdict:
        return "🌧️ 비 (매수 비추천)", "#4B89FF"
    else:
        return "☁️ 흐림 (중립/관망)", "#BEBEBE"

# 4. GPT-4o 분석 엔진 (결과값에 VERDICT 포함 유도)
def ask_gpt_analysis(ticker, s_info):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    prompt = f"""
    Analyze {ticker}. Data: {json.dumps(s_info)}. 
    At the end of your report, YOU MUST write one of these keywords: [VERDICT: BUY], [VERDICT: HOLD], or [VERDICT: SELL].
    Write the report in ENGLISH.
    """
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "Professional Wall Street Analyst."}, {"role": "user", "content": prompt}]
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['choices'][0]['message']['content']
    except: return "AI 분석 중 오류가 발생했습니다. [VERDICT: HOLD]"

# 5. 메인 화면 구성
st.markdown("<h1 style='text-align: center;'>🏛️ Tetrades Intelligence</h1>", unsafe_allow_html=True)

col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
with col_s2:
    ticker_input = st.text_input("", placeholder="티커 입력 (예: AAPL, NVDA)", label_visibility="collapsed").upper()
    search_clicked = st.button("AI 심층 분석 및 기상도 확인", use_container_width=True, type="primary")

st.divider()

# 좌측 뉴스 | 우측 히트맵
m1, m2 = st.columns([1.2, 1])
with m1:
    st.subheader("📰 실시간 세계 경제 뉴스")
    # 뉴스 안정성을 위해 'stock-news-sentiments-rss' 주소 시도
    news_data = get_stable_data("stock-news-sentiments-rss", "limit=5")
    if not news_data: # 실패 시 일반 뉴스 재시도
        news_data = get_stable_data("stock-news", "limit=5")
    
    if news_data:
        for n in news_data:
            with st.expander(f"📌 {n.get('title', 'News')[:60]}..."):
                st.write(n.get('text', ''))
                st.link_button("원문 읽기", n.get('url', '#'))
    else:
        st.info("뉴스를 불러오는 중입니다. 잠시 후 새로고침(F5) 해주세요.")

with m2:
    st.subheader("🔥 글로벌 히트맵")
    components.html('<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>', height=520)

# 6. 종목 분석 (검색 시 실행)
if search_clicked and ticker_input:
    st.divider()
    with st.spinner(f"AI가 {ticker_input}의 운명을 결정하는 중..."):
        s_data = get_stable_data("quote", f"symbol={ticker_input}")
        
        if s_data:
            s = s_data[0]
            # [핵심] AI 리포트를 먼저 생성하여 날씨 결정
            report_text = ask_gpt_analysis(ticker_input, s)
            w_label, w_color = get_ai_weather(report_text)
            
            # 결과 출력
            st.markdown(f"## {ticker_input} 투자 기상도: <span style='color:{w_color};'>{w_label}</span>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
            c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            c3.metric("52주 최고", f"${s.get('yearHigh', 0):,.2f}")
            c4.metric("PER", s.get('pe', 'N/A'))

            st.subheader("📑 AI Deep Analyst Report")
            st.markdown(report_text)
        else:
            st.error("티커 정보를 불러올 수 없습니다.")
