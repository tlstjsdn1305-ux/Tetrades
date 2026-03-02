import streamlit as st
from supabase import create_client, Client
import urllib.request, json, ssl
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import time

ssl_context = ssl._create_unverified_context()
st.set_page_config(page_title="TETRADES", page_icon="▲", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&family=Bebas+Neue&display=swap');

/* ─── RESET & BASE ─── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg-base:      #080C10;
    --bg-surface:   #0D1117;
    --bg-elevated:  #111820;
    --bg-card:      #141C24;
    --border:       #1E2A38;
    --border-light: #243040;
    --gold:         #C9A84C;
    --gold-dim:     #8A6E2F;
    --gold-glow:    rgba(201,168,76,0.15);
    --green:        #00C896;
    --green-dim:    rgba(0,200,150,0.1);
    --red:          #FF4466;
    --red-dim:      rgba(255,68,102,0.1);
    --text-primary: #E8EDF2;
    --text-secondary: #6B8299;
    --text-dim:     #3D5166;
    --font-mono:    'IBM Plex Mono', monospace;
    --font-sans:    'IBM Plex Sans', sans-serif;
    --font-display: 'Bebas Neue', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-base) !important;
    font-family: var(--font-sans);
    color: var(--text-primary);
}

[data-testid="stAppViewContainer"] {
    background-image: 
        linear-gradient(rgba(201,168,76,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(201,168,76,0.02) 1px, transparent 1px);
    background-size: 40px 40px;
}

[data-testid="stHeader"],
[data-testid="stToolbar"] { display: none !important; }

/* ─── SCROLLBAR ─── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--gold-dim); border-radius: 2px; }

/* ─── TOP STATUS BAR ─── */
.status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-dim);
    letter-spacing: 0.08em;
}
.status-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 6px;
    box-shadow: 0 0 8px var(--green);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ─── WORDMARK ─── */
.wordmark {
    font-family: var(--font-display);
    font-size: 3.2rem;
    letter-spacing: 0.25em;
    color: var(--text-primary);
    line-height: 1;
    display: flex;
    align-items: baseline;
    gap: 16px;
}
.wordmark-accent {
    color: var(--gold);
    font-size: 0.75rem;
    font-family: var(--font-mono);
    letter-spacing: 0.2em;
    font-weight: 400;
    opacity: 0.8;
    align-self: center;
}
.wordmark-sub {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    margin-top: 4px;
}

/* ─── TICKER TAPE ─── */
.ticker-tape {
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    padding: 8px 0;
    overflow: hidden;
    margin: 20px 0;
    position: relative;
}
.ticker-tape::before, .ticker-tape::after {
    content: '';
    position: absolute;
    top: 0; bottom: 0;
    width: 60px;
    z-index: 2;
}
.ticker-tape::before { left: 0; background: linear-gradient(90deg, var(--bg-base), transparent); }
.ticker-tape::after  { right: 0; background: linear-gradient(-90deg, var(--bg-base), transparent); }
.ticker-scroll {
    display: flex;
    gap: 48px;
    animation: scroll-left 30s linear infinite;
    width: max-content;
    font-family: var(--font-mono);
    font-size: 0.72rem;
}
@keyframes scroll-left {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
}
.ticker-item { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
.ticker-sym  { color: var(--gold); font-weight: 600; letter-spacing: 0.05em; }
.ticker-price { color: var(--text-primary); }
.ticker-up   { color: var(--green); }
.ticker-dn   { color: var(--red); }

/* ─── SECTION HEADERS ─── */
.section-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: var(--gold);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
}

