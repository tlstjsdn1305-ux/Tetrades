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
    .admin-card { background-color: #1E293B; padding: 20px; border-radius: 8px; border: 1px solid #475569; text-align: center; }
    .admin-card h2 { margin: 0; color: #E2E8F0 !important; }
    .admin-card p { margin: 5px 0 0 0; color: #94A3B8; font-size: 0.9rem; }
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
# 3. AI 퀀트 엔진 (상세 로직 유지)
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
    [TASK]: 90-DAY Premium Research Report for {ticker}.
    [WEIGHTS]: 
    1. Fundamentals (30%): Earnings, P/E, Market Cap.
    2. Macro & Policy (25%): Interest rates, sector subsidies.
    3. Technical Momentum (20%): Moving averages, RSI trends.
    4. Analyst Consensus (15%): Institutional buy/sell ratios.
    5. Market Psychology (10%): News sentiment, social hype.
    
    [DATA]: {json.dumps(s)}
    [FORMAT]: KOREAN Markdown. 
    구조: 1.예측승률 2.가중치분석요약 3.핵심정책이슈 4.월가동향 5.최종결론
    리포트 끝에 반드시 [VERDICT: BUY/SELL/HOLD] 포함.
    """
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": "Financial Expert."}, {"role": "user", "content": prompt}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 로딩 실패. [VERDICT: HOLD]"

# ---------------------------------------------------------
# [수정된 핵심 로직] 3.5 세션 강제 동기화 (PKCE 우회 및 에러 진단)
# ---------------------------------------------------------
if "user" not in st.session_state:
    if "code" in st.query_params:
        try:
            auth_code = st.query_params["code"]
            # verifier 없이 코드만으로 세션 교환 (PKCE 오류 해결)
            session_data = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
            
            if session_data.user:
                st.session_state["user"] = session_data.user
                st.session_state["profile"] = get_user_profile(session_data.user)
                st.query_params.clear()
                st.rerun()
        except Exception as e:
            # 진단 모드: 실패 시 에러를 숨기지 않고 표시 (디버깅용)
            st.error(f"⚠️ 로그인 처리 중 오류 발생: {e}")
    else:
        try:
            session = supabase.auth.get_session()
            if session:
                st.session_state["user"] = session.user
                st.session_state["profile"] = get_user_profile(session.user)
        except:
            pass

# ---------------------------------------------------------
# 4. 상단 레이아웃 및 인증 체크 (수동 URL 적용)
# ---------------------------------------------------------
now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p style='text-align:right; color:#64748B; font-size:0.85rem;'>Live Sync: {now_kst} (KST)</p>", unsafe_allow_html=True)

top_col1, top_col2 = st.columns([7, 3])
with top_col2:
    if "user" not in st.session_state:
        # [수정] PKCE를 피하기 위해 수동 URL 생성
        manual_auth_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=https://tetrades.streamlit.app"
        st.link_button("🚀 Google 계정으로 시작하기", manual_auth_url, use_container_width=True)
    else:
        profile = get_user_profile(st.session_state["user"])
        st.write(f"⚜️ {profile['subscription_type'].upper()} | 💰 {profile['points']}원")
        if st.button("Logout"):
            supabase.auth.sign_out()
            del st.session_state["user"]; st.rerun()

st.markdown("<h1 style='letter-spacing:5px; margin-bottom:40px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 메인 탭 구성 (관리자 로직 및 UI 복구)
# ---------------------------------------------------------
is_admin = "user" in st.session_state and st.session_state["user"].email == ADMIN_EMAIL
tab_names = ["📢 NOTICE", "🔍 QUANT RESEARCH", "🏆 RANKING"]
if is_admin: tab_names.append("👑 ADMIN")

tabs = st.tabs(tab_names)

# [Tab 1] 공지사항 (Notice Box 복구)
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

# [Tab 2] 퀀트 리서치 (Metric 및 Teaser 복구)
with tabs[1]:
    st.markdown("<h3 style='margin-bottom:30px;'>Institutional AI Analysis</h3>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("", placeholder="Ticker (e.g. MU, NVDA)", label_visibility="collapsed").upper()
        if st.button("AI 정밀 리포트 생성", type="primary") and ticker:
            s_data = fetch_fmp("quote", f"symbol={ticker}")
            if s_data:
                s = s_data[0]
                # 상세 지표 UI 복구
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
                m2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                m3.metric("52주 최고", f"${s.get('yearHigh')}")
                m4.metric("PER", s.get('pe', 'N/A'))

                if "user" not in st.session_state:
                    st.warning("🔒 리포트 전문은 회원 전용입니다. 로그인 후 9,900원의 가치를 확인하세요.")
                    st.markdown("<div class='report-card teaser-blur'><h4>[PREMIUM REPORT]</h4>본 종목의 90일 예측 승률 및 정책 이슈 분석 결과는 로그인 후 공개됩니다.</div>", unsafe_allow_html=True)
                else:
                    report = generate_ai_report(ticker, s)
                    st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
                    v = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                    save_prediction(ticker, s.get('price'), v)
            else:
                st.error("티커를 다시 확인해주세요.")

# [Tab 3] 랭킹 (Referral 로직 복구)
with tabs[2]:
    if "user" in st.session_state:
        st.success(f"나의 추천 코드: **{profile['referral_code']}** (가입 시 900원 적립)")
    st.subheader("Elite Analyst Ranking")
    ranks = supabase.table('profiles').select("email, points").order('points', desc=True).limit(10).execute()
    if ranks.data:
        st.table(pd.DataFrame(ranks.data))

# [Tab 4] 관리자 전용 (대시보드 UI 및 기능 복구)
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
            u_count = len(all_users.data) if all_users.data else 0
            p_count = len(all_preds.data) if all_preds.data else 0
            
            st.markdown(f"""
            <div class='admin-card'>
                <h2>{u_count}명</h2>
                <p>총 회원 수</p>
            </div>
            <div class='admin-card' style='margin-top:10px;'>
                <h2>{p_count}건</h2>
                <p>누적 AI 분석</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        st.subheader("👥 사용자 상세 현황")
        if all_users.data:
            df_users = pd.DataFrame(all_users.data)
            st.dataframe(df_users[['email', 'subscription_type', 'points', 'referral_code', 'id']])
