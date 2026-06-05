import os
import streamlit as st
import pandas as pd

from utils.dart_api import (
    search_companies, fetch_all_statements, fetch_employees_all
)
from utils.data_proc import build_period_series
from sections import revenue, margin, sga, nwc, cashflow, metrics, stock, peer, disclosures

st.set_page_config(
    page_title="OpenDart 기업 재무 Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0; border-radius: 6px 6px 0 0;
        padding: 5px 14px; font-weight: 500; font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] { background-color: #2E86AB; color: white; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("📊 기업 재무 Dashboard")
    st.markdown("---")

    api_key = os.environ.get("DART_API_KEY", "")
    if not api_key:
        api_key = st.text_input("DART API Key", type="password",
                                 help="https://opendart.fss.or.kr 에서 발급")
        if api_key:
            os.environ["DART_API_KEY"] = api_key
        else:
            st.warning("API Key를 입력하거나 환경변수 DART_API_KEY를 설정해 주세요.")
            st.stop()

    for k, v in [("companies", pd.DataFrame()), ("corp_code", None), ("corp_name", ""),
                  ("corp_cls", "Y"), ("stock_code", ""), ("statements", {}),
                  ("df_cum", pd.DataFrame()), ("df_emp", pd.DataFrame())]:
        if k not in st.session_state:
            st.session_state[k] = v

    st.markdown("### 🔍 기업 검색")
    keyword = st.text_input("기업명", placeholder="삼성전자, LG전자 등")
    if st.button("검색", use_container_width=True):
        with st.spinner("검색 중..."):
            st.session_state.companies = search_companies(keyword)
        st.session_state.corp_code = None

    if not st.session_state.companies.empty:
        df_r = st.session_state.companies
        options = {f"{r['corp_name']} ({r.get('stock_code','비상장')})": r["corp_code"]
                   for _, r in df_r.iterrows()}
        sel = st.selectbox("기업 선택", list(options.keys()))
        if sel:
            corp_code = options[sel]
            if corp_code != st.session_state.corp_code:
                st.session_state.corp_code   = corp_code
                st.session_state.corp_name   = sel.split(" (")[0]
                row = df_r[df_r["corp_code"] == corp_code].iloc[0]
                st.session_state.corp_cls    = row.get("corp_cls", "Y")
                st.session_state.stock_code  = str(row.get("stock_code", "") or "")

    st.markdown("---")
    st.markdown("### ⚙️ 조회 설정")
    cur_yr = pd.Timestamp.now().year
    years = st.multiselect("조회 연도", list(range(cur_yr, cur_yr - 7, -1)),
                            default=list(range(cur_yr, cur_yr - 4, -1)))
    fs_div = st.radio("재무제표 유형", ["CFS (연결)", "OFS (별도)"], index=0)
    fs_code = "CFS" if "CFS" in fs_div else "OFS"

    if st.button("📥 데이터 불러오기", use_container_width=True, type="primary"):
        if not st.session_state.corp_code:
            st.error("기업을 먼저 선택해 주세요.")
        elif not years:
            st.error("조회 연도를 선택해 주세요.")
        else:
            with st.spinner(f"{st.session_state.corp_name} 데이터 로딩 중..."):
                try:
                    stmts  = fetch_all_statements(st.session_state.corp_code, sorted(years), fs_code)
                    df_cum = build_period_series(stmts)
                    df_emp = fetch_employees_all(st.session_state.corp_code, sorted(years))
                    st.session_state.statements = stmts
                    st.session_state.df_cum     = df_cum
                    st.session_state.df_emp     = df_emp
                    if df_cum.empty:
                        st.warning("데이터를 가져오지 못했습니다.")
                    else:
                        st.success(f"✅ {len(stmts)}개 보고서 로드 완료")
                except Exception as e:
                    st.error(f"오류: {e}")

    if not st.session_state.df_cum.empty:
        with st.expander("로드된 기간"):
            st.write(", ".join(f"{y}{p}" for (y, p) in st.session_state.statements.keys()))

    st.markdown("---")
    st.markdown("### 📌 섹션 이동")
    section = st.radio("", [
        "📈 재무 실적",
        "💹 주가 / Consensus",
        "🔍 Peer 비교",
        "📋 공시 정보",
    ], label_visibility="collapsed")

if st.session_state.df_cum.empty:
    st.markdown("""
    ## 📊 OpenDart 기업 재무 Dashboard
    좌측 사이드바에서 기업을 검색하고 **데이터 불러오기**를 클릭하면 대시보드가 활성화됩니다.
    ---
    | 섹션 | 주요 내용 |
    |------|----------|
    | 📈 재무 실적 | Revenue · Margin · SG&A · NWC · 현금흐름 · 지표 |
    | 💹 주가/Consensus | 주가 트렌드 · PER/PBR · Forward Valuation |
    | 🔍 Peer 비교 | 산업군 분류 · 재무정보 Peer 비교 |
    | 📋 공시 정보 | 주요공시 · 수주잔고 · Capacity |
    > DART API Key는 [opendart.fss.or.kr](https://opendart.fss.or.kr) 에서 무료 발급 가능합니다.
    """)
    st.stop()

corp_name  = st.session_state.corp_name
df_cum     = st.session_state.df_cum
statements = st.session_state.statements
df_emp     = st.session_state.df_emp
stock_code = st.session_state.stock_code
corp_cls   = st.session_state.corp_cls
corp_code  = st.session_state.corp_code

st.title(f"📊 {corp_name} 재무 Dashboard")
st.caption(f"재무제표: {fs_div}  |  조회 연도: {', '.join(str(y) for y in sorted(years))}")
st.divider()

if section == "📈 재무 실적":
    tabs = st.tabs(["📈 Revenue","💰 Margin","📋 SG&A","🔄 NWC","💵 현금흐름","📐 각종 지표"])
    with tabs[0]: revenue.render(df_cum)
    with tabs[1]: margin.render(df_cum)
    with tabs[2]: sga.render(df_cum, statements, df_emp)
    with tabs[3]: nwc.render(df_cum)
    with tabs[4]: cashflow.render(df_cum)
    with tabs[5]: metrics.render(df_cum)
elif section == "💹 주가 / Consensus":
    stock.render(stock_code, corp_cls, corp_name)
elif section == "🔍 Peer 비교":
    peer.render(corp_name)
elif section == "📋 공시 정보":
    disclosures.render(corp_code, corp_name)
