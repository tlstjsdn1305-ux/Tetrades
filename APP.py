import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 보안 설정 및 테마 정의
# ---------------------------------------------------------
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
except:
    st.error("🔑 Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Gold", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Playfair Display', serif; }
    .stButton > button { background-color: #D4AF37; color: black; font-weight: 800; border-radius: 4px; border: none; }
    .stButton > button:hover { background-color: #AA8A2E; color: white; }
    .stTextInput > div > div > input { background-color: #111; border: 1px solid #D4AF37; color: white; }
    .update-time { color: #555; font-size: 0.8rem; text-align: right; margin-bottom: -10px; }
    hr { border: 0; height: 1px; background: linear-gradient(to right, transparent, #D4AF37, transparent); }
    [data-testid="stMetricValue"] { color: #FFD700 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #888; }
    .stTabs [aria-selected="true"] { color: #D4AF37 !important; border-bottom: 2px solid #D4AF37 !important; }
    .chat-msg { background-color: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #D4AF37; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 실시간 갱신 시간 및 상단 티커 테이프
# ---------------------------------------------------------
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p class='update-time'>Live Sync: {now}</p>", unsafe_allow_html=True)

ticker_tape_html = """
<div style="height:40px; border-bottom: 1px solid #D4AF37; margin-bottom: 20px;">
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
{
  "symbols": [
    {"proName": "FOREXCOM:SPX500", "title": "S&P 500"},
    {"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"},
    {"proName": "NASDAQ:AAPL", "title": "Apple"},
    {"proName": "NASDAQ:MU", "title": "Micron"},
    {"proName": "NYSE:PLTR", "title": "Palantir"}
  ],
  "colorTheme": "dark", "isTransparent": true, "displayMode": "adaptive", "locale": "ko"
}
</script>
</div>
"""
components.html(ticker_tape_html, height=50)

st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>TETRADES GOLD</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 데이터 처리 함수 (안전성 강화)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_api_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

# 월가 애널리스트 의견 가져오기 (v3 엔드포인트 사용)
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
    if "STRONG BUY" in v or "BUY" in v: return "☀️ 쾌청 (상승 확률 높음)", "#FF4B4B"
    elif "SELL" in v: return "🌧️ 비 (하락 위험)", "#4B89FF"
    else: return "☁️ 흐림 (관망)", "#BEBEBE"

# ---------------------------------------------------------
# 4. GPT-4o 90일 예측 가중치 엔진
# ---------------------------------------------------------
def ask_gpt_90day_forecast(ticker, s_info, recent_news, consensus):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    news_text = "\n".join([f"- {n['title']}" for n in recent_news]) if recent_news else "No recent news."
    
    prompt = f"""
    [ROLE]: Wall Street Lead Quant Analyst.
    [TASK]: Forecast {ticker}'s stock performance for the next 90 DAYS using the strict Multi-Factor Weighting Model below.

    [DATA PROVIDED]:
    - Market Data: {json.dumps(s_info)}
    - Analyst Consensus: {json.dumps(consensus)}
    - Recent News/Policy Issues: {news_text}

    [WEIGHTING MODEL]:
    1. Fundamentals (30%): Earnings, Valuation (PER, Market Cap).
    2. Macro & Policy (25%): Interest rates, sector subsidies, regulations.
    3. Technical Momentum (20%): Price trends, moving averages implied.
    4. Analyst Consensus (15%): Institutional sentiment provided.
    5. News & Psychology (10%): Short-term catalyst impact.

    [REPORT STRUCTURE]:
    Write a premium report in KOREAN (Markdown formatted).
    1. **Tetrades 90일 AI 예측 승률**: (예: 78% 상승 확률)
    2. **가중치 분석 요약**: 위 5가지 팩터가 각각 어떻게 작용했는지 점수나 상태(우수/위험 등) 표기.
    3. **핵심 정책 및 이슈 (Macro/Policy)**: 90일 내 영향을 줄 거시경제/정책 분석.
    4. **월가 애널리스트 동향**: 제공된 Consensus 데이터 해석.
    5. **최종 결론**: 향후 90일 전략.
    
    [RULE]: At the very end of the report, write EXACTLY one of: [VERDICT: STRONG BUY], [VERDICT: BUY], [VERDICT: HOLD], or [VERDICT: SELL].
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a quantitative AI forecasting the stock market 90 days out."}, 
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
# 5. UI 탭 및 메인 로직
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 AI 90-Day Forecast", "💬 Private Lounge", "🏆 Tetrades Elite"])

with tab1:
    st.subheader("Premium Stock Analysis")
    ticker_input = st.text_input("", placeholder="티커 입력 (예: AAPL, PLTR, MU)", label_visibility="collapsed").upper()
    search_clicked = st.button("RUN DEEP AI ANALYSIS", type="primary")

    if search_clicked and ticker_input:
        st.divider()
        with st.spinner(f"90일 멀티 팩터 가중치 모델로 {ticker_input}를 계산 중입니다..."):
            s_data = get_api_data("quote", f"symbol={ticker_input}")
            ticker_news = get_api_data("stock-news", f"symbol={ticker_input}&limit=5")
            analyst_data = get_analyst_consensus(ticker_input)
            
            if s_data and len(s_data) > 0:
                s = s_data[0]
                # AI 분석 실행 (한국어 리포트)
                report_text = ask_gpt_90day_forecast(ticker_input, s, ticker_news, analyst_data)
                w_label, w_color = get_ai_weather(report_text)
                
                # 대시보드
                st.markdown(f"## {ticker_input} 90일 기상도: <span style='color:{w_color};'>{w_label}</span>", unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"${s.get('price', 0):,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
                c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                c3.metric("52주 최고", f"${s.get('yearHigh', 0):,.2f}")
                c4.metric("PER", s.get('pe', 'N/A'))

                # 차트
                h_data = get_api_data("historical-price-eod/full", f"symbol={ticker_input}")
                if h_data and 'historical' in h_data:
                    df = pd.DataFrame(h_data['historical']).tail(120)
                    df['date'] = pd.to_datetime(df['date'])
                    st.line_chart(df.set_index('date')['close'])

                # 리포트 출력
                st.subheader("📑 90-Day Multi-Factor Quant Report")
                st.markdown(report_text)
            else:
                st.error("데이터를 불러오지 못했습니다. 티커를 확인하세요.")

with tab2:
    col_chat1, col_chat2 = st.columns(2)
    with col_chat1:
        st.subheader("🌐 Global Lounge")
        st.markdown("<div class='chat-msg'><b>[VIP] 골드회원</b>: 이번 달 무제한 분석 기능 정말 좋네요.</div>", unsafe_allow_html=True)
        st.markdown("<div class='chat-msg'><b>[Elite] 운영자</b>: 9,900원 멤버십 혜택이 다음 달에 더 추가될 예정입니다.</div>", unsafe_allow_html=True)
        st.text_input("메시지 입력 (유료 회원 전용)...", key="g_chat")
    
    with col_chat2:
        st.subheader("📊 종목 토론방")
        st.info("AI 분석을 1회 이상 실행한 종목의 토론방만 활성화됩니다.")

with tab3:
    col_rank1, col_rank2 = st.columns([2, 1])
    with col_rank1:
        st.subheader("Tetrades Hall of Fame")
        st.markdown("""
        | 순위 | 칭호 | 닉네임 | 누적 추천 캐시백 | 배지 |
        | :--- | :--- | :--- | :--- | :--- |
        | 1 | 👑 퀀트마스터 | 프라이빗K | 125,500원 | [Platinum] |
        | 2 | 💎 테크분석가 | 전기장인 | 68,300원 | [Gold] |
        | 3 | 🔱 선구자 | 자동화봇 | 42,600원 | [Silver] |
        """)
    with col_rank2:
        st.markdown("""
        <div style='border: 1px solid #D4AF37; padding: 15px; border-radius: 5px; background-color: #111;'>
            <h4 style='margin-top:0; color:#D4AF37;'>Tetrades Premium</h4>
            <p style='font-size: 0.9em; color: #CCC;'>광고 없는 90일 예측 무제한 분석 + VIP 전용 토론방</p>
            <p style='color: #FFD700; font-size: 1.5em; font-weight: bold;'>월 9,900원</p>
            <button style='width:100%; padding:10px; background-color:#D4AF37; color:black; font-weight:bold; border:none; border-radius:3px;'>구독하기</button>
            <hr style='margin: 15px 0 10px 0;'>
            <p style='font-size: 0.8em; color:#888;'>🤝 1명 추천 시 <b>900원</b> 평생 누적 적립</p>
        </div>
        """, unsafe_allow_html=True)
