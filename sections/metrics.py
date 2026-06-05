import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import calc_metrics

C = {"roe": "#2E86AB", "roic": "#44BBA4", "roa": "#F18F01",
     "de": "#C73E1D", "debt": "#A23B72"}


def _line_chart(df, cols_names, title, yaxis="%", height=360):
    fig = go.Figure()
    for col, name, color in cols_names:
        valid = df[df[col].notna()]
        fig.add_trace(go.Scatter(
            x=valid["period"], y=valid[col].round(1), name=name,
            mode="lines+markers", line=dict(color=color, width=2), marker=dict(size=7),
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="#aaa")
    fig.update_layout(title=title, yaxis_title=yaxis, hovermode="x unified",
                      plot_bgcolor="white", height=height,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _bar_line_combo(df, bar_col, line_col, bar_name, line_name, bar_color, line_color, title):
    D = 1e8
    valid = df[df[bar_col].notna()]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=valid["period"], y=valid[bar_col] / D, name=bar_name,
        marker_color=bar_color, opacity=0.8,
    ), secondary_y=False)
    valid2 = df[df[line_col].notna()]
    fig.add_trace(go.Scatter(
        x=valid2["period"], y=valid2[line_col].round(1), name=line_name,
        mode="lines+markers", line=dict(color=line_color, width=2), marker=dict(size=7),
    ), secondary_y=True)
    fig.update_layout(title=title, hovermode="x unified", plot_bgcolor="white", height=360,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title_text="금액 (억원)", showgrid=True, gridcolor="#f0f0f0", secondary_y=False)
    fig.update_yaxes(title_text="비율 (%)", showgrid=False, secondary_y=True)
    return fig


def render(df_cum):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    df_m = calc_metrics(df_cum)

    col1, col2 = st.columns(2)

    # ── 수익성 ───────────────────────────────────────────────────────────
    with col1:
        st.subheader("① 수익성 — ROE / ROIC / ROA")
        has = any(df_m[c].notna().any() for c in ["roe","roic","roa"])
        if has:
            fig = _line_chart(df_m, [
                ("roe",  "ROE (%)",  C["roe"]),
                ("roic", "ROIC (%)", C["roic"]),
                ("roa",  "ROA (%)",  C["roa"]),
            ], "수익성 지표 (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("순이익/자본 데이터 부족으로 수익성 지표를 계산할 수 없습니다.", icon="ℹ️")

    # ── 안정성 ───────────────────────────────────────────────────────────
    with col2:
        st.subheader("② 안정성 — 부채비율 / 자산부채비율")
        has2 = any(df_m[c].notna().any() for c in ["de_ratio","debt_ratio"])
        if has2:
            fig = _line_chart(df_m, [
                ("de_ratio",   "부채비율 (부채/자본, %)", C["de"]),
                ("debt_ratio", "자산부채비율 (부채/자산, %)", C["debt"]),
            ], "안정성 지표 (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("부채/자본 데이터 부족으로 안정성 지표를 계산할 수 없습니다.", icon="ℹ️")

    # ── 순부채 ───────────────────────────────────────────────────────────
    st.subheader("③ 순부채 추이")
    if df_m["net_debt"].notna().any():
        fig_nd = go.Figure()
        fig_nd.add_trace(go.Bar(
            x=df_m["period"], y=df_m["net_debt"] / 1e8, name="순부채 (억원)",
            marker_color=C["de"], opacity=0.8,
        ))
        fig_nd.add_hline(y=0, line_dash="dot", line_color="#aaa")
        fig_nd.update_layout(title="연도별 순부채 (억원, 음수=순현금)",
                             hovermode="x unified", plot_bgcolor="white", height=320)
        fig_nd.update_xaxes(showgrid=False)
        fig_nd.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig_nd, use_container_width=True)

    # ── 지표 요약 테이블 ──────────────────────────────────────────────────
    st.subheader("④ 지표 요약")
    tbl_cols = {
        "period": "연도", "roe": "ROE (%)", "roic": "ROIC (%)", "roa": "ROA (%)",
        "de_ratio": "부채비율 (%)", "debt_ratio": "자산부채비율 (%)",
        "net_debt": "순부채 (억원)",
    }
    tbl = df_m[[c for c in tbl_cols if c in df_m.columns]].rename(columns=tbl_cols).copy()
    if "순부채 (억원)" in tbl.columns:
        tbl["순부채 (억원)"] = tbl["순부채 (억원)"] / 1e8
    fmt = {c: "{:.1f}" for c in tbl.columns if c != "연도"}
    if "순부채 (억원)" in fmt:
        fmt["순부채 (억원)"] = "{:,.0f}"
    st.dataframe(tbl.set_index("연도").style.format(fmt, na_rep="—"), use_container_width=True)

    st.caption("⚠️ 배당수익률(시가배당률)은 주가 데이터가 연동된 후 주가정보 섹션에서 제공됩니다.")
