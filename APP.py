import streamlit as st
from supabase import create_client, Client
import urllib.request, json, ssl
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 시스템 보안 및 테마 설정 (Midnight Navy & Gold)
# ---------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
    ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🔑 Secrets 설정 오류: {e}")
    st.stop()

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Gold", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; text-align: center; }
    .stButton > button { background-color: transparent; color: #C8AA6E; font-weight: 600; border-radius: 4px; border: 1px solid #C8AA6E; width: 100%; transition: 0.3s; height: 48px; }
    .stButton > button:hover { background-color: #C8AA6E !important; color: #0B1320 !important; }
    .notice-box { background-color: #151E2D; padding: 25px; border-radius: 8px; border: 1px solid #C8AA6E; margin-bottom: 20px; }
    .report-card { background-color: #151E2D; padding: 35px; border-radius: 8px; border: 1px solid #2A3B52; color: #E2E8F0; line-height: 1.8; font-size: 1.05rem; }
    .teaser-blur { filter: blur(8px); pointer-events: none; user-select: none; opacity: 0.4; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 40px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 비즈니스 로직 (회원, 리워드, 예측 저장)
# ---------------------------------------------------------
def get_user_profile(user):
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data: return res.data[0]
    
    new_code = str(uuid.uuid4())[:8].upper()
    profile_data = {
        "id": user.id, "email": user.email, 
        "subscription_type": "free", "points": 0, "referral_code": new_code
    }
    supabase.table('profiles').insert(profile_data).execute()
    return profile_data

def save_prediction(ticker, price, verdict):
    target = (datetime.now() + timedelta(days=90)).date()
    supabase.table('predictions').insert({
        "ticker": ticker, "price": price, "verdict": verdict, "target_date": str(target)
    }).execute()

# ---------------------------------------------------------
# 3. AI 퀀트 엔진 (가중치 로직)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_fmp(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

def generate_ai_report(ticker, s):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    prompt = f"""
    [ROLE]: Lead Institutional Quant Analyst.
    [TASK]: 90-DAY Premium Report for {ticker}.
    [WEIGHTS]: 1.Fundamental(30%) 2.Macro(25%) 3.Tech(20%) 4.Consensus(15%) 5.News(10%)
    [DATA]: {json.dumps(s)}
    [FORMAT]: KOREAN Markdown. 리포트 끝에 반드시 [VERDICT: BUY/SELL/HOLD] 포함.
    """
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": "Financial Expert."}, {"role": "user", "content": prompt}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 로딩 실패. [VERDICT: HOLD]"

# ---------------------------------------------------------
# [수정된 핵심 로직] 3.5 세션 강제 동기화 (URL 파라미터 파싱)
# ---------------------------------------------------------
if "user" not in st.session_state:
    # 1. 구글 인증 후 돌아왔을 때 주소창에 'code'가 있는지 낚아챕니다.
    if "code" in st.query_params:
        try:
            auth_code = st.query_params["code"]
            # 2. 낚아챈 코드를 Supabase에 제출하고 진짜 세션을 받아옵니다.
            session_data = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
            
            if session_data.user:
                st.session_state["user"] = session_data.user
                st.session_state["profile"] = get_user_profile(session_data.user)
                
                # 3. 주소창을 깔끔하게 정리하고 화면을 새로고침합니다.
                st.query_params.clear()
                st.rerun()
        except Exception as e:
            st.error(f"구글 인증 연동 오류: {e}")
    else:
        # 코드가 없다면 기존 세션 유지가 되어있는지 일반 확인
        try:
            session = supabase.auth.get_session()
            if session:
                st.session_state["user"] = session.user
                st.session_state["profile"] = get_user_profile(session.user)
        except:
            pass

# ---------------------------------------------------------
# 4. 상단 레이아웃 및 인증 체크 
# ---------------------------------------------------------
now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p style='text-align:right; color:#64748B; font-size:0.85rem;'>Live Sync: {now_kst} (KST)</p>", unsafe_allow_html=True)

top_col1, top_col2 = st.columns([7, 3])
with top_col2:
    if "user" not in st.session_state:
        auth_response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirectTo": "https://tetrades.streamlit.app"}
        })
        st.link_button("🚀 Google 계정으로 시작하기", auth_response.url, use_container_width=True)
    else:
        profile = get_user_profile(st.session_state["user"])
        st.write(f"⚜️ {profile['subscription_type'].upper()} | 💰 {profile['points']}원")
        if st.button("Logout"):
            supabase.auth.sign_out()
            del st.session_state["user"]; st.rerun()

st.markdown("<h1 style='letter-spacing:5px; margin-bottom:40px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 메인 탭 구성 (관리자 로직 포함)
# ---------------------------------------------------------
is_admin = "user" in st.session_state and st.session_state["user"].email == ADMIN_EMAIL
tab_names = ["📢 NOTICE", "🔍 QUANT RESEARCH", "🏆 RANKING"]
if is_admin:
    tab_names.append("👑 ADMIN")

tabs = st.tabs(tab_names)

# [Tab 1] 공지사항
with tabs[0]:
    st.markdown("""
    <div class='notice-box'>
        <h4 style='margin-top:0; color:#C8AA6E;'>🛡️ Tetrades 보안 및 로그인 정책</h4>
        <p>본 플랫폼은 강력한 <b>개인정보 보호</b>를 위해 구글 소셜 로그인만을 지원합니다. 타 계정으로의 이전 및 변경은 불가능합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    notices = supabase.table('announcements').select("*").order('created_at', desc=True).execute()
    for n in notices.data:
        st.info(f"**[{n['created_at'][:10]}]**\n\n{n['content']}")

# [Tab 2] 퀀트 리서치
with tabs[1]:
    st.markdown("<h3 style='margin-bottom:30px;'>Institutional AI Analysis</h3>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("", placeholder="Ticker (e.g. MU, NVDA)", label_visibility="collapsed").upper()
        if st.button("AI 정밀 리포트 생성", type="primary") and ticker:
            s_data = fetch_fmp("quote", f"symbol={ticker}")
            if s_data:
                s = s_data[0]
                st.metric(f"{ticker} Current Price", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
                if "user" not in st.session_state:
                    st.warning("🔒 리포트 전문은 회원 전용입니다. 로그인 후 9,900원의 가치를 확인하세요.")
                    st.markdown("<div class='report-card teaser-blur'>74% 상승 확률 예측... 거시경제 수혜 전망...</div>", unsafe_allow_html=True)
                else:
                    report = generate_ai_report(ticker, s)
                    st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
                    v = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                    save_prediction(ticker, s.get('price'), v)

# [Tab 3] 랭킹 & 리워드
with tabs[2]:
    if "user" in st.session_state:
        st.success(f"나의 추천 코드: **{profile['referral_code']}** (가입 시 900원 적립)")
    st.subheader("Elite Analyst Ranking")
    ranks = supabase.table('profiles').select("email, points").order('points', desc=True).limit(10).execute()
    if ranks.data:
        st.table(pd.DataFrame(ranks.data))

# [Tab 4] 관리자 전용 패널
if is_admin:
    with tabs[3]:
        st.markdown("### 👑 Tetrades 마스터 관리 도구")
        
        col_adm1, col_adm2 = st.columns(2)
        with col_adm1:
            st.subheader("📝 공지사항 즉시 게시")
            admin_msg = st.text_area("내용을 입력하세요 (Markdown 지원)", height=150)
            if st.button("전체 사용자 공지 게시"):
                if admin_msg:
                    supabase.table('announcements').insert({"content": admin_msg}).execute()
                    st.success("공지가 성공적으로 게시되었습니다!"); st.rerun()
        
        with col_adm2:
            st.subheader("📊 플랫폼 요약 지표")
            all_users = supabase.table('profiles').select("*").execute()
            all_preds = supabase.table('predictions').select("*").execute()
            if all_users.data:
                st.write(f"전체 회원 수: **{len(all_users.data)}** 명")
                st.write(f"누적 분석 횟수: **{len(all_preds.data)}** 회")
        
        st.divider()
        st.subheader("👥 사용자 상세 현황")
        if all_users.data:
            df_users = pd.DataFrame(all_users.data)
            st.dataframe(df_users[['email', 'subscription_type', 'points', 'referral_code', 'id']])
