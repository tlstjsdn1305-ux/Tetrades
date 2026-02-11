import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 보안 설정 및 테마 정의 (미드나이트 네이비 & 샴페인 골드)
# ---------------------------------------------------------
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
except:
    st.error("🔑 Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Premium", page_icon="🏛️", layout="wide")

# 세련된 금융기관 스타일 CSS
st.markdown("""
    <style>
    /* 전체 배경 (미드나이트 네이비) 및 텍스트 (플래티넘 화이트) */
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    
    /* 헤더 스타일 (샴페인 골드) */
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; letter-spacing: 0.5px; }
    
    /* 버튼 스타일 (고스트 버튼 형태의 모던 럭셔리) */
    .stButton > button { 
        background-color: transparent; 
        color: #C8AA6E; 
        font-weight: 600; 
        border-radius: 4px; 
        border: 1px solid #C8AA6E; 
        transition: 0.3s; 
    }
    .stButton > button:hover { background-color: #C8AA6E; color: #0B1320; }
    
    /* 입력창 스타일 */
    .stTextInput > div > div > input { background-color: #151E2D; border: 1px solid #2A3B52; color: #E2E8F0; }
    .stTextInput > div > div > input:focus { border-color: #C8AA6E; box-shadow: none; }
    
    /* 갱신 시간 텍스트 */
    .update-time { color: #64748B; font-size: 0.85rem; text-align: right; margin-bottom: -15px; }
    
    /* 은은한 구분선 */
    hr { border: 0; height: 1px; background: #1E293B; }
    
    /* 메트릭(지표) 숫자 색상 */
    [data-testid="stMetricValue"] { color: #F8FAFC !important; }
    
    /* 탭 스타일 정제 */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    
    /* 채팅/토론방 박스 */
    .chat-msg { background-color: #151E2D; padding: 15px; border-radius: 6px; border-left: 2px solid #334155; margin-bottom: 12px; font-size: 0.95rem; }
    .chat-msg b { color: #C8AA6E; }
    
    /* 프리미엄 카드 박스 */
    .premium-card { background-color: #0F172A; border: 1px solid #1E293B; padding: 25px; border-radius: 8px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 상단 정보 (갱신 시간 & 티커 테이프)
# ---------------------------------------------------------
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p class='update-time'>Market Data Sync: {now}</p>", unsafe_allow_html=True)

ticker_tape_html = """
<div style="height:40px; border-bottom: 1px solid #1E293B; margin-bottom: 30px; margin-top: 10px;">
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{
  "symbols": [
    {"proName": "FOREXCOM:SPX500", "title": "S&P 500"},
    {"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"},
    {"proName": "NASDAQ:AAPL", "title": "Apple"},
    {"proName": "NASDAQ:NVDA", "title": "NVIDIA"},
    {"proName": "NASDAQ:MU", "title": "Micron"}
  ],
  "colorTheme": "dark", "isTransparent": true, "displayMode": "adaptive", "locale": "ko"
}
</script>
</div>
"""
components.html(ticker_tape_html, height=50)

st.markdown("<h1 style='text-align: center; letter-spacing: 3px; margin-bottom: 40px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 데이터 처리 및 AI 엔진 함수
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_api_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

@st.cache_data(ttl=3600)
def get_analyst_consensus(ticker):
    url = f"https://financialmodelingprep.com/api/v3/analyst-stock-recommendations/{ticker}?limit=1&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data[0] if data else "No analyst consensus available."
    except: return "No analyst consensus available."

def get_ai_weather(verdict):
    v = verdict.upper()
    if "STRONG BUY" in v or "BUY" in v: return "📈 긍정적 (Positive)", "#10B981" # 차분한 녹색
    elif "SELL" in v: return "📉 부정적 (Negative)", "#EF4444" # 차분한 붉은색
    else: return "⚖️ 관망 (Neutral)", "#94A3B8" # 슬레이트 그레이

# GPT-4o 90일 예측 가중치 엔진
def ask_gpt_90day_forecast(ticker, s_info, recent_news, consensus):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    news_text = "\n".join([f"- {n['title']}" for n in recent_news]) if recent_news else "No recent news."
    
    prompt = f"""
    [ROLE]: Institutional Lead Quant Analyst.
    [TASK]: Forecast {ticker}'s stock performance for the next 90 DAYS using the strict Multi-Factor Weighting Model below.

    [DATA PROVIDED]:
    - Market Data: {json.dumps(s_info)}
    - Analyst Consensus: {json.dumps(consensus)}
    - Recent News/Policy Issues: {news_text}

    [WEIGHTING MODEL (Total 100%)]:
    1. Fundamentals (30%): Earnings, Valuation (PER, Market Cap).
    2. Macro & Policy (25%): Interest rates, sector subsidies, regulations.
    3. Technical Momentum (20%): Price trends, moving averages implied.
    4. Analyst Consensus (15%): Institutional sentiment provided.
    5. News & Psychology (10%): Short-term catalyst impact.

    [REPORT STRUCTURE]:
    Write a highly professional institutional-grade report in KOREAN (Markdown formatted).
    1. **Tetrades AI 90일 상승 예측도**: (예: 78% 상승 전망) -> Must be at the top. Do not use the word '승률'.
    2. **멀티 팩터 분석 요약**: 위 5가지 팩터가 각각 어떻게 작용했는지 점수나 상태(우수/위험 등) 표기.
    3. **거시경제 및 정책 동향 (Macro/Policy)**: 90일 내 영향을 줄 거시경제/정책 심층 분석.
    4. **기관 투자자 컨센서스**: 제공된 Consensus 데이터 해석.
    5. **최종 투자 전략 요약**: 향후 90일 기관 관점의 전략.
    
    [RULE]: At the very end of the report, write EXACTLY one of: [VERDICT: STRONG BUY], [VERDICT: BUY], [VERDICT: HOLD], or [VERDICT: SELL]. Maintain a serious, objective tone.
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a highly professional quantitative AI analyst."}, 
                     {"role": "user", "content": prompt}],
        "temperature": 0.4
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 분석 중 오류 발생: {e} \n\n[VERDICT: HOLD]"

