import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def render(corp_name: str):
    st.markdown("""
    ### Peer 비교 섹션 구성

    | 단계 | 내용 | 상태 |
    |------|------|------|
    | 1️⃣ 산업군 라벨링 | DART '사업의 내용' 기반 1차 분류 → 리서치 기반 2차 정교화 | 🔧 개발 중 |
    | 2️⃣ Peer 기업 선택 | 동일 산업군 내 국내외 유사기업 선택 | 🔧 개발 중 |
    | 3️⃣ 재무정보 비교 | 매출총이익률, 영업이익률, NWC 회전기일 등 평균 비교 | 🔧 개발 중 |
    """)

    st.divider()

    # ── Peer 수기 입력 섹션 ──────────────────────────────────────────────
    st.subheader("📝 Peer 기업 수기 입력 (임시)")
    st.caption("자동 수집 전 수기로 비교 데이터를 입력해 빠르게 비교할 수 있습니다.")

    default_peers = pd.DataFrame({
        "기업명":      [corp_name, "", "", ""],
        "매출액 (억원)": ["", "", "", ""],
        "영업이익률 (%)": ["", "", "", ""],
        "매출총이익률 (%)": ["", "", "", ""],
        "DSO (일)":   ["", "", "", ""],
        "DIO (일)":   ["", "", "", ""],
        "DPO (일)":   ["", "", "", ""],
    })

    edited = st.data_editor(default_peers, use_container_width=True,
                             num_rows="dynamic", key="peer_input")

    if st.button("📊 비교 차트 생성", key="peer_chart_btn"):
        try:
            df_plot = edited.copy()
            for col in ["매출총이익률 (%)", "영업이익률 (%)"]:
                df_plot[col] = pd.to_numeric(df_plot[col].astype(str).str.replace(",",""), errors="coerce")
            df_plot = df_plot[df_plot["기업명"].str.strip() != ""].dropna(subset=["기업명"])

            if df_plot.empty or df_plot[["매출총이익률 (%)", "영업이익률 (%)"]].isna().all().all():
                st.warning("유효한 Peer 데이터를 입력해 주세요.")
            else:
                fig = go.Figure()
                for _, row in df_plot.iterrows():
                    fig.add_trace(go.Bar(
                        name=row["기업명"],
                        x=["매출총이익률 (%)", "영업이익률 (%)"],
                        y=[row.get("매출총이익률 (%)"), row.get("영업이익률 (%)")],
                    ))
                fig.update_layout(
                    title="Peer 수익성 비교",
                    barmode="group", plot_bgcolor="white", height=400,
                    yaxis_title="%",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"차트 생성 오류: {e}")
