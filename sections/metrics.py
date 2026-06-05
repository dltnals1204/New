import plotly.graph_objects as go
import streamlit as st
from utils.data_proc import calc_metrics

C = {"roe":"#2E86AB","roic":"#44BBA4","roa":"#F18F01","de":"#C73E1D","debt":"#A23B72"}


def render(df_cum):
    if df_cum.empty: st.warning("재무 데이터가 없습니다."); return
    df_m = calc_metrics(df_cum)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("① 수익성 — ROE / ROIC / ROA")
        if any(df_m[c].notna().any() for c in ["roe","roic","roa"]):
            fig = go.Figure()
            for col,name,color in [("roe","ROE",C["roe"]),("roic","ROIC",C["roic"]),("roa","ROA",C["roa"])]:
                v = df_m[df_m[col].notna()]
                fig.add_trace(go.Scatter(x=v["period"],y=v[col].round(1),name=f"{name} (%)",
                                          mode="lines+markers",line=dict(color=color,width=2),marker=dict(size=7)))
            fig.add_hline(y=0,line_dash="dot",line_color="#aaa")
            fig.update_layout(title="수익성 (%)",hovermode="x unified",plot_bgcolor="white",height=360,
                              legend=dict(orientation="h",yanchor="bottom",y=1.02))
            fig.update_xaxes(showgrid=False); fig.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("수익성 지표 없음",icon="ℹ️")
    with col2:
        st.subheader("② 안정성 — 부채비율")
        if any(df_m[c].notna().any() for c in ["de_ratio","debt_ratio"]):
            fig2 = go.Figure()
            for col,name,color in [("de_ratio","부채비율",C["de"]),("debt_ratio","자산부채비율",C["debt"])]:
                v = df_m[df_m[col].notna()]
                fig2.add_trace(go.Scatter(x=v["period"],y=v[col].round(1),name=f"{name} (%)",
                                           mode="lines+markers",line=dict(color=color,width=2),marker=dict(size=7)))
            fig2.add_hline(y=0,line_dash="dot",line_color="#aaa")
            fig2.update_layout(title="안정성 (%)",hovermode="x unified",plot_bgcolor="white",height=360,
                               legend=dict(orientation="h",yanchor="bottom",y=1.02))
            fig2.update_xaxes(showgrid=False); fig2.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
            st.plotly_chart(fig2,use_container_width=True)
        else:
            st.info("안정성 지표 없음",icon="ℹ️")
    st.subheader("③ 순부채 추이")
    if df_m["net_debt"].notna().any():
        fig3 = go.Figure(go.Bar(x=df_m["period"],y=df_m["net_debt"]/1e8,name="순부채",marker_color=C["de"],opacity=0.8))
        fig3.add_hline(y=0,line_dash="dot",line_color="#aaa")
        fig3.update_layout(title="순부채 (억원, 음수=순현금)",hovermode="x unified",plot_bgcolor="white",height=320)
        fig3.update_xaxes(showgrid=False); fig3.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
        st.plotly_chart(fig3,use_container_width=True)
