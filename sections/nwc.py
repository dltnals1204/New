import plotly.graph_objects as go
import streamlit as st
from utils.data_proc import calc_nwc

C = {"dso":"#2E86AB","dio":"#F18F01","dpo":"#A23B72","ccc":"#44BBA4"}


def render(df_cum):
    if df_cum.empty: st.warning("재무 데이터가 없습니다."); return
    df_nwc = calc_nwc(df_cum)
    if not any(df_nwc[c].notna().any() for c in ["dso","dio","dpo"] if c in df_nwc.columns):
        st.warning("NWC 계산에 필요한 데이터가 없습니다."); return
    st.caption("채권: 매출채권+미수금 | 채무: 매입채무+미지급금 | 재고: 재고자산")
    st.subheader("① DSO / DIO / DPO")
    fig = go.Figure()
    for col, name in [("dso","DSO"),("dio","DIO"),("dpo","DPO")]:
        v = df_nwc[df_nwc[col].notna()]
        fig.add_trace(go.Bar(x=v["period"],y=v[col].round(1),name=name,marker_color=C[col],opacity=0.85))
    fig.update_layout(title="DSO / DIO / DPO (일)",barmode="group",hovermode="x unified",
                      plot_bgcolor="white",height=400,yaxis_title="일수 (Days)")
    fig.update_xaxes(showgrid=False); fig.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
    st.plotly_chart(fig,use_container_width=True)
    st.subheader("② Cash Conversion Cycle")
    v2 = df_nwc[df_nwc["ccc"].notna()]
    fig2 = go.Figure(go.Scatter(x=v2["period"],y=v2["ccc"].round(1),name="CCC",
                                mode="lines+markers",line=dict(color=C["ccc"],width=2.5),
                                marker=dict(size=8),fill="tozeroy",fillcolor="rgba(68,187,164,0.15)"))
    fig2.add_hline(y=0,line_dash="dot",line_color="gray")
    fig2.update_layout(title="CCC (DSO+DIO-DPO)",hovermode="x unified",plot_bgcolor="white",height=320,yaxis_title="일")
    fig2.update_xaxes(showgrid=False); fig2.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
    st.plotly_chart(fig2,use_container_width=True)
