import plotly.graph_objects as go
import streamlit as st
import numpy as np
from utils.data_proc import calc_nwc

C = {"dso": "#2E86AB", "dio": "#F18F01", "dpo": "#A23B72", "ccc": "#44BBA4"}


def _nwc_bar(df):
    fig = go.Figure()
    for col, name in [("dso", "DSO (채권 회수일)"), ("dio", "DIO (재고 회전일)"), ("dpo", "DPO (채무 지급일)")]:
        valid = df[df[col].notna()]
        fig.add_trace(go.Bar(x=valid["period"], y=valid[col].round(1), name=name,
                             marker_color=C[col], opacity=0.85))
    fig.update_layout(title="연도별 DSO / DIO / DPO (일)", barmode="group",
                      hovermode="x unified", plot_bgcolor="white", height=400,
                      yaxis_title="일수 (Days)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _ccc_chart(df):
    valid = df[df["ccc"].notna()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid["period"], y=valid["ccc"].round(1),
                              name="CCC (일)", mode="lines+markers",
                              line=dict(color=C["ccc"], width=2.5), marker=dict(size=8),
                              fill="tozeroy", fillcolor="rgba(68,187,164,0.15)"))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(title="Cash Conversion Cycle (DSO + DIO − DPO)",
                      hovermode="x unified", plot_bgcolor="white", height=320,
                      yaxis_title="일수 (Days)")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def render(df_cum):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    df_nwc = calc_nwc(df_cum)
    has = any(df_nwc[col].notna().any() for col in ["dso","dio","dpo"] if col in df_nwc.columns)
    if not has:
        st.warning("NWC 계산에 필요한 데이터(매출채권+미수금, 재고자산, 매입채무+미지급금)를 찾을 수 없습니다.")
        return

    st.caption("채권: 매출채권 + 미수금 | 채무: 매입채무 + 미지급금 | 재고: 재고자산")

    st.subheader("① DSO / DIO / DPO")
    st.plotly_chart(_nwc_bar(df_nwc), use_container_width=True)

    st.subheader("② Cash Conversion Cycle")
    st.plotly_chart(_ccc_chart(df_nwc), use_container_width=True)

    st.subheader("③ NWC 요약 테이블")
    tbl_cols = {
        "period": "연도",
        "receivables": "채권 (억원)", "inventory_v": "재고 (억원)", "payables": "채무 (억원)",
        "dso": "DSO (일)", "dio": "DIO (일)", "dpo": "DPO (일)", "ccc": "CCC (일)",
        "ar_turnover": "채권회전율", "inv_turnover": "재고회전율", "ap_turnover": "채무회전율",
    }
    tbl = df_nwc[[c for c in tbl_cols if c in df_nwc.columns]].copy()
    for c in ["receivables", "inventory_v", "payables"]:
        if c in tbl.columns:
            tbl[c] = tbl[c] / 1e8
    tbl = tbl.rename(columns=tbl_cols)
    fmt = {c: "{:,.1f}" for c in tbl.columns if c != "연도"}
    st.dataframe(tbl.set_index("연도").style.format(fmt, na_rep="—"), use_container_width=True)
