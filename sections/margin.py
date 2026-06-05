import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import make_quarter_df, make_annual_df, add_ebitda, add_margins

BAR_COLOR = "#2E86AB"; LINE_COLOR = "#C73E1D"


def _combo(df, amount_col, pct_col, bar_label, line_label, title):
    valid = df[df[amount_col].notna() & (df[amount_col] != 0)]
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=valid["period"],y=valid[amount_col]/1e8,name=bar_label,
                          marker_color=BAR_COLOR,opacity=0.85,text=(valid[amount_col]/1e8).round(0),
                          textposition="outside",texttemplate="%{text:,.0f}"),secondary_y=False)
    fig.add_trace(go.Scatter(x=valid["period"],y=valid[pct_col].round(1),name=line_label,
                              mode="lines+markers",line=dict(color=LINE_COLOR,width=2),marker=dict(size=7)),secondary_y=True)
    fig.update_layout(title=title,hovermode="x unified",plot_bgcolor="white",height=380,
                      legend=dict(orientation="h",yanchor="bottom",y=1.02))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title_text="금액 (억원)",showgrid=True,gridcolor="#f0f0f0",secondary_y=False)
    fig.update_yaxes(title_text="마진율 (%)",showgrid=False,secondary_y=True)
    return fig


def render(df_cum):
    if df_cum.empty: st.warning("재무 데이터가 없습니다."); return
    view = st.radio("기간 선택",["분기별","연도별"],horizontal=True,key="margin_view")
    df = add_margins(add_ebitda(make_quarter_df(df_cum) if view=="분기별" else make_annual_df(df_cum)))
    label = "분기별" if view=="분기별" else "연도별"
    st.subheader("① 매출총이익 / 매출총이익률")
    if df["gross_profit"].notna().any():
        st.plotly_chart(_combo(df,"gross_profit","gross_margin","매출총이익 (억원)","매출총이익률 (%)",f"매출총이익 ({label})"),use_container_width=True)
    else:
        st.info("매출총이익 데이터 없음",icon="ℹ️")
    st.subheader("② 영업이익 / 영업이익률")
    if df["op_income"].notna().any():
        st.plotly_chart(_combo(df,"op_income","op_margin","영업이익 (억원)","영업이익률 (%)",f"영업이익 ({label})"),use_container_width=True)
    else:
        st.warning("영업이익 데이터 없음")
    st.subheader("③ EBITDA / EBITDA Margin")
    if df["ebitda"].notna().any() and (df["ebitda"]!=0).any():
        st.plotly_chart(_combo(df,"ebitda","ebitda_margin","EBITDA (억원)","EBITDA Margin (%)",f"EBITDA ({label})"),use_container_width=True)
    else:
        st.info("📌 EBITDA는 D&A 데이터가 필요합니다.",icon="ℹ️")
