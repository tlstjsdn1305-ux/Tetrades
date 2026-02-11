import streamlit as st
from supabase import create_client, Client
import urllib.request, json, ssl
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 보안 설정 및 테마 정의
# ---------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("🔑 Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Premium", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3 { color: #C8AA6E !important; }
    .stButton > button { background-color: transparent; color: #C8AA6E; border: 1px solid #C8AA6E; width: 100%; transition: 0.3s; }
    .stButton > button:hover { background-color: #C8AA6E; color: #0B1320; }
    .report-card { background-color: #151E2D; padding: 30px; border-radius: 8px; border: 1px solid #2A3B52; line-height: 1.8; }
    .teaser-blur { filter: blur(5px); pointer-events: none; user-select: none; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. [NEW] 리워드 및 회원 관리 로직
# ---------------------------------------------------------
def get_or_create_profile(user):
    # 기존 프로필 확인
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data:
        return res.data[0]
    
    # 새 프로필 생성 (회원가입 시 최초 1회)
    new_ref_code = str(uuid.uuid4())[:8].upper()
    profile_data = {
        "id": user.id,
        "email": user.email,
        "subscription_type": "free",
        "points": 0,
        "referral_code": new_ref_code
    }
    supabase.table('profiles').insert(profile_data).execute()
    return profile_data

def process_referral(referrer_code):
    # 추천인 코드를 가진 유저를 찾아 900원 지급
    res = supabase.table('profiles').select("*").eq('referral_code', referrer_code).execute()
    if res.data:
        referrer = res.data[0]
        new_points = referrer['points'] + 900
        supabase.table('profiles').update({"points": new_points}).eq('id', referrer['id']).execute()
        return True
    return False

# ---------------------------------------------------------
# 3. 데이터 및 AI 엔진 (기존 유지)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_api_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

# ---------------------------------------------------------
# 4. 상단 로그인 및 회원가입 UI
# ---------------------------------------------------------
top_c1, top_c2 = st.columns([8, 2])
with top_c2:
    if "user" not in st.session_state:
        with st.expander("👤 LOGIN / JOIN"):
            mode = st.radio("선택", ["로그인", "회원가입"], horizontal=True)
            email = st.text_input("이메일")
            pw = st.text_input("비밀번호", type="password")
            
            if mode == "회원가입":
                ref_input = st.text_input("추천인 코드 (선택)")
                if st.button("가입하기"):
                    res = supabase.auth.sign_up({"email": email, "password": pw})
                    if res.user:
                        new_prof = get_or_create_profile(res.user)
                        if ref_input:
                            if process_referral(ref_input.upper()):
                                st.success("추천인 리워드가 반영되었습니다!")
                        st.success("가입 완료! 이메일 인증 후 로그인해주세요.")
            else:
                if st.button("로그인"):
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                    if res.user:
                        st.session_state["user"] = res.user
                        st.session_state["profile"] = get_or_create_profile(res.user)
                        st.rerun()
    else:
        prof = st.session_state.get("profile", {})
        st.write(f"⚜️ {prof.get('subscription_type', 'FREE').upper()}")
        st.write(f"💰 {prof.get('points', 0)} 원")
        if st.button("Logout"):
            supabase.auth.sign_out()
            del st.session_state["user"]
            st.rerun()

st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>TETRADES GOLD</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 메인 기능 (권한 제어 적용)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 퀀트 리서치", "💬 투자자 라운지", "🏆 랭킹 & 내 정보"])

with tab1:
    st.markdown("<h3 style='text-align: center;'>90-Day Multi-Factor Forecast</h3>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("", placeholder="종목 티커 입력 (예: PLTR, MU)", label_visibility="collapsed").upper()
        run_analysis = st.button("AI 정밀 리포트 생성", type="primary")

    if run_analysis and ticker:
        s_data = get_api_data("quote", f"symbol={ticker}")
        if s_data:
            s = s_data[0]
            st.subheader(f"📊 {ticker} 현재 시장 지표")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
            c2.metric("시가총액", f"${s.get('marketCap', 0):,}")
            c3.metric("52주 최고", f"${s.get('yearHigh')}")
            c4.metric("PER", s.get('pe', 'N/A'))

            st.divider()
            
            # [1번 기능] 로그인 여부에 따른 리포트 제어
            if "user" not in st.session_state:
                st.warning("🔒 심층 분석 리포트는 회원 전용 콘텐츠입니다.")
                st.markdown("""
                <div class='report-card teaser-blur'>
                    <h4>[샘플 리포트]</h4>
                    <p>본 종목의 90일 예측 승률은... (로그인 시 공개)</p>
                    <p>현재 거시경제 정책에 따른 가중치 분석 결과...</p>
                </div>
                """, unsafe_allow_html=True)
                st.info("무료 회원가입 후 즉시 전체 내용을 확인하실 수 있습니다.")
            else:
                st.success("✅ 프리미엄 AI 리포트를 불러왔습니다.")
                # 여기에 실제 GPT 분석 결과(report_text)를 출력
                st.markdown("<div class='report-card'>AI 분석 리포트 내용이 여기에 표시됩니다...</div>", unsafe_allow_html=True)

with tab3:
    if "user" in st.session_state:
        prof = st.session_state["profile"]
        st.subheader("내 파트너 정보")
        st.info(f"나의 추천 코드: **{prof['referral_code']}**")
        st.write("위 코드를 지인에게 공유하세요. 친구 가입 시 900원이 즉시 적립됩니다.")
    
    st.subheader("Elite Analyst Ranking")
    st.write("리워드 수익 TOP 10 랭킹 (준비 중)")