# ---------------------------------------------------------
# 6. 메인 콘텐츠 (탭 구조)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 퀀트 리서치", "💬 투자자 라운지", "🏆 멤버십 & 랭킹"])

# [Tab 1] AI 분석 탭
with tab1:
    col_main1, col_main2 = st.columns([2, 1])
    with col_main1:
        st.subheader("Institutional AI Analysis")
        ticker_input = st.text_input("", placeholder="종목 심볼 입력 (예: AAPL, PLTR, MU)", label_visibility="collapsed").upper()
        search_clicked = st.button("AI 심층 리포트 생성", type="primary", use_container_width=True)

    if search_clicked and ticker_input:
        st.divider()
        with st.spinner(f"글로벌 금융 데이터 기반 {ticker_input} 멀티 팩터 분석 중..."):
            s_data = get_api_data("quote", f"symbol={ticker_input}")
            ticker_news = get_api_data("stock-news", f"symbol={ticker_input}&limit=5")
            analyst_data = get_analyst_consensus(ticker_input)
            
            if s_data and len(s_data) > 0:
                s = s_data[0]
                report_text = ask_gpt_90day_forecast(ticker_input, s, ticker_news, analyst_data)
                w_label, w_color = get_ai_weather(report_text)
                
                # 대시보드
                st.markdown(f"## {ticker_input} 90일 AI 전망: <span style='color:{w_color};'>{w_label}</span>", unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
                c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                c3.metric("52주 최고가", f"${s.get('yearHigh', 0):,.2f}")
                c4.metric("PER (주가수익비율)", s.get('pe', 'N/A'))

                # 차트
                h_data = get_api_data("historical-price-eod/full", f"symbol={ticker_input}")
                if h_data and 'historical' in h_data:
                    df = pd.DataFrame(h_data['historical']).tail(120)
                    df['date'] = pd.to_datetime(df['date'])
                    st.line_chart(df.set_index('date')['close'])

                # 리포트 출력 영역 (모던 네이비 테마 적용)
                st.subheader("📑 90-Day Multi-Factor Research Report")
                styled_report_container = f"""
                <div style="
                    background-color: #151E2D; 
                    padding: 35px;
                    border-radius: 8px;
                    border: 1px solid #2A3B52; 
                    color: #E2E8F0; 
                    line-height: 1.8; 
                    font-size: 1.05rem;
                ">
                    {report_text}
                </div>
                """
                st.markdown(styled_report_container, unsafe_allow_html=True)
                
            else:
                st.error("데이터 로딩 실패. 종목 심볼을 다시 확인해 주십시오.")

# [Tab 2] 커뮤니티 탭
with tab2:
    col_chat1, col_chat2 = st.columns(2)
    with col_chat1:
        st.subheader("🌐 글로벌 투자자 라운지")
        st.markdown("<div class='chat-msg'><b>[인텔리전스] 퀀트매니저</b>: 이번 달 반도체 섹터 정책 가중치가 상향 조정되었습니다.</div>", unsafe_allow_html=True)
        st.markdown("<div class='chat-msg'><b>[프리미엄] 투자자A</b>: 테슬라 90일 상승 예측도가 꽤 높게 나왔네요.</div>", unsafe_allow_html=True)
        st.text_input("메시지 입력 (프리미엄 회원 전용)...", key="g_chat")
    
    with col_chat2:
        st.subheader("📊 개별 종목 토론방")
        st.info("AI 분석을 1회 이상 실행한 종목의 토론방만 활성화됩니다.")

# [Tab 3] 랭킹 및 멤버십 탭
with tab3:
    col_rank1, col_rank2 = st.columns([2, 1])
    with col_rank1:
        st.subheader("파트너 애널리스트 랭킹")
        st.markdown("""
        | 순위 | 멤버십 등급 | 닉네임 | 파트너 리워드 누적 | 배지 |
        | :--- | :--- | :--- | :--- | :--- |
        | 1 | 🏛️ 수석 파트너 | PrivateK | 152,100 원 | [Black] |
        | 2 | 📊 시니어 파트너 | TechQuant | 88,200 원 | [Navy] |
        | 3 | 📈 어소시에이트 | AutoBot | 51,300 원 | [Steel] |
        """)
    with col_rank2:
        # 멤버십 결제 카드
        st.markdown("""
        <div class='premium-card'>
            <h3 style='margin-top:0;'>Tetrades Premium</h3>
            <p style='font-size: 0.9em; color: #94A3B8; margin-bottom: 25px;'>
                무제한 90일 멀티 팩터 퀀트 리서치<br>
                광고 제거 및 프라이빗 라운지 입장
            </p>
            <p style='color: #E2E8F0; font-size: 2.2em; font-weight: 700; margin: 0;'>₩9,900<span style='font-size:0.4em; color:#64748B;'> /월</span></p>
            <button style='width:100%; padding:14px; margin-top: 20px; background-color:transparent; color:#C8AA6E; font-weight:bold; border:1px solid #C8AA6E; border-radius:4px; cursor: pointer; transition: 0.3s;' onmouseover="this.style.backgroundColor='#C8AA6E'; this.style.color='#0B1320';" onmouseout="this.style.backgroundColor='transparent'; this.style.color='#C8AA6E';">
                프리미엄 멤버십 시작하기
            </button>
            <hr style='margin: 25px 0;'>
            <p style='font-size: 0.85em; color:#64748B; text-align: left;'>
                🤝 <b>파트너 리워드 프로그램</b><br>
                추천 가입자 1명당 <b>900원</b> 평생 누적 적립.
            </p>
        </div>
        """, unsafe_allow_html=True)
