import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import (
    make_quarter_df, make_annual_df, add_margins,
    extract_sga_detail, cumulative_to_actual,
)

BAR_COLOR  = "#A23B72"
LINE_COLOR = "#F18F01"


def _sga_combo(df: pd.DataFrame, title: str) -> go.Figure:
    divisor = 1e8
    valid = df[df["sga"].notna() & (df["sga"] != 0)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=valid["period"], y=valid["sga"] / divisor,
            name="판관비 (억원)",
            marker_color=BAR_COLOR, opacity=0.85,
            text=(valid["sga"] / divisor).round(0),
            textposition="outside",
            texttemplate="%{text:,.0f}",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=valid["period"], y=valid["sga_pct"].round(1),
            name="판관비율 (%)", mode="lines+markers",
            line=dict(color=LINE_COLOR, width=2),
            marker=dict(size=7),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title=title, hovermode="x unified",
        plot_bgcolor="white", height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title_text="금액 (억원)", showgrid=True, gridcolor="#f0f0f0", secondary_y=False)
    fig.update_yaxes(title_text="매출액 대비 (%)", showgrid=False, secondary_y=True)
    return fig


def _detail_table(
    df_detail: pd.DataFrame,
    df_main: pd.DataFrame,
    view: str,
) -> None:
    """SG&A 세부 항목 피벗 테이블"""
    if df_detail.empty:
        st.info(
            "📌 판관비 세부 항목 데이터를 추출할 수 없습니다.\n\n"
            "DART 공시에서 판관비 하위 계정이 별도 기재되지 않은 경우입니다.",
            icon="ℹ️",
        )
        return

    # 분기/연도별 필터
    if view == "분기별":
        df_detail = df_detail[df_detail["period"] != "Annual"]
        df_detail = df_detail.copy()
        _qmap = {"Q1": 1, "Q2": 2, "Q3": 3}
        df_detail["label"] = df_detail.apply(
            lambda r: f"{r['year']}Q{_qmap.get(r['period'], r['period'])}",
            axis=1,
        )
    else:
        df_detail = df_detail[df_detail["period"] == "Annual"].copy()
        df_detail["label"] = df_detail["year"].astype(str)

    if df_detail.empty:
        return

    pivot = df_detail.pivot_table(
        index="account", columns="label", values="amount", aggfunc="sum"
    )
    pivot = pivot / 1e8  # 억원

    # 매출액 대비 % 테이블
    rev_map = df_main.set_index("period")["revenue"].to_dict()
    pct_pivot = pivot.copy()
    for col in pivot.columns:
        rev = rev_map.get(col, np.nan)
        pct_pivot[col] = pivot[col] / (rev / 1e8) * 100 if rev and not np.isnan(rev) else np.nan

    st.markdown("**판관비 세부 항목 (억원)**")
    st.dataframe(
        pivot.style.format("{:,.1f}").background_gradient(axis=1, cmap="Blues"),
        use_container_width=True,
    )
    st.markdown("**판관비 세부 항목 / 매출액 (%)**")
    st.dataframe(
        pct_pivot.style.format("{:.1f}%").background_gradient(axis=1, cmap="Oranges"),
        use_container_width=True,
    )


def render(df_cum: pd.DataFrame, statements: dict):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    view = st.radio(
        "기간 선택",
        ["분기별", "연도별"],
        horizontal=True,
        key="sga_view",
    )

    df_q = add_margins(make_quarter_df(df_cum))
    df_a = add_margins(make_annual_df(df_cum))
    df = df_q if view == "분기별" else df_a
    label = "분기별" if view == "분기별" else "연도별"

    # ── 1. 총 판관비 콤보 ───────────────────────────────────────────────
    st.subheader("① 총 판매관리비")
    if df["sga"].notna().any() and (df["sga"] != 0).any():
        fig = _sga_combo(df, f"판매관리비 & 매출액 대비 비율 ({label})")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("판관비 데이터를 찾을 수 없습니다.")

    # ── 2. SG&A 세부 ─────────────────────────────────────────────────────
    st.subheader("② 판관비 세부 항목")
    with st.spinner("세부 항목 추출 중..."):
        df_detail = extract_sga_detail(statements)
    _detail_table(df_detail, df, view)
