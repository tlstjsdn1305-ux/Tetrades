import streamlit as st
from supabase import create_client, Client
import urllib.request, json, ssl
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 보안 설정 및 테마 정의 (Midnight Navy & Champagne Gold)
# ---------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🔑 Streamlit Secrets 설정 오류: {e}")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Gold", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; text-align: center; }
    .stButton > button { background-color: transparent; color: #C8AA6E; font-weight: 600; border-radius: 4px; border: 1px solid #C8AA6E; width: 100%; transition: 0.3s; }
    .stButton > button:hover { background-color: #C8AA6E; color: #0B1320; }
    .stTextInput > div > div > input { background-color: #151E2D; border: 1px solid #2A3B52; color: #E2E8F0; text-align: center; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 40px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    .report-card { background-color: #151E2D; padding: 35px; border-radius: 8px; border: 1px solid #2A3B52; color: #E2E8F0; line-height: 1.8; font-size: 1.05rem; }
    .teaser-blur { filter: blur(8px); pointer-events: none; user-select: none; opacity: 0.4; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DB 및 유저 수익 로직 (Supabase)
# ---------------------------------------------------------
def get_or_create_profile(user):
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data: return res.data[0]
    new_ref_code = str(uuid.uuid4())[:8].upper()
    profile_data = {"id": user.id, "email": user.email, "subscription_type": "free", "points": 0, "referral_code": new_ref_code}
    supabase.table('profiles').insert(profile_data).execute()
    return profile_data

def process_referral(referrer_code):
    res = supabase.table('profiles').select("*").eq('referral_code', referrer_code).execute()
    if res.data:
        referrer = res.data[0]
        supabase.table('profiles').update({"points": referrer['points'] + 900}).eq('id', referrer['id']).execute()
        return True
    return False

def save_prediction(ticker, price, verdict):
    target = (datetime.now() + timedelta(days=90)).date()
    supabase.table('predictions').insert({"ticker": ticker, "price": price, "verdict": verdict, "target_date": str(target)}).execute()

# ---------------------------------------------------------
# 3. 고도화된 90일 예측 엔진 (멀티 팩터 가중치 모델)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_fmp_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

def ask_gpt_deep_analysis(ticker, s, news, consensus):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    # 가중치 로직 및 상세 보고서 구조 주입
    prompt = f"""
    [ROLE]: Lead Institutional Quant Analyst.
    [TASK]: Create a 90-DAY Premium Research Report for {ticker}.
    
    [FACTOR WEIGHTS]:
    1. Fundamentals (30%): Earnings, P/E, Market Cap.
    2. Macro & Policy (25%): Interest rates, sector subsidies, regulations.
    3. Technical Momentum (20%): Moving averages, RSI trends.
    4. Analyst Consensus (15%): Institutional buy/sell ratios.
    5. Market Psychology (10%): News sentiment, social hype.

    [DATA]: Market:{json.dumps(s)}, News:{news}, Analyst:{consensus}

    [REPORT STRUCTURE]: 작성 언어: 한국어 (Markdown)
    # {ticker} 90일 AI 예측 보고서
    ## 1. Tetrades 90일 AI 예측 승률
    - **XX% 상승 확률**
    ## 2. 가중치 분석 요약
    - 기초 분석(30%): [상태/분석내용]
    - 거시경제 및 정책(25%): [상태/분석내용]
    - 기술적 모멘텀(20%): [상태/분석내용]
    - 애널리스트 컨센서스(15%): [상태/분석내용]
    - 뉴스 및 심리(10%): [상태/분석내용]
    ## 3. 핵심 정책 및 이슈 (Macro/Policy)
    ## 4. 월가 애널리스트 동향
    ## 5. 최종 결론 및 전략
    [VERDICT: BUY/SELL/HOLD] 형식으로 끝낼 것.
    """
    
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": "Professional financial analyst."}, {"role": "user", "content": prompt}], "temperature": 0.3}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 로딩 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. [VERDICT: HOLD]"

# ---------------------------------------------------------
# 4. 상단 UI 및 레이아웃
# ---------------------------------------------------------
t_c1, t_c2 = st.columns([8, 2])
with t_c2:
    if "user" not in st.session_state:
        with st.expander("👤 LOGIN / JOIN"):
            mode = st.radio("", ["로그인", "회원가입"], horizontal=True, label_visibility="collapsed")
            e_in = st.text_input("Email")
            p_in = st.text_input("PW", type="password")
            if mode == "회원가입":
                r_in = st.text_input("추천인 코드")
                if st.button("가입"):
                    res = supabase.auth.sign_up({"email": e_in, "password": p_in})
                    if res.user:
                        get_or_create_profile(res.user)
                        if r_in: process_referral(r_in.upper())
                        st.success("인증 메일 발송 완료.")
            else:
                if st.button("접속"):
                    res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                    if res.user:
                        st.session_state["user"] = res.user
                        st.session_state["profile"] = get_or_create_profile(res.user)
                        st.rerun()
    else:
        pr = st.session_state["profile"]
        st.write(f"⚜️ {pr['subscription_type'].upper()} | 💰 {pr['points']}원")
        if st.button("Logout"):
            supabase.auth.sign_out()
            del st.session_state["user"]; st.rerun()

now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p style='text-align:right; color:#64748B; font-size:0.8rem;'>Market Sync: {now_kst} (KST 한국시간)</p>", unsafe_allow_html=True)
st.markdown("<h1 style='letter-spacing:5px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 메인 기능 탭
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 퀀트 리서치", "💬 투자자 라운지", "🏆 멤버십 & 랭킹"])

with tab1:
    st.markdown("<h3 style='margin-bottom:30px;'>Institutional AI Analysis</h3>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("", placeholder="Ticker (e.g. MU, PLTR)", label_visibility="collapsed").upper()
        run_btn = st.button("AI 정밀 리포트 생성", type="primary")

    if run_btn and ticker:
        st.divider()
        with st.spinner("멀티 팩터 가중치 모델 계산 중..."):
            s_data = get_fmp_data("quote", f"symbol={ticker}")
            if s_data:
                s = s_data[0]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
                m2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                m3.metric("52주 최고", f"${s.get('yearHigh')}")
                m4.metric("PER", s.get('pe', 'N/A'))

                # [권한 체크] 리포트 공개 여부
                if "user" not in st.session_state:
                    st.warning("🔒 리포트 전문은 회원 전용입니다. 로그인 시 9,900원의 가치를 확인하세요.")
                    st.markdown("<div class='report-card teaser-blur'><h4>[PREMIUM REPORT]</h4>본 종목의 90일 예측 승률 및 정책 이슈 분석 결과는 로그인 후 공개됩니다.</div>", unsafe_allow_html=True)
                else:
                    report = ask_gpt_deep_analysis(ticker, s, "News Summary", "Buy Rating")
                    st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
                    verdict = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                    save_prediction(ticker, s.get('price'), verdict)
            else:
                st.error("티커를 다시 확인해주세요.")
