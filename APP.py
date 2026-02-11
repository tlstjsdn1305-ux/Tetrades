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
st.set_page_config(page_title="Tetrades", page_icon="🌤️", layout="wide")

# 2. 무료 플랜 맞춤형 데이터 함수 (가장 기본 주소 사용)
@st.cache_data(ttl=300)
def get_fmp_data(url_path):
    # 'stable' 대신 일반 v3 주소를 사용하여 무료 키 호환성 높임
    url = f"https://financialmodelingprep.com/api/v3/{url_path}&apikey={FMP_API_KEY}"
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

# 3. 메인 화면
st.title("🏛️ Tetrades Intelligence")
ticker = st.text_input("분석할 티커 입력 (예: TSLA, NVDA)").upper()

if ticker:
    # 종목 정보 (Quote)
    data = get_fmp_data(f"quote/{ticker}?")
    if data and len(data) > 0:
        s = data[0]
        w_label, w_color = get_weather(s.get('changesPercentage'))
        st.subheader(f"{ticker} 투자 기상도: {w_label}")
        
        # 기본 지표
        col1, col2 = st.columns(2)
        col1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
        col2.metric("시가총액", f"${s.get('marketCap', 0):,}")
        
        # 차트 (무료 플랜은 5년까지만 안전함)
        hist = get_fmp_data(f"historical-price-eod/{ticker}?limit=120") # 약 6개월치
        if hist and 'historical' in hist:
            df = pd.DataFrame(hist['historical'])
            st.line_chart(df.set_index('date')['close'])
    else:
        st.error(f"'{ticker}' 데이터를 가져올 수 없습니다. API 키 인증 메일을 확인해보세요.")

# 하단 히트맵 (항상 표시)
st.divider()
st.subheader("🔥 시장 히트맵")
components.html('<div style="height:500px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>{"dataSource": "S&P500","locale": "ko","colorTheme": "light","width": "100%","height": "100%"}</script></div>', height=520)
