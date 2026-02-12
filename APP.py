import streamlit as st
from supabase import create_client, Client
import urllib.request, json, ssl
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import time

# ---------------------------------------------------------
# 1. 시스템 보안 및 테마 설정
# ---------------------------------------------------------
ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="Tetrades Gold", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; text-align: center; }
    
    /* 버튼 스타일 */
    .stButton > button { background-color: transparent; color: #C8AA6E; font-weight: 600; border-radius: 4px; border: 1px solid #C8AA6E; width: 100%; transition: 0.3s; height: 48px; }
    .stButton > button:hover { background-color: #C8AA6E !important; color: #0B1320 !important; }
    
    /* 카드 및 박스 스타일 */
    .notice-box { background-color: #151E2D; padding: 25px; border-radius: 8px; border: 1px solid #C8AA6E; margin-bottom: 20px; }
    .report-card { background-color: #151E2D; padding: 35px; border-radius: 8px; border: 1px solid #2A3B52; color: #E2E8F0; line-height: 1.8; font-size: 1.05rem; }
    .teaser-blur { filter: blur(8px); pointer-events: none; user-select: none; opacity: 0.4; }
    
    /* 관리자 카드 스타일 */
    .admin-card { background-color: #1E293B; padding: 20px; border-radius: 8px; border: 1px solid #475569; text-align: center; margin-bottom: 10px; }
    .admin-card h2 { margin: 0; color: #E2E8F0 !important; }
    .admin-card p { margin: 5px 0 0 0; color: #94A3B8; font-size: 0.9rem; }
    
    /* 광고 배너 스타일 (신규) */
    .ad-banner { background: linear-gradient(45deg, #1e3c72, #2a5298); color: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; font-weight: bold; border: 1px dashed #C8AA6E; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 40px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Supabase & API 설정 (캐싱 적용 - 로그인 유지 필수)
# ---------------------------------------------------------
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase 연결 실패: {e}")
        return None

try:
    supabase = init_supabase()
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
    ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]
except Exception as e:
    st.error(f"🔑 Secrets 로딩 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 비즈니스 로직 (닉네임, 온보딩, 예측 저장)
# ---------------------------------------------------------
def get_user_profile(user):
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data: return res.data[0]
    
    # 신규 가입 시 초기 데이터 설정
    new_code = str(uuid.uuid4())[:8].upper()
    profile_data = {
        "id": user.id, 
        "email": user.email, 
        "subscription_type": "free", 
        "points": 0, 
        "referral_code": new_code,
        "is_onboarded": False, # 온보딩 미완료 상태로 시작
        "nickname": user.email.split("@")[0] # 기본 닉네임
    }
    supabase.table('profiles').insert(profile_data).execute()
    return profile_data

def update_profile(user_id, updates):
    supabase.table('profiles').update(updates).eq('id', user_id).execute()
    st.session_state["profile"].update(updates)

def save_prediction(ticker, price, verdict):
    target = (datetime.now() + timedelta(days=90)).date()
    supabase.table('predictions').insert({
        "ticker": ticker, "price": price, "verdict": verdict, "target_date": str(target)
    }).execute()

# ---------------------------------------------------------
# 4. AI 퀀트 엔진 (비용 최적화 적용)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_fmp(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

def generate_ai_report(ticker, s, user_tier="free"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    # [수익화 핵심] 무료=mini(저비용), 유료=gpt4o(고성능)
    ai_model = "gpt-4o" if user_tier == "premium" else "gpt-4o-mini"
    
    prompt = f"""
    [ROLE]: Lead Institutional Quant Analyst.
    [TASK]: 90-DAY Premium Research Report for {ticker}.
    [TIER]: {user_tier.upper()}.
    [WEIGHTS]: 
    1. Fundamentals (30%): Earnings, P/E, Market Cap.
    2. Macro & Policy (25%): Interest rates, sector subsidies.
    3. Technical Momentum (20%): Moving averages, RSI trends.
    4. Analyst Consensus (15%): Institutional buy/sell ratios.
    5. Market Psychology (10%): News sentiment, social hype.
    
    [DATA]: {json.dumps(s)}
    [FORMAT]: KOREAN Markdown. 
    [STRUCTURE]: 1.예측승률 2.가중치분석요약 3.핵심정책이슈 4.월가동향 5.최종결론
    리포트 끝에 반드시 [VERDICT: BUY/SELL/HOLD] 포함.
    """
    
    payload = {"model": ai_model, "messages": [{"role": "system", "content": "Financial Expert."}, {"role": "user", "content": prompt}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 로딩 실패. [VERDICT: HOLD]"

# ---------------------------------------------------------
# 5. 인증 로직 (세션 유지)
# ---------------------------------------------------------
if "code" in st.query_params and "user" not in st.session_state:
    try:
        auth_code = st.query_params["code"]
        res = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
        if res.user:
            st.session_state["user"] = res.user
            st.session_state["profile"] = get_user_profile(res.user)
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        if "code" in st.query_params: st.query_params.clear()

if "user" not in st.session_state:
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state["user"] = session.user
            st.session_state["profile"] = get_user_profile(session.user)
    except: pass

# ---------------------------------------------------------
# 6. 상단 UI 및 온보딩 (가입 절차)
# ---------------------------------------------------------
now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p style='text-align:right; color:#64748B; font-size:0.85rem;'>Live Sync: {now_kst} (KST)</p>", unsafe_allow_html=True)

# [온보딩 모달] 로그인 후 닉네임/추천인 입력 강제
if "user" in st.session_state and not st.session_state["profile"].get("is_onboarded"):
    with st.form("onboarding_form"):
        st.markdown("### 👋 환영합니다! 분석가님.")
        st.info("서비스 이용을 위해 닉네임과 추천인 코드를 설정해주세요.")
        
        new_nick = st.text_input("닉네임 설정", value=st.session_state["profile"].get("email").split("@")[0])
        ref_code = st.text_input("추천인 코드 (선택사항)")
        
        if st.form_submit_button("Tetrades 시작하기"):
            updates = {"nickname": new_nick, "is_onboarded": True}
            if ref_code:
                updates["referred_by"] = ref_code
            
            update_profile(st.session_state["user"].id, updates)
            st.success("설정이 완료되었습니다!")
            time.sleep(1)
            st.rerun()
    st.stop() # 온보딩 전에는 아래 화면 안 보임

# [로그인 버튼 및 마이페이지]
top_col1, top_col2 = st.columns([7, 3])
with top_col2:
    if "user" not in st.session_state:
        auth_resp = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirectTo": "https://tetrades.streamlit.app",
                "queryParams": {"access_type": "offline", "prompt": "consent"}
            }
        })
        st.link_button("🚀 Google 계정으로 시작하기", auth_resp.url, use_container_width=True)
    else:
        # 마이페이지 확장 패널
        p = st.session_state["profile"]
        tier_icon = "👑" if p['subscription_type'] == 'premium' else "🌱"
        tier_text = "PREMIUM" if p['subscription_type'] == 'premium' else "FREE"
        
        with st.expander(f"{tier_icon} {p.get('nickname', 'User')}님 | {tier_text}"):
            st.write(f"📧 {p['email']}")
            st.write(f"🎫 내 추천코드: **{p['referral_code']}**")
            
            new_n = st.text_input("닉네임 변경", value=p.get('nickname'))
            if st.button("정보 수정 저장"):
                update_profile(st.session_state["user"].id, {"nickname": new_n})
                st.success("수정되었습니다.")
                st.rerun()
            
            if st.button("로그아웃"):
                supabase.auth.sign_out()
                del st.session_state["user"]
                st.rerun()

st.markdown("<h1 style='letter-spacing:5px; margin-bottom:40px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. 메인 탭 구성
# ---------------------------------------------------------
is_admin = "user" in st.session_state and st.session_state["user"].email == ADMIN_EMAIL
tab_names = ["📢 NOTICE", "🔍 QUANT RESEARCH", "🏆 RANKING"]
if is_admin: tab_names.append("👑 ADMIN")

tabs = st.tabs(tab_names)

# [Tab 1] 공지사항
with tabs[0]:
    st.markdown("""
    <div class='notice-box'>
        <h4 style='margin-top:0; color:#C8AA6E;'>🛡️ Tetrades 보안 및 운영 정책</h4>
        <p>본 플랫폼은 강력한 보안을 위해 구글 로그인을 사용합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    notices = supabase.table('announcements').select("*").order('created_at', desc=True).execute()
    for n in notices.data:
        st.info(f"**[{n['created_at'][:10]}]**\n\n{n['content']}")

# [Tab 2] 퀀트 리서치 (무제한 광고 모델 적용)
with tabs[1]:
    st.markdown("<h3 style='margin-bottom:30px;'>Institutional AI Analysis</h3>", unsafe_allow_html=True)
    
    # 유저 등급 확인
    user_is_premium = "user" in st.session_state and st.session_state["profile"]["subscription_type"] == "premium"
    
    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("", placeholder="Ticker (e.g. MU, NVDA)", label_visibility="collapsed").upper()
        
        # 버튼 텍스트 차별화
        btn_text = "AI 정밀 리포트 생성 (즉시)" if user_is_premium else "AI 정밀 리포트 생성 (광고 후 무료)"
        
        if st.button(btn_text, type="primary") and ticker:
            s_data = fetch_fmp("quote", f"symbol={ticker}")
            if s_data:
                s = s_data[0]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
                m2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                m3.metric("52주 최고", f"${s.get('yearHigh')}")
                m4.metric("PER", s.get('pe', 'N/A'))

                if "user" not in st.session_state:
                    st.warning("🔒 로그인 후 무료로 리포트를 확인하세요.")
                    st.markdown("<div class='report-card teaser-blur'><h4>[PREMIUM REPORT]</h4>분석 결과 숨김 처리됨...</div>", unsafe_allow_html=True)
                else:
                    # [광고 로직] 무료 유저인 경우 5초 카운트다운 배너 노출
                    if not user_is_premium:
                        ad_place = st.empty()
                        with ad_place.container():
                            st.markdown("""
                            <div class='ad-banner'>
                                <h3>📣 스폰서 광고 시청 중... (5초)</h3>
                                <p>잠시 후 AI 분석 리포트가 생성됩니다.</p>
                                <small>프리미엄 구독 시 광고 없이 즉시 확인 가능</small>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            prog = st.progress(0)
                            for i in range(100):
                                time.sleep(0.05) # 0.05 * 100 = 5초 대기
                                prog.progress(i + 1)
                        ad_place.empty() # 광고 제거
                    
                    # 리포트 생성 (tier 전달)
                    tier = "premium" if user_is_premium else "free"
                    
                    with st.spinner("AI가 데이터를 분석 중입니다..."):
                        report = generate_ai_report(ticker, s, tier)
                        st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
                        
                        # 예측 데이터 저장
                        v = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                        save_prediction(ticker, s.get('price'), v)
            else:
                st.error("티커를 다시 확인해주세요.")

# [Tab 3] 랭킹
with tabs[2]:
    if "user" in st.session_state:
        p = st.session_state["profile"]
        st.success(f"👋 **{p.get('nickname', 'User')}**님 환영합니다! (내 추천코드: {p['referral_code']})")
    
    st.subheader("Elite Analyst Ranking")
    ranks = supabase.table('profiles').select("nickname, email, points, subscription_type").order('points', desc=True).limit(10).execute()
    if ranks.data:
        ranking_data = []
        for r in ranks.data:
            d_name = r.get('nickname') if r.get('nickname') else r['email'].split('@')[0]
            badge = "👑" if r['subscription_type'] == 'premium' else "🌱"
            ranking_data.append({"Rank": badge, "Analyst": d_name, "Points": r['points']})
        st.table(pd.DataFrame(ranking_data))

# [Tab 4] 관리자 전용 (공지 등록/삭제 & 통계 UI 완비)
if is_admin:
    with tabs[3]:
        st.markdown("### 👑 Tetrades 마스터 관리 도구")
        
        adm_c1, adm_c2 = st.columns(2)
        
        with adm_c1:
            st.subheader("📝 공지사항 관리")
            # 등록
            new_msg = st.text_area("새 공지 내용", height=100)
            if st.button("공지 게시"):
                if new_msg:
                    supabase.table('announcements').insert({"content": new_msg}).execute()
                    st.success("게시 완료"); st.rerun()
            
            st.divider()
            # 삭제
            st.subheader("🗑️ 공지사항 삭제")
            current_notices = supabase.table('announcements').select("*").order('created_at', desc=True).execute()
            if current_notices.data:
                notice_list = {f"[{n['created_at'][:10]}] {n['content'][:20]}...": n['id'] for n in current_notices.data}
                target_notice = st.selectbox("삭제할 공지 선택", options=list(notice_list.keys()))
                if st.button("선택한 공지 삭제", type="secondary"):
                    supabase.table('announcements').delete().eq('id', notice_list[target_notice]).execute()
                    st.success("삭제되었습니다."); st.rerun()
        
        with adm_c2:
            st.subheader("📊 플랫폼 지표")
            u_all = supabase.table('profiles').select("*").execute()
            p_all = supabase.table('predictions').select("*").execute()
            u_count = len(u_all.data) if u_all.data else 0
            p_count = len(p_all.data) if p_all.data else 0
            
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
        st.subheader("👥 전체 사용자 상세 데이터")
        if u_all.data:
            st.dataframe(pd.DataFrame(u_all.data))
