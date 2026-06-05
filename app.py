import os
import streamlit as st
import pandas as pd
from utils.dart_api import search_companies, fetch_all_statements
from utils.data_proc import build_period_series
from sections import revenue, margin, sga, nwc

st.set_page_config(
    page_title="OpenDart 기업 재무 Dashboard",
    page_icon="📊",
    layout="wide",
)

# ── 스타일 ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0;
        border-radius: 6px 6px 0 0;
        padding: 6px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E86AB;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 기업 재무 Dashboard")
    st.markdown("---")

    api_key = os.environ.get("DART_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "DART API Key",
            type="password",
            help="https://opendart.fss.or.kr 에서 발급",
        )
        if api_key:
            os.environ["DART_API_KEY"] = api_key
        else:
            st.warning("API Key를 입력하거나 환경변수 DART_API_KEY를 설정해 주세요.")
            st.stop()

    st.markdown("### 🔍 기업 검색")
    keyword = st.text_input("기업명", placeholder="삼성전자, LG전자 등")
    search_btn = st.button("검색", use_container_width=True)

    if "companies" not in st.session_state:
        st.session_state.companies = pd.DataFrame()
    if "corp_code" not in st.session_state:
        st.session_state.corp_code = None
    if "corp_name" not in st.session_state:
        st.session_state.corp_name = ""
    if "statements" not in st.session_state:
        st.session_state.statements = {}
    if "df_cum" not in st.session_state:
        st.session_state.df_cum = pd.DataFrame()

    if search_btn and keyword:
        with st.spinner("검색 중..."):
            results = search_companies(keyword)
        st.session_state.companies = results
        st.session_state.corp_code = None

    if not st.session_state.companies.empty:
        df_r = st.session_state.companies
        options = {
            f"{row['corp_name']} ({row.get('stock_code','비상장')})": row["corp_code"]
            for _, row in df_r.iterrows()
        }
        selected = st.selectbox("기업 선택", list(options.keys()))
        if selected:
            st.session_state.corp_code = options[selected]
            st.session_state.corp_name = selected.split(" (")[0]

    st.markdown("---")
    st.markdown("### ⚙️ 조회 설정")

    current_year = pd.Timestamp.now().year
    years = st.multiselect(
        "조회 연도",
        list(range(current_year, current_year - 7, -1)),
        default=list(range(current_year, current_year - 4, -1)),
    )

    fs_div = st.radio(
        "재무제표 유형",
        ["CFS (연결)", "OFS (별도)"],
        index=0,
    )
    fs_div_code = "CFS" if "CFS" in fs_div else "OFS"

    load_btn = st.button("📥 데이터 불러오기", use_container_width=True, type="primary")

    if load_btn:
        if not st.session_state.corp_code:
            st.error("기업을 먼저 선택해 주세요.")
        elif not years:
            st.error("조회 연도를 선택해 주세요.")
        else:
            with st.spinner(f"{st.session_state.corp_name} 재무 데이터 로딩 중..."):
                try:
                    stmts = fetch_all_statements(
                        st.session_state.corp_code,
                        sorted(years),
                        fs_div_code,
                    )
                    df_cum = build_period_series(stmts)
                    st.session_state.statements = stmts
                    st.session_state.df_cum = df_cum
                    if df_cum.empty:
                        st.warning("데이터를 가져오지 못했습니다. 연도/유형을 확인해 주세요.")
                    else:
                        st.success(f"✅ {len(stmts)}개 보고서 로드 완료")
                except Exception as e:
                    st.error(f"데이터 로드 오류: {e}")

    if not st.session_state.df_cum.empty:
        with st.expander("로드된 기간"):
            loaded = [f"{y} {p}" for (y, p) in st.session_state.statements.keys()]
            st.write(", ".join(loaded))

# ── 메인 영역 ─────────────────────────────────────────────────────────────
if st.session_state.df_cum.empty:
    st.markdown("""
    ## OpenDart 기업 재무 Dashboard

    좌측 사이드바에서 기업을 검색하고 데이터를 불러오면 아래 섹션이 활성화됩니다.

    | 섹션 | 내용 |
    |------|------|
    | 📈 Revenue | 매출액 분기/연도별, 성장률 |
    | 💰 Margin | 매출총이익, 영업이익, EBITDA 마진 |
    | 📋 SG&A | 판관비 수준 및 세부 항목 |
    | 🔄 NWC | DSO / DIO / DPO / CCC |

    > **DART API Key**는 [OpenDart](https://opendart.fss.or.kr)에서 무료 발급 가능합니다.
    """)
    st.stop()

corp_name = st.session_state.corp_name
df_cum = st.session_state.df_cum
statements = st.session_state.statements

st.title(f"📊 {corp_name} 재무 Dashboard")
st.caption(f"재무제표 유형: {fs_div} | 조회 연도: {', '.join(str(y) for y in sorted(years))}")
st.markdown("---")

tab_rev, tab_margin, tab_sga, tab_nwc = st.tabs([
    "📈 Revenue",
    "💰 Margin",
    "📋 SG&A",
    "🔄 NWC",
])

with tab_rev:
    revenue.render(df_cum)

with tab_margin:
    margin.render(df_cum)

with tab_sga:
    sga.render(df_cum, statements)

with tab_nwc:
    nwc.render(df_cum)