/* ─── METRIC CARDS ─── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 24px;
}
.metric-cell {
    background: var(--bg-card);
    padding: 20px 24px;
    position: relative;
}
.metric-cell::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--gold);
    opacity: 0;
    transition: opacity 0.2s;
}
.metric-cell:hover::before { opacity: 1; }
.metric-label {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 8px;
}
.metric-value {
    font-family: var(--font-mono);
    font-size: 1.4rem;
    font-weight: 500;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}
.metric-change-up { color: var(--green); font-size: 0.75rem; font-family: var(--font-mono); }
.metric-change-dn { color: var(--red);   font-size: 0.75rem; font-family: var(--font-mono); }

/* ─── REPORT CONTAINER ─── */
.report-wrapper {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
}
.report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 24px;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-secondary);
    letter-spacing: 0.1em;
}
.report-header-title { color: var(--gold); font-weight: 600; }
.report-body {
    padding: 28px 32px;
    font-size: 0.92rem;
    line-height: 1.9;
    color: var(--text-primary);
}
.report-body h1, .report-body h2, .report-body h3, .report-body h4 {
    font-family: var(--font-mono) !important;
    color: var(--gold) !important;
    letter-spacing: 0.05em;
    text-align: left !important;
    margin: 20px 0 10px;
}
.report-body strong { color: var(--text-primary); }
.report-body p { color: var(--text-secondary); margin-bottom: 12px; }
.report-footer {
    padding: 12px 24px;
    background: var(--bg-elevated);
    border-top: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-dim);
    letter-spacing: 0.1em;
}

/* ─── VERDICT BADGE ─── */
.verdict-buy  { display:inline-flex; align-items:center; gap:8px; background:var(--green-dim); border:1px solid var(--green); color:var(--green); font-family:var(--font-mono); font-size:0.75rem; padding:6px 16px; letter-spacing:0.15em; font-weight:600; border-radius:2px; }
.verdict-sell { display:inline-flex; align-items:center; gap:8px; background:var(--red-dim);   border:1px solid var(--red);   color:var(--red);   font-family:var(--font-mono); font-size:0.75rem; padding:6px 16px; letter-spacing:0.15em; font-weight:600; border-radius:2px; }
.verdict-hold { display:inline-flex; align-items:center; gap:8px; background:rgba(201,168,76,0.1); border:1px solid var(--gold); color:var(--gold); font-family:var(--font-mono); font-size:0.75rem; padding:6px 16px; letter-spacing:0.15em; font-weight:600; border-radius:2px; }

/* ─── NOTICE CARDS ─── */
.notice-item {
    border-left: 2px solid var(--gold);
    padding: 14px 20px;
    background: var(--bg-card);
    margin-bottom: 8px;
    border-radius: 0 4px 4px 0;
    font-size: 0.88rem;
    color: var(--text-secondary);
}
.notice-date {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}

/* ─── RANKING TABLE ─── */
.rank-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 0.8rem;
}
.rank-table thead tr {
    border-bottom: 1px solid var(--border);
}
.rank-table thead th {
    padding: 10px 16px;
    text-align: left;
    color: var(--text-dim);
    font-size: 0.62rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 400;
}
.rank-table tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
}
.rank-table tbody tr:hover { background: var(--bg-elevated); }
.rank-table tbody td { padding: 12px 16px; color: var(--text-secondary); }
.rank-table tbody td:first-child { color: var(--text-dim); font-size: 0.7rem; }
.rank-table tbody td.analyst { color: var(--text-primary); }
.rank-table tbody td.points { color: var(--gold); }
.rank-1 td.analyst { color: var(--gold) !important; }

/* ─── INPUT OVERRIDE ─── */
[data-testid="stTextInput"] input {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
    padding: 10px 14px !important;
    letter-spacing: 0.05em;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 2px var(--gold-glow) !important;
}
[data-testid="stTextInput"] label {
    font-family: var(--font-mono) !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em !important;
    color: var(--text-dim) !important;
    text-transform: uppercase !important;
}

/* ─── BUTTON OVERRIDE ─── */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--gold) !important;
    color: var(--gold) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 10px 24px !important;
    border-radius: 2px !important;
    transition: all 0.2s !important;
    height: auto !important;
}
.stButton > button:hover {
    background: var(--gold) !important;
    color: var(--bg-base) !important;
    box-shadow: 0 0 20px var(--gold-glow) !important;
}
.stButton > button[kind="primary"] {
    background: var(--gold) !important;
    color: var(--bg-base) !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 24px rgba(201,168,76,0.4) !important;
}

/* ─── LINK BUTTON ─── */
[data-testid="stLinkButton"] a {
    background: var(--gold) !important;
    color: var(--bg-base) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    font-weight: 600 !important;
}

