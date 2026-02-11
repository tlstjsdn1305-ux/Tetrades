import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime
import pytz
import sqlite3
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
st.set_page_config(page_title="Tetrades Premium", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    /* 미드나이트 네이비 & 샴페인 골드 테마 */
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; }
    
    /* 우측 상단 로그인 버튼용 특수 스타일 */
    .login-btn > button { background-color: transparent; color: #E2E8F0; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; padding: 2px 15px; float: right; }
    .login-btn > button:hover { border-color: #C8AA6E; color: #C8AA6E; }
    
    /* 일반 버튼 고스트 스타일 */
    .stButton > button { background-color: transparent; color: #C8AA6E; font-weight: 600; border-radius: 4px; border: 1px solid #C8AA6E; transition: 0.3s; }
    .stButton > button:hover { background-color: #C8AA6E; color: #0B1320; }
    
    /* 입력창 중앙 정렬 및 디자인 */
    .stTextInput > div > div > input { background-color: #151E2D; border: 1px solid #2A3B52; color: #E2E8F0; text-align: center; font-size: 1.1rem; }
    .stTextInput > div > div > input:focus { border-color: #C8AA6E; box-shadow: none; }
    
    /* 갱신 시간 텍스트 */
    .update-time { color: #64748B; font-size: 0.85rem; text-align: right; margin-bottom: -10px; }
    
    /* 탭 중앙 정렬 및 디자인 */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 40px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    
    /* 리포트 카드 박스 */
    .report-card { background-color: #151E2D; padding: 35px; border-radius: 8px; border: 1px solid #2A3B52; color: #E2E8F0; line-height: 1.8; font-size: 1.05rem; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터베이스(DB) 초기화 및 관리 함수
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('tetrades.db')
    c = conn.cursor()
    # 예측 기록 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS predictions 
                 (date TEXT, ticker TEXT, price REAL, verdict TEXT)''')
    # 공지사항 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS announcements 
                 (date TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_prediction(ticker, price, verdict):
    conn = sqlite3.connect('tetrades.db')
    c = conn.cursor()
    now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO predictions VALUES (?, ?, ?, ?)", (now_kst, ticker, price, verdict))
    conn.commit()
    conn.close()

def save_announcement(content):
    conn = sqlite3.connect('tetrades.db')
    c = conn.cursor()
    now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO announcements VALUES (?, ?)", (now_kst, content))
    conn.commit()
    conn.close()

def load_announcements():
    conn = sqlite3.connect('tetrades.db')
    df = pd.read_sql_query("SELECT * FROM announcements ORDER BY date DESC", conn)
    conn.close()
    return df

init_db() # 앱 실행 시 DB 준비

# ---------------------------------------------------------
# 3. 최상단 UI (로그인 & 한국시간 동기화)
# ---------------------------------------------------------
top1, top2 = st.columns([8, 2])
with top2:
    st.markdown("<div class='login-btn'>", unsafe_allow_html=True)
    st.button("로그인 / 가입", key="login")
    st.markdown("</div>", unsafe_allow_html=True)

kst = pytz.timezone('Asia/Seoul')
now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p class='update-time'>Market Data Sync: {now_str} (KST 한국시간)</p>", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; letter-spacing: 3px; margin-bottom: 20px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. 분석 엔진 및 API 함수 (기존 로직 유지)
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

def ask_gpt_90day_forecast(ticker, s_info, recent_news, consensus):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    news_text = "\n".join([f"- {n['title']}" for n in recent_news]) if recent_news else "No recent news."
    
    prompt = f"""
    [ROLE]: Institutional Lead Quant Analyst.
    [TASK]: Forecast {ticker}'s stock performance for the next 90 DAYS.
    [DATA]: {json.dumps(s_info)}, Consensus: {json.dumps(consensus)}, News: {news_text}
    [REPORT STRUCTURE]: In KOREAN Markdown.
    1. **Tetrades AI 90일 상승 예측도**: (예: 78% 상승 전망)
    2. **멀티 팩터 분석 요약**: Fundamentals(30%), Macro(25%), Technical(20%), Consensus(15%), News(10%).
    3. **거시경제 및 정책 동향**: 심층 분석.
    4. **최종 투자 전략 요약**.
    [RULE]: End with EXACTLY one: [VERDICT: STRONG BUY], [VERDICT: BUY], [VERDICT: HOLD], or [VERDICT: SELL].
    """
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": "Professional quantitative AI analyst."}, {"role": "user", "content": prompt}], "temperature": 0.4}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except Exception as e: return f"분석 오류: {e} \n\n[VERDICT: HOLD]"

# ---------------------------------------------------------
# 5. 중앙 집중형 메인 콘텐츠 (탭 구조)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📢 공지사항", "🔍 퀀트 리서치", "💬 투자자 라운지", "🏆 멤버십 & 랭킹"])

# [Tab 1] 공지사항 (Admin 작성 가능)
with tab1:
    st.markdown("<h3 style='text-align: center;'>Tetrades 공식 공지사항</h3>", unsafe_allow_html=True)
    
    # 관리자용 공지 작성 기능 (실제 서비스에선 관리자 로그인 시에만 보이게 처리 가능)
    with st.expander("⚙️ 관리자 전용: 새 공지사항 등록"):
        new_notice = st.text_area("공지 내용을 입력하세요")
        if st.button("공지 등록하기"):
            if new_notice:
                save_announcement(new_notice)
                st.success("공지가 등록되었습니다!")
                st.rerun()
                
    notices_df = load_announcements()
    if not notices_df.empty:
        for index, row in notices_df.iterrows():
            st.info(f"**[{row['date']}]**\n\n{row['content']}")
    else:
        st.write("등록된 공지사항이 없습니다.")

# [Tab 2] 퀀트 리서치 (중앙 배치)
with tab2:
    st.markdown("<h3 style='text-align: center;'>Institutional AI Analysis</h3>", unsafe_allow_html=True)
    col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
    with col_s2:
        ticker_input = st.text_input("", placeholder="종목 심볼 입력 (예: AAPL, PLTR)", label_visibility="collapsed").upper()
        search_clicked = st.button("AI 심층 리포트 생성", type="primary", use_container_width=True)

    if search_clicked and ticker_input:
        st.divider()
        with st.spinner(f"글로벌 금융 데이터 기반 {ticker_input} 분석 중..."):
            s_data = get_api_data("quote", f"symbol={ticker_input}")
            ticker_news = get_api_data("stock-news", f"symbol={ticker_input}&limit=5")
            analyst_data = get_analyst_consensus(ticker_input)
            
            if s_data and len(s_data) > 0:
                s = s_data[0]
                current_price = s.get('price', 0)
                report_text = ask_gpt_90day_forecast(ticker_input, s, ticker_news, analyst_data)
                
                # [DB 저장 로직] 리포트 결과에서 VERDICT 추출 후 DB에 저장
                verdict_status = "HOLD"
                if "[VERDICT:" in report_text:
                    verdict_status = report_text.split("[VERDICT:")[1].split("]")[0].strip()
                save_prediction(ticker_input, current_price, verdict_status)
                
                # 지표 대시보드
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"${current_price:,.2f}", f"{s.get('changesPercentage', 0):.2f}%")
                c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                c3.metric("52주 최고가", f"${s.get('yearHigh', 0):,.2f}")
                c4.metric("PER", s.get('pe', 'N/A'))

                # 리포트 출력
                st.markdown(f"<div class='report-card'>{report_text}</div>", unsafe_allow_html=True)
            else:
                st.error("데이터 로딩 실패. 종목 심볼을 확인해주세요.")

# [Tab 3] 커뮤니티 / [Tab 4] 랭킹 (이전 로직과 동일, 생략 없이 깔끔하게 배치)
with tab3:
    st.markdown("<h3 style='text-align: center;'>글로벌 투자자 라운지</h3>", unsafe_allow_html=True)
    st.write("해당 기능은 프리미엄 멤버십 가입 후 이용 가능합니다.")

with tab4:
    col_rank1, col_rank2 = st.columns([2, 1])
    with col_rank1:
        st.subheader("파트너 애널리스트 랭킹")
        st.markdown("""
        | 순위 | 닉네임 | 파트너 리워드 누적 | 배지 |
        | :--- | :--- | :--- | :--- |
        | 1 | PrivateK | 152,100 원 | [Black] |
        | 2 | TechQuant | 88,200 원 | [Navy] |
        """)
    with col_rank2:
        st.markdown("""
        <div style='background-color: #0F172A; border: 1px solid #1E293B; padding: 25px; border-radius: 8px; text-align: center;'>
            <h3 style='margin-top:0; color:#C8AA6E;'>Tetrades Premium</h3>
            <p style='color: #E2E8F0; font-size: 2.2em; font-weight: 700; margin: 0;'>₩9,900</p>
            <button style='width:100%; padding:14px; margin-top:20px; background-color:transparent; color:#C8AA6E; border:1px solid #C8AA6E;'>멤버십 시작하기</button>
        </div>
        """, unsafe_allow_html=True)
