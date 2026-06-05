import numpy as np
import plotly.graph_objects as go
import streamlit as st
from utils.data_proc import make_quarter_df, make_annual_df, add_growth, add_annual_yoy, detect_ytd

COLORS = ["#2E86AB","#A23B72","#F18F01","#C73E1D","#3B1F2B","#44BBA4","#E94F37","#393E41"]


def render(df_cum):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다."); return
    ytd_year, ytd_period = detect_ytd(df_cum)
    if ytd_year:
        label = {"Q1":"1분기","Q2":"반기","Q3":"3분기"}.get(ytd_period, ytd_period)
        st.info(f"⚠️ 최신 데이터: {ytd_year}년 {label} (YTD).", icon="📅")
    view = st.radio("기간 선택",["분기별","연도별"],horizontal=True,key="rev_view")
    df_q = add_growth(make_quarter_df(df_cum))
    df_a = add_annual_yoy(make_annual_df(df_cum))
    df = df_q if view == "분기별" else df_a
    suffix = "분기별" if view == "분기별" else "연도별"

    st.subheader("① 총 매출액")
    fig = go.Figure(go.Bar(x=df["period"], y=df["revenue"]/1e8, name="매출액",
                            marker_color=COLORS[0], text=(df["revenue"]/1e8).round(0),
                            textposition="outside", texttemplate="%{text:,.0f}"))
    fig.update_layout(title=f"매출액 ({suffix})", yaxis_title="억원",
                      hovermode="x unified", plot_bgcolor="white", height=380)
    fig.update_xaxes(showgrid=False); fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("② 사업부문별 매출")
    st.info("📌 사업부문별 데이터는 DART 주석 파싱이 필요합니다.", icon="ℹ️")
    st.subheader("③ 지역별 매출")
    st.info("📌 지역별 데이터는 DART 주석 파싱이 필요합니다.", icon="ℹ️")

    st.subheader("④ 매출 성장률")
    fig2 = go.Figure()
    if view == "분기별":
        if "qoq" in df_q.columns:
            fig2.add_trace(go.Scatter(x=df_q["period"],y=df_q["qoq"].round(1),name="QoQ (%)",
                                      mode="lines+markers",line=dict(color=COLORS[1],width=2),marker=dict(size=7)))
        if "yoy" in df_q.columns:
            fig2.add_trace(go.Scatter(x=df_q["period"],y=df_q["yoy"].round(1),name="YoY (%)",
                                      mode="lines+markers",line=dict(color=COLORS[2],width=2),marker=dict(size=7)))
    else:
        fig2.add_trace(go.Scatter(x=df_a["period"],y=df_a["yoy"].round(1),name="YoY (%)",
                                  mode="lines+markers",line=dict(color=COLORS[2],width=2),marker=dict(size=8)))
    fig2.add_hline(y=0,line_dash="dot",line_color="gray")
    fig2.update_layout(title=f"성장률 ({suffix})",yaxis_title="%",hovermode="x unified",
                       plot_bgcolor="white",height=340)
    fig2.update_xaxes(showgrid=False); fig2.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig2, use_container_width=True)