/* ─── TABS ─── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-dim) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 12px 24px !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--gold) !important;
    border-bottom-color: var(--gold) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: var(--text-secondary) !important;
    background: var(--bg-elevated) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 28px !important;
}

/* ─── EXPANDER ─── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    color: var(--text-secondary) !important;
    letter-spacing: 0.08em !important;
}

/* ─── AD BANNER ─── */
.ad-countdown {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold-dim);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-dim);
    margin: 16px 0;
    letter-spacing: 0.05em;
}
.ad-countdown-num {
    font-size: 1.4rem;
    color: var(--gold-dim);
    font-weight: 600;
}

/* ─── TEASER BLUR ─── */
.teaser-blur {
    filter: blur(6px);
    pointer-events: none;
    user-select: none;
    opacity: 0.3;
}

/* ─── ADMIN STATS ─── */
.stat-block {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: 2px solid var(--gold);
    padding: 24px;
    border-radius: 4px;
    text-align: center;
    margin-bottom: 12px;
}
.stat-block-num {
    font-family: var(--font-display);
    font-size: 2.8rem;
    color: var(--text-primary);
    letter-spacing: 0.05em;
    line-height: 1;
}
.stat-block-label {
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--text-dim);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 6px;
}

/* ─── DISCLAIMER ─── */
.disclaimer {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-dim);
    letter-spacing: 0.05em;
    line-height: 1.6;
    padding: 12px 0;
    border-top: 1px solid var(--border);
    margin-top: 40px;
}

/* ─── ONBOARDING MODAL ─── */
.onboard-wrap {
    max-width: 480px;
    margin: 80px auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: 2px solid var(--gold);
    padding: 40px;
    border-radius: 4px;
}

/* ─── PROGRESS BAR ─── */
[data-testid="stProgress"] > div > div {
    background: var(--gold) !important;
}
[data-testid="stProgress"] > div {
    background: var(--bg-elevated) !important;
    border-radius: 0 !important;
}

/* ─── SPINNER ─── */
[data-testid="stSpinner"] { color: var(--gold) !important; }

/* ─── DATAFRAME ─── */
[data-testid="stDataFrame"] {
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
}

/* ─── DIVIDER ─── */
hr { border-color: var(--border) !important; margin: 24px 0 !important; }

/* ─── SUCCESS / ERROR / INFO ─── */
[data-testid="stAlert"] {
    background: var(--bg-elevated) !important;
    border-radius: 2px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
}

/* ─── HIDE STREAMLIT BRANDING ─── */
#MainMenu, footer { visibility: hidden; }

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Supabase & API 설정
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
    FMP_API_KEY    = st.secrets["FMP_API_KEY"]
    ADMIN_EMAIL    = st.secrets["ADMIN_EMAIL"]
