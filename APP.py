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
    st.error("🔑 Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Deep Insight", page_icon="🌤️", layout="wide")

# 2. 데이터 처리 함수 (Stable 버전 최적화)
@st.cache_data(ttl=600)
def get_stable_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

def get_ai_weather(verdict):
    v = verdict.upper()
    if "STRONG BUY" in v or "BUY" in v: return "☀️ 쾌청 (매수 추천)", "#FF4B4B"
    elif "SELL" in v: return "🌧️ 비 (매수 비추천)", "#4B89FF"
    else: return "☁️ 흐림 (중립/관망)", "#BEBEBE"

# 3. GPT-4o 고성능 분석 엔진 (최신 뉴스 반영)
def ask_gpt_deep_insight(ticker, s_info, recent_news):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    # 뉴스 데이터를 텍스트로 합쳐서 GPT에게 전달
    news_context = "\n".join([f"- {n['title']}: {n['text'][:200]}" for n in recent_news]) if recent_news else "No recent news found."
    
    prompt = f"""
    [ROLE]: Senior Equity Research Analyst at a Global Investment Bank.
    [TASK]: Write a highly detailed, 1500-word equivalent institutional-grade report for {ticker}.
    
    [DATA PROVIDED]:
    - Current Market Data: {json.dumps(s_info)}
    - Recent News & Issues: {news_context}
    
    [REPORT STRUCTURE]:
    1. **Executive Summary**: Core investment thesis.
    2. **Recent Catalyst Analysis**: Detailed analysis of the news provided above and how they impact the stock price.
    3. **Quantitative Deep Dive**: Valuation metrics (PER, Market Cap) vs Industry averages.
    4. **Risk Factors**: Identify specific downside risks.
    5. **Technical Outlook**: Analyze recent price trends.
    6. **Final Investment Verdict**: End with exactly one: [VERDICT: BUY], [VERDICT: HOLD], or [VERDICT: SELL].
    
    [STYLE]: Professional, objective, and analytical. Use Markdown formatting. Output in ENGLISH.
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a top-tier financial analyst specializing in deep fundamental and news-driven analysis."}, 
                     {"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 분석 중 오류가 발생했습니다: {e}. [VERDICT: HOLD]"

# 4. 메인 화면 구성
st.markdown("<h1 style='text-align: center;'>🏛️ Tetrades Deep Insight</h1>", unsafe_allow_html=True)

col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
with col_s2:
    ticker_input = st.text_input("", placeholder="티커 입력 (예: MU, AAPL, PLTR)", label_visibility="collapsed").upper()
    search_clicked = st.button("전문 AI 심층 분석 실행", use_container_width=True, type="primary")

st.divider()

# 좌측 뉴스 | 우측 히트맵
m1, m2 = st.columns([1.2, 1])
with m1:
    st.subheader("📰 실시간 글로벌 마켓 뉴스")
    # 뉴스 안정성을 위해 여러 엔드포인트 시도
    news_data = get_stable_data("stock-news-sentiments-rss", "limit=10")
    if not news_data:
        news_data = get_stable_data("stock-news", "limit=10")
    
    if news_data:
        for n in news_data[:5]:
            with st.expander(f"📌 {n.get('title', 'News')[:70]}..."):
                st.write(f"**출처:** {n.get('site')} | {n.get('publishedDate')}")
                st.write(n.get('text', ''))
                st.link_button("기사 원문 읽기", n.get('url', '#'))
    else:
        st.info("실시간 뉴스를 동기화 중입니다. 1~2분 후 새로고침(F5) 해주세요.")

with m2:
    st.subheader("🔥 글로벌 섹터 히트맵")
    components.html('<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>', height=520)

# 5. 종목 분석 실행
if search_clicked and ticker_input:
    st.divider()
    with st.spinner(f"최신 이슈를 포함하여 {ticker_input}를 정밀 분석 중..."):
        # 데이터 수집 (최신 뉴스 포함)
        s_data = get_stable_data("quote", f"symbol={ticker_input}")
        ticker_news = get_stable_data("stock-news", f"symbol={ticker_input}&limit=5")
        
        if s_data:
            s = s_data[0]
            # [핵심] 수집된 뉴스를 GPT에게 전달하여 리포트 작성
            report_text = ask_gpt_deep_insight(ticker_input, s, ticker_news)
            w_label, w_color = get_ai_weather(report_text)
            
            # 대시보드 출력
            st.markdown(f"## {ticker_input} 투자 기상도: <span style='color:{w_color};'>{w_label}</span>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
            c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            c3.metric("52주 최고", f"${s.get('yearHigh', 0):,.2f}")
            c4.metric("PER", s.get('pe', 'N/A'))

            st.subheader("📑 Institutional Equity Research Report")
            st.markdown(report_text)
        else:
            st.error("데이터 로딩 실패. 티커와 API 상태를 확인하세요.")
