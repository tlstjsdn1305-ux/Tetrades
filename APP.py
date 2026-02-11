import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime
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

# 2. 데이터 처리 함수 (Stable 버전)
@st.cache_data(ttl=600)
def get_stable_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

def get_weather(change):
    if change is None: return "⚪ 정보 없음", "#BEBEBE"
    if change > 1.5: return "☀️ 쾌청 (Strong Bull)", "#FF4B4B"
    elif change > 0.3: return "🌤️ 맑음 (Bullish)", "#FF8C8C"
    elif change > -0.3: return "☁️ 흐림 (Neutral)", "#BEBEBE"
    elif change > -1.5: return "🌧️ 비 (Bearish)", "#4B89FF"
    else: return "⛈️ 폭풍우 (Strong Bear)", "#0042ED"

# 3. GPT-4o 심층 분석 엔진
def ask_gpt_deep_analysis(ticker, s_info, h_summary):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    prompt = f"""
    **TASK**: Conduct a professional equity research analysis for {ticker}.
    **DATA**: Current Quote: {json.dumps(s_info)}, History Summary: {h_summary}
    **ROLE**: Senior Wall Street Strategist.
    **STRUCTURE**:
    1. Executive Summary
    2. Quantitative Trend Analysis
    3. Risk Assessment
    4. Final Verdict (STRONG BUY/BUY/HOLD/SELL)
    **FORMAT**: Use professional Markdown with bold headers. Output in ENGLISH.
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a top-tier institutional financial analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 분석 중 오류 발생: {e}"

# 4. 메인 UI 구성
st.markdown("<h1 style='text-align: center;'>🏛️ Tetrades Intelligence</h1>", unsafe_allow_html=True)

col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
with col_s2:
    ticker_input = st.text_input("", placeholder="분석할 티커(예: AAPL, NVDA, TSLA)", label_visibility="collapsed").upper()
    search_clicked = st.button("AI 심층 분석 및 기상도 확인", use_container_width=True, type="primary")

st.divider()

# 5. 뉴스 및 히트맵 섹션
m_col1, m_col2 = st.columns([1.2, 1])

with m_col1:
    st.subheader("📰 실시간 세계 경제 뉴스")
    news = get_stable_data("stock-news", "limit=8")
    if news:
        for n in news[:5]:
            with st.expander(f"📌 {n.get('title', '')[:60]}..."):
                st.write(f"**{n.get('site', 'News')}** | {n.get('publishedDate', '')}")
                st.write(n.get('text', ''))
                st.link_button("기사 원문 보기", n.get('url', '#'))
    else:
        st.info("뉴스를 불러오는 중입니다. FMP 이메일 인증 여부를 확인해주세요.")

with m_col2:
    st.subheader("🔥 글로벌 시장 히트맵")
    heatmap_html = '<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>'
    components.html(heatmap_html, height=520)

# 6. 종목 심층 분석 실행 (검색 시)
if search_clicked and ticker_input:
    st.divider()
    with st.spinner(f"AI 애널리스트가 {ticker_input}를 정밀 분석 중입니다..."):
        # 데이터 수집
        s_data = get_stable_data("quote", f"symbol={ticker_input}")
        h_data = get_stable_data("historical-price-eod/full", f"symbol={ticker_input}")
        
        if s_data and len(s_data) > 0:
            s = s_data[0]
            change = s.get('changesPercentage', s.get('changePercentage', 0))
            st_w, st_c = get_weather(change)
            
            # (1) 투자 기상도 및 핵심 지표
            st.markdown(f"## {s.get('name', ticker_input)} 투자 기상도: <span style='color:{st_c};'>{st_w}</span>", unsafe_allow_html=True)
            
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{change:.2f}%")
            sc2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            sc3.metric("52주 최고", f"${s.get('yearHigh', 0):,.2f}")
            sc4.metric("PER", s.get('pe', 'N/A'))

            # (2) 차트 출력
            if h_data and 'historical' in h_data:
                df = pd.DataFrame(h_data['historical']).tail(120)
                df['date'] = pd.to_datetime(df['date'])
                st.line_chart(df.set_index('date')['close'])
                h_summary = f"Recent high: {df['high'].max()}, Recent low: {df['low'].min()}"
            else:
                h_summary = "Historical data unavailable."

            # (3) GPT 전문 분석 리포트
            st.subheader("📑 AI Institutional Research Report")
            report = ask_gpt_deep_analysis(ticker_input, s, h_summary)
            st.markdown(report)
            st.success("✅ 심층 분석 리포트 생성이 완료되었습니다.")
        else:
            st.error(f"'{ticker_input}' 데이터를 가져올 수 없습니다. 티커가 정확한지 확인하세요.")
