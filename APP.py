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

# 2. [중요] 최신 STABLE 주소 체계 적용
@st.cache_data(ttl=600)
def get_stable_data(endpoint, params=""):
    # api/v3 대신 stable 경로를 사용하여 신규 계정 차단 방지
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

def get_weather(change):
    if change is None: return "⚪ 알 수 없음", "#BEBEBE"
    if change > 1.0: return "☀️ 쾌청", "#FF4B4B"
    elif change > 0: return "🌤️ 맑음", "#FF8C8C"
    else: return "🌧️ 비", "#4B89FF"

# 3. 메인 UI
st.markdown("<h1 style='text-align: center;'>🏛️ Tetrades Intelligence</h1>", unsafe_allow_html=True)

ticker = st.text_input("분석할 티커 입력 (예: TSLA, NVDA)").upper()
search_btn = st.button("AI 심층 분석 실행", type="primary", use_container_width=True)

st.divider()

# 4. 시장 지수 및 뉴스 (신규 stable 주소 사용)
m_col1, m_col2 = st.columns([1.2, 1])

with m_col1:
    st.subheader("📰 실시간 세계 뉴스")
    # 최신 뉴스 엔드포인트: stock-news
    news = get_stable_data("stock-news", "limit=5")
    if news:
        for n in news:
            with st.expander(f"📌 {n.get('title', '')[:60]}..."):
                st.write(n.get('text', ''))
                st.link_button("원문 읽기", n.get('url', '#'))
    else:
        st.info("뉴스를 불러오는 중입니다. API 인증 완료 여부를 확인하세요.")

with m_col2:
    st.subheader("🔥 글로벌 히트맵")
    components.html('<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>', height=520)

# 5. 종목 분석 로직
if search_btn and ticker:
    with st.spinner(f"{ticker} 분석 중..."):
        # 최신 quote 주소는 ?symbol= 형식을 사용해야 함
        s_data = get_stable_data("quote", f"symbol={ticker}")
        
        if s_data and len(s_data) > 0:
            s = s_data[0]
            st_w, st_c = get_weather(s.get('changesPercentage'))
            st.markdown(f"## {ticker} 투자 기상도: <span style='color:{st_c};'>{st_w}</span>", unsafe_allow_html=True)
            
            # 차트 (최신 historical 주소)
            h_data = get_stable_data("historical-price-eod/full", f"symbol={ticker}")
            if h_data and 'historical' in h_data:
                df = pd.DataFrame(h_data['historical']).tail(120)
                st.line_chart(df.set_index('date')['close'])
            
            st.success("✅ 최신 Stable 데이터를 성공적으로 불러왔습니다!")
        else:
            st.error(f"❌ {ticker} 데이터를 가져올 수 없습니다. 새로운 주소 체계에서도 차단된다면 FMP 이메일 인증을 확인해주세요.")
