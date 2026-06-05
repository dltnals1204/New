import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import make_annual_df, make_quarter_df, build_indirect_cashflow

C = {"cfo": "#2E86AB", "cfi": "#A23B72", "cff": "#F18F01", "fcf": "#44BBA4",
     "ebitda": "#2E86AB", "nwc": "#44BBA4", "capex": "#C73E1D", "fin": "#F18F01"}
D = 1e8


def _indirect_table(df: pd.DataFrame):
    """간접법 현금흐름표 — 시계열 표"""
    cols_def = [
        ("ebitda",         "EBITDA"),
        ("nwc_movement",   "  + NWC Movement"),
        ("ebitda_after_nwc", "= EBITDA after NWC"),
        ("ccr_nwc",        "  Cash Conversion Ratio (NWC 후, %)"),
        ("capex_neg",      "  - Capex"),
        ("cff_val",        "  - 재무활동현금흐름"),
        ("other_op",       "  - 기타 영업활동현금흐름 (잔차)"),
        ("fcf",            "= FCF"),
        ("ccr_fcf",        "  Cash Conversion Ratio (FCF/EBITDA, %)"),
        ("net_cash_chg",   "  현금변동 (검증)"),
    ]
    pct_rows = {"ccr_nwc", "ccr_fcf"}
    periods = sorted(df["period"].dropna().unique())
    df_idx = df.set_index("period")

    table_data = {}
    for col, label in cols_def:
        if col not in df_idx.columns:
            continue
        row = {}
        for p in periods:
            val = df_idx.loc[p, col] if p in df_idx.index else np.nan
            if isinstance(val, float) and np.isnan(val):
                row[p] = "—"
            elif col in pct_rows:
                row[p] = f"{val:.1f}%"
            else:
                row[p] = f"{val/D:,.0f}"
        table_data[label] = row

    table_df = pd.DataFrame(table_data).T
    table_df.index.name = "항목 (억원, % 제외)"

    # 굵게 표시할 행
    bold_rows = {"= EBITDA after NWC", "= FCF"}
    styled = table_df.style.apply(
        lambda row: ["font-weight: bold; background-color: #f0f4f8"
                     if row.name in bold_rows else "" for _ in row],
        axis=1
    )
    st.dataframe(styled, use_container_width=True, height=380)


def _direct_chart(df_a: pd.DataFrame):
    """직접법 현금흐름 차트 (CFO/CFI/CFF 라인 + FCF 막대)"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for col, name, color in [
        ("cfo", "영업활동현금흐름", C["cfo"]),
        ("cfi", "투자활동현금흐름", C["cfi"]),
        ("cff", "재무활동현금흐름", C["cff"]),
    ]:
        if col in df_a.columns and df_a[col].notna().any():
            fig.add_trace(go.Scatter(
                x=df_a["period"], y=df_a[col] / D, name=name,
                mode="lines+markers", line=dict(color=color, width=2),
                marker=dict(size=7),
            ), secondary_y=False)

    # FCF = CFO + CFI (단순 직접법)
    if "cfo" in df_a.columns and "cfi" in df_a.columns:
        fcf = (df_a["cfo"].fillna(0) + df_a["cfi"].fillna(0))
        fig.add_trace(go.Bar(
            x=df_a["period"], y=fcf / D, name="FCF",
            marker_color=C["fcf"], opacity=0.6,
        ), secondary_y=False)

    fig.update_layout(
        title="현금흐름 추이 (직접법)",
        hovermode="x unified", plot_bgcolor="white", height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        barmode="overlay",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title_text="금액 (억원)", showgrid=True, gridcolor="#f0f0f0")
    return fig


def _waterfall_chart(df: pd.DataFrame, period: str):
    """특정 연도 간접법 워터폴 차트"""
    if period not in df["period"].values:
        return None
    row = df[df["period"] == period].iloc[0]

    items = [
        ("EBITDA",           row.get("ebitda", np.nan)),
        ("NWC Movement",     row.get("nwc_movement", np.nan)),
        ("Capex",            row.get("capex_neg", np.nan)),
        ("재무활동CF",         row.get("cff_val", np.nan)),
        ("기타",              row.get("other_op", np.nan)),
        ("FCF",              row.get("fcf", np.nan)),
    ]
    labels = [i[0] for i in items]
    values = [i[1] / D if not (isinstance(i[1], float) and np.isnan(i[1])) else 0 for i in items]
    measure = ["absolute", "relative", "relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        name="", measure=measure,
        x=labels, y=values,
        connector=dict(line=dict(color="#aaa")),
        increasing=dict(marker_color="#44BBA4"),
        decreasing=dict(marker_color="#C73E1D"),
        totals=dict(marker_color="#2E86AB"),
        texttemplate="%{y:,.0f}억",
        textposition="outside",
    ))
    fig.update_layout(title=f"{period} 현금흐름 브리지 (억원)",
                      plot_bgcolor="white", height=380, showlegend=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def render(df_cum: pd.DataFrame):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    df_icf = build_indirect_cashflow(df_cum)
    df_a   = make_annual_df(df_cum)

    # ── 탭 구성 ──
    t1, t2, t3 = st.tabs(["📋 간접법 테이블", "📈 직접법 차트", "🌊 Bridge 차트"])

    with t1:
        st.subheader("간접법 현금흐름표 (억원)")
        st.caption("FCF = EBITDA + NWC Movement − Capex − 재무활동CF − 기타 / 현금변동과 비교 검증")
        if df_icf.empty or df_icf["ebitda"].isna().all():
            st.info("현금흐름 계산에 필요한 데이터(EBITDA, D&A)가 부족합니다.", icon="ℹ️")
        else:
            _indirect_table(df_icf)

    with t2:
        st.subheader("현금흐름 추이 (직접법)")
        if df_a[["cfo","cfi","cff"]].isna().all().all():
            st.info("영업/투자/재무활동 현금흐름 데이터가 없습니다.", icon="ℹ️")
        else:
            st.plotly_chart(_direct_chart(df_a), use_container_width=True)

    with t3:
        st.subheader("연도별 FCF 브리지 (Waterfall)")
        periods = sorted(df_icf["period"].dropna().unique(), reverse=True)
        sel = st.selectbox("연도 선택", periods, key="cf_wf_year")
        fig_wf = _waterfall_chart(df_icf, sel)
        if fig_wf:
            st.plotly_chart(fig_wf, use_container_width=True)
        else:
            st.info("선택 연도 데이터가 없습니다.")
