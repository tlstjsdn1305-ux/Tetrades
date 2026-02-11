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

# 프리미엄 다크 테마 커스텀 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0B1320; color: #E2E8F0; }
    h1, h2, h3, h4 { color: #C8AA6E !important; font-family: 'Helvetica Neue', sans-serif; text-align: center; }
    
    /* 버튼 스타일 (Ghost Button) */
    .stButton > button { 
        background-color: transparent; color: #C8AA6E; font-weight: 600; 
        border-radius: 4px; border: 1px solid #C8AA6E; width: 100%; transition: 0.3s; 
    }
    .stButton > button:hover { background-color: #C8AA6E; color: #0B1320; }
    
    /* 입력창 및 중앙 정렬 */
    .stTextInput > div > div > input { background-color: #151E2D; border: 1px solid #2A3B52; color: #E2E8F0; text-align: center; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 40px; border-bottom: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab"] { color: #64748B; padding-bottom: 10px; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] { color: #C8AA6E !important; border-bottom: 2px solid #C8AA6E !important; }
    
    /* 리포트 카드 및 티저 블러 효과 */
    .report-card { background-color: #151E2D; padding: 35px; border-radius: 8px; border: 1px solid #2A3B52; color: #FFE5B4; line-height: 1.8; font-size: 1.05rem; }
    .teaser-blur { filter: blur(6px); pointer-events: none; user-select: none; opacity: 0.5; }
    
    /* 상단 로그인 및 갱신 시간 */
    .top-info { color: #64748B; font-size: 0.85rem; text-align: right; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DB 및 유저 관리 함수 (Supabase 연동)
# ---------------------------------------------------------
def get_or_create_profile(user):
    res = supabase.table('profiles').select("*").eq('id', user.id).execute()
    if res.data:
        return res.data[0]
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
# 3. 데이터 로직 (FMP & GPT-4o)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_fmp_data(endpoint, params=""):
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except: return None

def ask_gpt_forecast(ticker, s_info, news, consensus):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    prompt = f"""
    [ROLE]: Lead Quant Analyst. Forecast {ticker} for 90 DAYS.
    [WEIGHT]: Fundamental(30%), Macro(25%), Technical(20%), Analyst(15%), News(10%).
    [DATA]: {json.dumps(s_info)}, News: {news}, Consensus: {consensus}
    [FORMAT]: KOREAN Markdown. Include '90일 상승 예측도(%)' and '[VERDICT: BUY/SELL/HOLD]'.
    """
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": "Professional financial forecasting AI."}, {"role": "user", "content": prompt}], "temperature": 0.4}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))['choices'][0]['message']['content']
    except: return "분석 오류 발생. [VERDICT: HOLD]"

# ---------------------------------------------------------
# 4. 상단 UI (로그인 & 티커 테이프)
# ---------------------------------------------------------
t_col1, t_col2 = st.columns([8, 2])
with t_col2:
    if "user" not in st.session_state:
        with st.expander("👤 LOGIN / JOIN"):
            mode = st.radio("", ["로그인", "회원가입"], horizontal=True, label_visibility="collapsed")
            email_in = st.text_input("Email", key="login_email")
            pw_in = st.text_input("PW", type="password", key="login_pw")
            if mode == "회원가입":
                ref_in = st.text_input("추천인 코드 (900원 적립)")
                if st.button("가입 신청"):
                    res = supabase.auth.sign_up({"email": email_in, "password": pw_in})
                    if res.user:
                        get_or_create_profile(res.user)
                        if ref_in: process_referral(ref_in.upper())
                        st.success("인증 메일을 확인해주세요.")
            else:
                if st.button("접속"):
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": pw_in})
                    if res.user:
                        st.session_state["user"] = res.user
                        st.session_state["profile"] = get_or_create_profile(res.user)
                        st.rerun()
    else:
        p = st.session_state["profile"]
        st.write(f"🏛️ {p['subscription_type'].upper()} | 💰 {p['points']}원")
        if st.button("Logout"):
            supabase.auth.sign_out()
            del st.session_state["user"]
            st.rerun()

now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p class='top-info'>Market Sync: {now_kst} (KST 한국시간)</p>", unsafe_allow_html=True)

ticker_tape = '<div style="height:40px;"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"NASDAQ:AAPL","title":"Apple"},{"proName":"NASDAQ:NVDA","title":"NVIDIA"},{"proName":"NASDAQ:MU","title":"Micron"},{"proName":"BITSTAMP:BTCUSD","title":"Bitcoin"}],"colorTheme":"dark","isTransparent":true,"displayMode":"adaptive","locale":"ko"}</script></div>'
components.html(ticker_tape, height=50)

st.markdown("<h1 style='letter-spacing: 5px; margin-top: 20px;'>TETRADES INTELLIGENCE</h1>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 메인 콘텐츠 (중앙 탭 구조)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📢 공지사항", "🔍 퀀트 리서치", "💬 투자자 라운지", "🏆 멤버십 & 랭킹"])

with tab2:
    st.markdown("<h3 style='margin-bottom: 30px;'>Institutional AI Research</h3>", unsafe_allow_html=True)
    c_col1, c_col2, c_col3 = st.columns([1, 2, 1])
    with c_col2:
        ticker_input = st.text_input("", placeholder="종목 심볼 입력 (예: PLTR, MU)", label_visibility="collapsed").upper()
        run_btn = st.button("AI 심층 분석 실행", type="primary")

    if run_btn and ticker_input:
        st.divider()
        with st.spinner(f"90일 멀티 팩터 가중치 모델로 {ticker_input} 분석 중..."):
            s_data = get_fmp_data("quote", f"symbol={ticker_input}")
            if s_data:
                s = s_data[0]
                # 지표 요약
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${s.get('price')}", f"{s.get('changesPercentage')}%")
                m2.metric("시가총액", f"${s.get('marketCap', 0):,}")
                m3.metric("52주 최고", f"${s.get('yearHigh')}")
                m4.metric("PER", s.get('pe', 'N/A'))
                
                # 차트
                h_data = get_fmp_data("historical-price-eod/full", f"symbol={ticker_input}")
                if h_data:
                    df = pd.DataFrame(h_data['historical']).tail(120)
                    st.line_chart(df.set_index('date')['close'])

                # [권한 제어 및 리포트]
                st.subheader("📑 90-Day Multi-Factor Quant Report")
                if "user" not in st.session_state:
                    st.warning("🔒 리포트 전문은 회원 전용입니다. 로그인 후 무료로 확인하세요.")
                    st.markdown("<div class='report-card teaser-blur'><p>AI 90일 상승 예측도: 7X% 상승 전망<br>가중치 분석 요약: Fundamentals(우수), Policy(안정)...<br>본 리포트는 90일간의 거시경제 정책과 월가 컨센서스를...</p></div>", unsafe_allow_html=True)
                else:
                    report = ask_gpt_forecast(ticker_input, s, "News omitted for demo", "Consensus: Buy")
                    st.markdown(f"<div class='report-card'>{report}</div>", unsafe_allow_html=True)
                    # DB 저장
                    verdict = report.split("[VERDICT:")[1].split("]")[0].strip() if "[VERDICT:" in report else "HOLD"
                    save_prediction(ticker_input, s.get('price'), verdict)
            else:
                st.error("데이터 로딩 실패. 심볼을 확인해주세요.")

with tab4:
    r_col1, r_col2 = st.columns([2, 1])
    with r_col1:
        st.subheader("Elite Analyst Ranking")
        st.write("리워드 수익 TOP 10 실시간 랭킹 (Supabase 연동 중)")
    with r_col2:
        st.markdown(f"""
        <div style='background-color:#0F172A; border:1px solid #1E293B; padding:25px; border-radius:8px; text-align:center;'>
            <h3 style='margin:0; color:#C8AA6E; border:none;'>Premium</h3>
            <p style='color:#E2E8F0; font-size:2.2em; font-weight:700; margin:10px 0;'>₩9,900</p>
            <p style='font-size:0.85em; color:#64748B;'>광고 제거 및 무제한 분석<br>친구 추천 시 900원 적립</p>
            <hr style='margin:20px 0;'>
            <p style='font-size:0.9em;'>나의 추천 코드:<br><b style='color:#C8AA6E;'>{st.session_state["profile"]["referral_code"] if "user" in st.session_state else "Login required"}</b></p>
        </div>
        """, unsafe_allow_html=True)
