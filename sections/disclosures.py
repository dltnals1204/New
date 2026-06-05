import streamlit as st
import pandas as pd
from utils.dart_api import search_disclosures


def render(corp_code: str, corp_name: str):
    t1, t2, t3 = st.tabs(["📋 주요 공시", "📦 수주 잔고", "🏭 Capacity/Utilization"])

    # ── 주요 공시 ────────────────────────────────────────────────────────
    with t1:
        st.subheader(f"{corp_name} 주요 공시")
        col1, col2 = st.columns([2, 1])
        with col1:
            bgn_de = st.text_input("조회 시작일 (YYYYMMDD)", value="20240101", key="disc_bgn")
        with col2:
            pblntf_ty = st.selectbox("공시 유형", ["전체", "A (정기공시)", "B (주요사항)", "C (발행공시)"],
                                      key="disc_ty")
        ty_map = {"전체": None, "A (정기공시)": "A", "B (주요사항)": "B", "C (발행공시)": "C"}

        if st.button("공시 조회", key="disc_btn"):
            with st.spinner("조회 중..."):
                df_disc = search_disclosures(
                    corp_code, bgn_de=bgn_de,
                    pblntf_ty=ty_map[pblntf_ty]
                )
            if df_disc.empty:
                st.info("조회된 공시가 없습니다.")
            else:
                display_cols = ["rcept_dt", "report_nm", "flr_nm", "rm"]
                col_names    = {"rcept_dt": "접수일", "report_nm": "공시명",
                                "flr_nm": "제출인", "rm": "비고"}
                df_show = df_disc[[c for c in display_cols if c in df_disc.columns]].rename(columns=col_names)
                st.dataframe(df_show, use_container_width=True, height=400)
                st.caption(f"총 {len(df_show)}건 조회")

    # ── 수주 잔고 ─────────────────────────────────────────────────────────
    with t2:
        st.subheader("수주 잔고 정보")
        st.info(
            "📌 수주 잔고는 DART '사업의 내용_매출 및 수주상황' 섹션에서 추출됩니다.\n\n"
            "공시 원문 파싱 기능 개발 후 자동화 예정입니다. 현재 수기 입력으로 활용하세요.",
            icon="ℹ️",
        )
        default_orders = pd.DataFrame({
            "기간":        ["", "", "", ""],
            "수주잔고 (억원)": ["", "", "", ""],
            "신규수주 (억원)": ["", "", "", ""],
            "매출 (억원)":   ["", "", "", ""],
        })
        st.data_editor(default_orders, use_container_width=True,
                        num_rows="dynamic", key="orders_input")

    # ── Capacity / Utilization ───────────────────────────────────────────
    with t3:
        st.subheader("Capacity & Utilization")
        st.info(
            "📌 Capacity 및 Utilization 데이터는 DART '사업의 내용_원재료 및 생산설비' 섹션에서 추출됩니다.\n\n"
            "공시 원문 파싱 기능 개발 후 자동화 예정입니다. 현재 수기 입력으로 활용하세요.",
            icon="ℹ️",
        )
        default_cap = pd.DataFrame({
            "기간":                ["", "", "", ""],
            "생산능력 (단위 입력)":    ["", "", "", ""],
            "실제 생산량":           ["", "", "", ""],
            "가동률 (%)":           ["", "", "", ""],
        })
        st.data_editor(default_cap, use_container_width=True,
                        num_rows="dynamic", key="cap_input")