except Exception as e:
    st.error(f"🔑 Secrets 로딩 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 비즈니스 로직
# ---------------------------------------------------------
def get_user_profile(user):
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data: return res.data[0]
    new_code = str(uuid.uuid4())[:8].upper()
    profile_data = {
        "id": user.id, "email": user.email, "subscription_type": "free",
        "points": 0, "referral_code": new_code, "is_onboarded": False,
        "nickname": user.email.split("@")[0]
    }
    supabase.table('profiles').insert(profile_data).execute()
    return profile_data

def update_profile(user_id, updates):
    supabase.table('profiles').update(updates).eq('id', user_id).execute()
    st.session_state["profile"].update(updates)

def save_prediction(user_id, ticker, price, verdict):
    target = (datetime.now() + timedelta(days=90)).date()
    supabase.table('predictions').insert({
        "user_id": user_id, "ticker": ticker, "price": price,
        "verdict": verdict, "target_date": str(target)
    }).execute()

# ---------------------------------------------------------
# 4. AI 퀀트 엔진
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_fmp(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except: return None

def generate_ai_report(ticker, s, user_tier="free"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
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
        with urllib.request.urlopen(req, context=ssl_context) as r:
            return json.loads(r.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 로딩 실패. [VERDICT: HOLD]"

# ---------------------------------------------------------
# 5. 인증 로직
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
    except:
        if "code" in st.query_params: st.query_params.clear()

if "user" not in st.session_state:
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state["user"] = session.user
            st.session_state["profile"] = get_user_profile(session.user)
    except: pass

# ---------------------------------------------------------
# 6. 온보딩
# ---------------------------------------------------------
if "user" in st.session_state and not st.session_state["profile"].get("is_onboarded"):
    st.markdown("<div class='onboard-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>ANALYST ONBOARDING</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-family:var(--font-display);font-size:1.8rem;letter-spacing:0.1em;color:#E8EDF2;'>WELCOME TO TETRADES</h3>", unsafe_allow_html=True)
    with st.form("onboarding_form"):
        new_nick = st.text_input("ANALYST HANDLE", value=st.session_state["profile"].get("email").split("@")[0])
        ref_code = st.text_input("REFERRAL CODE (OPTIONAL)")
        if st.form_submit_button("ACTIVATE ACCOUNT", type="primary"):
            updates = {"nickname": new_nick, "is_onboarded": True}
            if ref_code: updates["referred_by"] = ref_code
            update_profile(st.session_state["user"].id, updates)
            st.success("ACCESS GRANTED")
            time.sleep(1)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------
# 7. 상단 레이아웃
# ---------------------------------------------------------
now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")

st.markdown(f"""
<div class='status-bar'>
    <span><span class='status-dot'></span>MARKET DATA LIVE</span>
    <span>KST {now_kst}</span>
    <span>TETRADES INTELLIGENCE PLATFORM v2.0</span>
</div>
""", unsafe_allow_html=True)

# 헤더 + 로그인 버튼
hcol1, hcol2 = st.columns([6, 4])
with hcol1:
    st.markdown("""
    <div class='wordmark'>
        TETRADES
        <span class='wordmark-accent'>▲ INTELLIGENCE</span>
    </div>
    <div class='wordmark-sub'>INSTITUTIONAL GRADE QUANT RESEARCH PLATFORM</div>
    """, unsafe_allow_html=True)

with hcol2:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if "user" not in st.session_state:
        auth_resp = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirectTo": "https://tetrades.streamlit.app",
                "queryParams": {"access_type": "offline", "prompt": "consent"}
            }
        })
        st.link_button("→ SIGN IN WITH GOOGLE", auth_resp.url, use_container_width=True)
    else:
        p = st.session_state["profile"]
        tier_text = "PREMIUM" if p['subscription_type'] == 'premium' else "FREE TIER"
        with st.expander(f"▲ {p.get('nickname', 'ANALYST').upper()}  ·  {tier_text}"):
            st.markdown(f"<span style='font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);'>{p['email']}</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='font-family:var(--font-mono);font-size:0.7rem;color:var(--gold);'>REFERRAL: {p['referral_code']}</span>", unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            new_n = st.text_input("UPDATE HANDLE", value=p.get('nickname'))
            if st.button("SAVE CHANGES"):
                update_profile(st.session_state["user"].id, {"nickname": new_n})
                st.success("UPDATED")
                st.rerun()
            if st.button("SIGN OUT"):
                supabase.auth.sign_out()
                del st.session_state["user"]
                st.rerun()

# 티커 테이프
tickers = [
    ("SPY","597.42","+0.31%","up"), ("NVDA","875.20","+1.24%","up"),
    ("AAPL","228.50","-0.18%","dn"), ("TSLA","182.30","+2.10%","up"),
    ("MSFT","415.80","+0.55%","up"), ("AMZN","196.40","-0.44%","dn"),
    ("META","578.90","+0.89%","up"), ("GOOGL","193.20","+0.22%","up"),
    ("MU","98.40","-1.32%","dn"),   ("AMD","168.70","+1.88%","up"),
]
tape_items = "".join([
    f"<span class='ticker-item'><span class='ticker-sym'>{s}</span><span class='ticker-price'>{p}</span><span class='ticker-{d}'>{c}</span></span>"
    for s,p,c,d in tickers
] * 2)
st.markdown(f"<div class='ticker-tape'><div class='ticker-scroll'>{tape_items}</div></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. 탭 구성
# ---------------------------------------------------------
is_admin = "user" in st.session_state and st.session_state["user"].email == ADMIN_EMAIL
tab_names = ["NOTICE", "QUANT RESEARCH", "ANALYST RANKING"]
if is_admin: tab_names.append("SYSTEM ADMIN")
tabs = st.tabs(tab_names)

# ── Tab 1: NOTICE ──
with tabs[0]:
    st.markdown("<div class='section-label'>PLATFORM ANNOUNCEMENTS</div>", unsafe_allow_html=True)
    notices = supabase.table('announcements').select("*").order('created_at', desc=True).execute()
    if notices.data:
        for n in notices.data:
            st.markdown(f"""
            <div class='notice-item'>
                <div class='notice-date'>{n['created_at'][:10]} · TETRADES OFFICIAL</div>
                {n['content']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='notice-item'><div class='notice-date'>SYSTEM</div>공지사항이 없습니다.</div>", unsafe_allow_html=True)

# ── Tab 2: QUANT RESEARCH ──
with tabs[1]:
    st.markdown("<div class='section-label'>AI QUANT ANALYSIS ENGINE</div>", unsafe_allow_html=True)
    user_is_premium = "user" in st.session_state and st.session_state["profile"]["subscription_type"] == "premium"

    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc2:
        ticker = st.text_input("TICKER SYMBOL", placeholder="MU  ·  NVDA  ·  AAPL").upper()
        btn_text = "GENERATE REPORT  →" if user_is_premium else "GENERATE REPORT (AD-SUPPORTED)  →"
        run = st.button(btn_text, type="primary", use_container_width=True)

    if run and ticker:
        s_data = fetch_fmp("quote", f"symbol={ticker}")
        if s_data:
            s = s_data[0]
            chg = s.get('changesPercentage', 0)
            chg_class = "metric-change-up" if chg >= 0 else "metric-change-dn"
            chg_sign  = "▲" if chg >= 0 else "▼"

            st.markdown(f"""
            <div class='metric-grid'>
                <div class='metric-cell'>
                    <div class='metric-label'>CURRENT PRICE</div>
                    <div class='metric-value'>${s.get('price', 'N/A')}</div>
                    <div class='{chg_class}'>{chg_sign} {abs(chg):.2f}%</div>
                </div>
                <div class='metric-cell'>
                    <div class='metric-label'>MARKET CAP</div>
                    <div class='metric-value'>${s.get('marketCap', 0):,.0f}</div>
                </div>
                <div class='metric-cell'>
                    <div class='metric-label'>52W HIGH</div>
                    <div class='metric-value'>${s.get('yearHigh', 'N/A')}</div>
                </div>
                <div class='metric-cell'>
                    <div class='metric-label'>P/E RATIO</div>
                    <div class='metric-value'>{s.get('pe', 'N/A')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if "user" not in st.session_state:
                st.warning("로그인 후 무료로 리포트를 확인하세요.")
                st.markdown("<div class='report-wrapper'><div class='report-body teaser-blur'><h3>TETRADES QUANT REPORT</h3><p>분석 결과는 로그인 후 확인 가능합니다...</p></div></div>", unsafe_allow_html=True)
            else:
                if not user_is_premium:
                    ad_place = st.empty()
                    with ad_place.container():
                        prog_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.05)
                            prog_bar.progress(i + 1)
                            if i % 20 == 0:
                                remaining = 5 - (i // 20)
                    ad_place.empty()

                tier = "premium" if user_is_premium else "free"
                with st.spinner("ANALYZING MARKET DATA..."):
                    report = generate_ai_report(ticker, s, tier)

                v = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                v_class = {"BUY": "verdict-buy", "SELL": "verdict-sell"}.get(v, "verdict-hold")
                v_icon  = {"BUY": "▲", "SELL": "▼"}.get(v, "—")

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.markdown(f"""
                <div class='report-wrapper'>
                    <div class='report-header'>
                        <span class='report-header-title'>TETRADES QUANT REPORT · {ticker}</span>
                        <span>{now_str} KST · {tier.upper()} TIER</span>
                    </div>
                    <div class='report-body'>{report}</div>
                    <div class='report-footer'>
                        <span class='{v_class}'>{v_icon} {v}</span>
                        &nbsp;&nbsp;
                        ⚠ 본 리포트는 AI 생성 참고용 정보이며 투자 권유가 아닙니다. 투자 결과에 대한 책임은 투자자 본인에게 있습니다.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                uid = st.session_state["user"].id
                save_prediction(uid, ticker, s.get('price'), v)
                pts = st.session_state["profile"]["points"]
                update_profile(uid, {"points": pts + 10})
        else:
            st.error(f"티커 '{ticker}'를 찾을 수 없습니다.")

# ── Tab 3: RANKING ──
with tabs[2]:
    st.markdown("<div class='section-label'>ELITE ANALYST LEADERBOARD</div>", unsafe_allow_html=True)
    if "user" in st.session_state:
        p = st.session_state["profile"]
        st.markdown(f"<span style='font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);'>SIGNED IN AS </span><span style='font-family:var(--font-mono);font-size:0.72rem;color:var(--gold);'>{p.get('nickname','').upper()}</span><span style='font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);'> · REFERRAL: {p['referral_code']} · POINTS: {p['points']}</span>", unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    ranks = supabase.table('profiles').select("nickname,email,points,subscription_type").order('points', desc=True).limit(10).execute()
    if ranks.data:
        rows = ""
        for i, r in enumerate(ranks.data):
            name   = r.get('nickname') or r['email'].split('@')[0]
            badge  = "◆" if r['subscription_type'] == 'premium' else "·"
            rank_class = "rank-1" if i == 0 else ""
            rows += f"<tr class='{rank_class}'><td>#{i+1}</td><td class='analyst'>{badge} {name.upper()}</td><td class='points'>{r['points']:,} PTS</td></tr>"

        st.markdown(f"""
        <table class='rank-table'>
            <thead><tr><th>RANK</th><th>ANALYST</th><th>SCORE</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

# ── Tab 4: ADMIN ──
if is_admin:
    with tabs[3]:
        st.markdown("<div class='section-label'>SYSTEM ADMINISTRATION</div>", unsafe_allow_html=True)
        adm1, adm2 = st.columns(2)

        with adm1:
            st.markdown("<div class='section-label'>NOTICE MANAGEMENT</div>", unsafe_allow_html=True)
            new_msg = st.text_area("COMPOSE ANNOUNCEMENT", height=100)
            if st.button("PUBLISH", type="primary"):
                if new_msg:
                    supabase.table('announcements').insert({"content": new_msg}).execute()
                    st.success("PUBLISHED"); st.rerun()
            st.divider()
            current_notices = supabase.table('announcements').select("*").order('created_at', desc=True).execute()
            if current_notices.data:
                notice_list = {f"[{n['created_at'][:10]}] {n['content'][:30]}...": n['id'] for n in current_notices.data}
                target = st.selectbox("SELECT TO DELETE", options=list(notice_list.keys()))
                if st.button("DELETE SELECTED"):
                    supabase.table('announcements').delete().eq('id', notice_list[target]).execute()
                    st.success("DELETED"); st.rerun()

        with adm2:
            st.markdown("<div class='section-label'>PLATFORM METRICS</div>", unsafe_allow_html=True)
            u_all = supabase.table('profiles').select("*").execute()
            p_all = supabase.table('predictions').select("*").execute()
            u_count = len(u_all.data) if u_all.data else 0
            p_count = len(p_all.data) if p_all.data else 0
            st.markdown(f"""
            <div class='stat-block'>
                <div class='stat-block-num'>{u_count:,}</div>
                <div class='stat-block-label'>REGISTERED ANALYSTS</div>
            </div>
            <div class='stat-block'>
                <div class='stat-block-num'>{p_count:,}</div>
                <div class='stat-block-label'>AI REPORTS GENERATED</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("<div class='section-label'>USER DATABASE</div>", unsafe_allow_html=True)
        if u_all.data:
            st.dataframe(pd.DataFrame(u_all.data), use_container_width=True)

# ── FOOTER ──
st.markdown("""
<div class='disclaimer'>
    © 2025 TETRADES INTELLIGENCE · ALL RIGHTS RESERVED<br>
    본 플랫폼의 모든 분석 결과는 AI가 생성한 참고용 정보입니다. 투자 권유 또는 금융 자문이 아니며, 
    투자 결과에 대한 모든 책임은 투자자 본인에게 있습니다. 과거 성과가 미래 수익을 보장하지 않습니다.
</div>
""", unsafe_allow_html=True)
