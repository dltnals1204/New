import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import (
    make_quarter_df, make_annual_df,
    add_growth, add_annual_yoy,
    detect_ytd,
)

COLORS = [
    "#2E86AB", "#A23B72", "#F18F01", "#C73E1D",
    "#3B1F2B", "#44BBA4", "#E94F37", "#393E41",
]


def _bar_revenue(df: pd.DataFrame, title: str, unit: str = "억원") -> go.Figure:
    divisor = 1e8
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["period"],
        y=df["revenue"] / divisor,
        name="매출액",
        marker_color=COLORS[0],
        text=(df["revenue"] / divisor).round(0),
        textposition="outside",
        texttemplate="%{text:,.0f}",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title=f"매출액 ({unit})",
        hovermode="x unified",
        plot_bgcolor="white",
        height=380,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _growth_chart(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    if "qoq" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["period"], y=df["qoq"].round(1),
            name="QoQ (%)", mode="lines+markers",
            line=dict(color=COLORS[1], width=2),
            marker=dict(size=7),
        ))
    if "yoy" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["period"], y=df["yoy"].round(1),
            name="YoY (%)", mode="lines+markers",
            line=dict(color=COLORS[2], width=2),
            marker=dict(size=7),
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=title,
        yaxis_title="성장률 (%)",
        hovermode="x unified",
        plot_bgcolor="white",
        height=340,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _segment_placeholder(label: str):
    st.info(
        f"📌 **{label}** 데이터는 DART 주석(Note) 파싱이 필요합니다.\n\n"
        "표준 재무제표 API에서는 사업부문/지역별 분류가 제공되지 않습니다. "
        "해당 기능은 추후 공시 원문 파싱 또는 수기 입력 방식으로 지원 예정입니다.",
        icon="ℹ️",
    )


def render(df_cum: pd.DataFrame):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    ytd_year, ytd_period = detect_ytd(df_cum)
    if ytd_year:
        period_label = {"Q1": "1분기", "Q2": "반기", "Q3": "3분기"}.get(ytd_period, ytd_period)
        st.info(
            f"⚠️ 최신 데이터: {ytd_year}년 {period_label} (YTD). "
            "매출액 막대 차트에 YTD 수치를 별도 표기합니다.",
            icon="📅",
        )

    # ── 분기/연도 전환 토글 ────────────────────────────────────────────────
    view = st.radio(
        "기간 선택",
        ["분기별", "연도별"],
        horizontal=True,
        key="rev_view",
    )

    df_q = add_growth(make_quarter_df(df_cum))
    df_a = add_annual_yoy(make_annual_df(df_cum))
    df = df_q if view == "분기별" else df_a

    # ── 1. 총 매출액 ─────────────────────────────────────────────────────
    st.subheader("① 총 매출액")
    title_suffix = "분기별" if view == "분기별" else "연도별"

    fig_rev = _bar_revenue(df, f"매출액 ({title_suffix})")

    # YTD 표시 (분기별 + YTD 존재 시)
    if view == "분기별" and ytd_year:
        ytd_rev = df_cum[
            (df_cum["year"] == ytd_year) & (df_cum["period"] == ytd_period)
        ]["revenue"].values
        if len(ytd_rev) > 0 and not np.isnan(ytd_rev[0]):
            fig_rev.add_annotation(
                x=f"{ytd_year}Q{'12334'.index(str({'Q1':1,'Q2':2,'Q3':3}.get(ytd_period,1)))+1}",
                y=ytd_rev[0] / 1e8,
                text=f"YTD {ytd_rev[0]/1e8:,.0f}억",
                showarrow=True,
                arrowhead=2,
                font=dict(color="red"),
            )

    st.plotly_chart(fig_rev, use_container_width=True)

    # ── 2. 사업부문별 매출 ──────────────────────────────────────────────
    st.subheader("② 사업부문별 매출")
    _segment_placeholder("사업부문별 매출액")

    # ── 3. 지역별 매출 ──────────────────────────────────────────────────
    st.subheader("③ 지역별 매출 (내수/수출)")
    _segment_placeholder("지역별 매출액 (내수/수출/국가별)")

    # ── 4. 성장률 ────────────────────────────────────────────────────────
    st.subheader("④ 매출 성장률")
    if view == "분기별":
        fig_growth = _growth_chart(df_q, "분기별 QoQ / YoY 성장률 (%)")
        st.plotly_chart(fig_growth, use_container_width=True)
    else:
        fig_yoy = go.Figure()
        fig_yoy.add_trace(go.Scatter(
            x=df_a["period"], y=df_a["yoy"].round(1),
            name="YoY (%)", mode="lines+markers",
            line=dict(color=COLORS[2], width=2),
            marker=dict(size=8),
        ))
        fig_yoy.add_hline(y=0, line_dash="dot", line_color="gray")
        fig_yoy.update_layout(
            title="연도별 YoY 성장률 (%)",
            yaxis_title="성장률 (%)",
            hovermode="x unified",
            plot_bgcolor="white",
            height=340,
        )
        fig_yoy.update_xaxes(showgrid=False)
        fig_yoy.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig_yoy, use_container_width=True)
