import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import make_quarter_df, make_annual_df, add_margins, extract_sga_detail

BAR_COLOR  = "#A23B72"
LINE_COLOR = "#F18F01"


def _sga_combo(df, title):
    valid = df[df["sga"].notna() & (df["sga"] != 0)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=valid["period"], y=valid["sga"] / 1e8, name="판관비 (억원)",
                         marker_color=BAR_COLOR, opacity=0.85,
                         text=(valid["sga"] / 1e8).round(0), textposition="outside",
                         texttemplate="%{text:,.0f}"), secondary_y=False)
    fig.add_trace(go.Scatter(x=valid["period"], y=valid["sga_pct"].round(1),
                              name="판관비율 (%)", mode="lines+markers",
                              line=dict(color=LINE_COLOR, width=2), marker=dict(size=7)),
                  secondary_y=True)
    fig.update_layout(title=title, hovermode="x unified", plot_bgcolor="white", height=380,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title_text="금액 (억원)", showgrid=True, gridcolor="#f0f0f0", secondary_y=False)
    fig.update_yaxes(title_text="매출액 대비 (%)", showgrid=False, secondary_y=True)
    return fig


def _detail_table(df_detail, df_main, view):
    if df_detail.empty:
        st.info("📌 판관비 세부 항목 데이터를 추출할 수 없습니다. DART 공시에서 하위 계정이 별도 기재되지 않은 경우입니다.", icon="ℹ️")
        return
    if view == "분기별":
        df_detail = df_detail[df_detail["period"] != "Annual"].copy()
        _qmap = {"Q1": 1, "Q2": 2, "Q3": 3}
        df_detail["label"] = df_detail.apply(lambda r: f"{r['year']}Q{_qmap.get(r['period'], r['period'])}", axis=1)
    else:
        df_detail = df_detail[df_detail["period"] == "Annual"].copy()
        df_detail["label"] = df_detail["year"].astype(str)
    if df_detail.empty:
        return
    pivot = df_detail.pivot_table(index="account", columns="label", values="amount", aggfunc="sum") / 1e8
    rev_map = df_main.set_index("period")["revenue"].to_dict()
    pct_pivot = pivot.copy()
    for col in pivot.columns:
        rev = rev_map.get(col, np.nan)
        pct_pivot[col] = pivot[col] / (rev / 1e8) * 100 if rev and not (isinstance(rev, float) and np.isnan(rev)) else np.nan
    st.markdown("**판관비 세부 항목 (억원)**")
    st.dataframe(pivot.style.format("{:,.1f}").background_gradient(axis=1, cmap="Blues"), use_container_width=True)
    st.markdown("**판관비 세부 항목 / 매출액 (%)**")
    st.dataframe(pct_pivot.style.format("{:.1f}%").background_gradient(axis=1, cmap="Oranges"), use_container_width=True)


def _headcount_section(df_emp: pd.DataFrame):
    """임직원 현황 차트"""
    if df_emp.empty:
        st.info("📌 임직원 현황 데이터를 가져올 수 없습니다. DART 임직원현황(empSttus) API 응답이 없는 경우입니다.", icon="ℹ️")
        return

    try:
        df = df_emp.copy()
        df = df[df["period"] == "Annual"]
        # 수치 컬럼 정리
        for col in ["fyer_enpls_co", "bsis_enpls_co", "enpls_co"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

        # 임원/직원 분리
        exec_df = df[df["fo_bbm"].astype(str).str.contains("임원|등기|사외", na=False)]
        emp_df  = df[~df["fo_bbm"].astype(str).str.contains("임원|등기|사외", na=False)]

        exec_total = exec_df.groupby("year")["fyer_enpls_co"].sum().reset_index()
        emp_total  = emp_df.groupby("year")["fyer_enpls_co"].sum().reset_index()
        exec_total["year"] = exec_total["year"].astype(str)
        emp_total["year"]  = emp_total["year"].astype(str)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=emp_total["year"],  y=emp_total["fyer_enpls_co"],
                             name="직원",  marker_color="#2E86AB"))
        fig.add_trace(go.Bar(x=exec_total["year"], y=exec_total["fyer_enpls_co"],
                             name="임원",  marker_color="#F18F01"))
        fig.update_layout(title="연도별 임직원 수", barmode="stack",
                          hovermode="x unified", plot_bgcolor="white", height=360,
                          yaxis_title="인원 (명)",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"임직원 데이터 처리 중 오류: {e}")


def render(df_cum, statements, df_emp=None):
    if df_cum.empty:
        st.warning("재무 데이터가 없습니다.")
        return

    view = st.radio("기간 선택", ["분기별", "연도별"], horizontal=True, key="sga_view")
    df_q = add_margins(make_quarter_df(df_cum))
    df_a = add_margins(make_annual_df(df_cum))
    df   = df_q if view == "분기별" else df_a
    label = "분기별" if view == "분기별" else "연도별"

    st.subheader("① 총 판매관리비")
    if df["sga"].notna().any() and (df["sga"] != 0).any():
        st.plotly_chart(_sga_combo(df, f"판매관리비 & 매출액 대비 비율 ({label})"), use_container_width=True)
    else:
        st.warning("판관비 데이터를 찾을 수 없습니다.")

    st.subheader("② 판관비 세부 항목")
    with st.spinner("세부 항목 추출 중..."):
        df_detail = extract_sga_detail(statements)
    _detail_table(df_detail, df, view)

    st.subheader("③ 임직원 현황")
    _headcount_section(df_emp if df_emp is not None else pd.DataFrame())
