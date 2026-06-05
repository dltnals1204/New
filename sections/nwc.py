import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from utils.data_proc import calc_nwc

COLORS = {
    "dso": "#2E86AB",
    "dio": "#F18F01",
    "dpo": "#A23B72",
    "ccc": "#44BBA4",
}


def _nwc_line(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    metrics = [
        ("dso", "DSO (매출채권 회수일)"),
        ("dio", "DIO (재고자산 회전일)"),
        ("dpo", "DPO (매입채무 지급일)"),
    ]
    for col, name in metrics:
        valid = df[df[col].notna()]
        fig.add_trace(go.Bar(
            x=valid["period"], y=valid[col].round(1),
            name=name,
            marker_color=COLORS[col],
            opacity=0.85,
        ))

    fig.update_layout(
        title="연도별 DSO / DIO / DPO (일)",
        barmode="group",
        hovermode="x unified",
        plot_bgcolor="white",
        height=400,
        yaxis_title="일수 (Days)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _ccc_line(df: pd.DataFrame) -> go.Figure:
    valid = df[df["ccc"].notna()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid["period"], y=valid["ccc"].round(1),
        name="Cash Conversion Cycle",
        mode="lines+markers",
        line=dict(color=COLORS["ccc"], width=2.5),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(68,187,164,0.15)",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="Cash Conversion Cycle (DSO + DIO − DPO)",
        hovermode="x unified",
        plot_bgcolor="white",
        height=320,
        yaxis_title="일수 (Days)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _nwc_table(df: pd.DataFrame) -> None:
    cols = {
        "period": "연도",
        "trade_rec": "매출채권 (억원)",
        "inventory": "재고자산 (억원)",
        "trade_pay": "매입채무 (억원)",
        "dso": "DSO (일)",
        "dio": "DIO (일)",
        "dpo": "DPO (일)",
        "ccc": "CCC (일)",
    }
    table = df[[c for c in cols if c in df.columns]].copy()
    for c in ["trade_rec", "inventory", "trade_pay"]:
        if c in table.columns:
            table[c] = table[c] / 1e8

    table = table.rename(columns=cols)
    fmt = {
        "매출채권 (억원)": "{:,.1f}",
        "재고자산 (억원)": "{:,.1f}",
        "매입채무 (억원)": "{:,.1f}",
        "DSO (일)": "{:.1f}",
        "DIO (일)": "{:.1f}",
        "DPO (일)": "{:.1f}",
        "CCC (일)": "{:.1f}",
    }
    st.dataframe(
        table.set_index("연도").style.format(fmt, na_rep="—"),
        use_container_width=True,
    )


def render(df_cum: pd.DataFrame):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    df_nwc = calc_nwc(df_cum)

    has_data = any(
        df_nwc[col].notna().any()
        for col in ["dso", "dio", "dpo"]
        if col in df_nwc.columns
    )

    if not has_data:
        st.warning(
            "NWC 계산에 필요한 데이터(매출채권, 재고자산, 매입채무)를 찾을 수 없습니다.\n\n"
            "재무상태표(BS) 데이터가 정상적으로 로드되었는지 확인해 주세요."
        )
        return

    st.subheader("① DSO / DIO / DPO")
    st.plotly_chart(_nwc_line(df_nwc), use_container_width=True)

    st.subheader("② Cash Conversion Cycle")
    st.plotly_chart(_ccc_line(df_nwc), use_container_width=True)

    st.subheader("③ NWC 요약 테이블")
    _nwc_table(df_nwc)
