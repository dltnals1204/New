import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from utils.data_proc import make_quarter_df, make_annual_df, add_margins, extract_sga_detail


def render(df_cum, statements, df_emp=None):
    if df_cum.empty: st.warning("재무 데이터가 없습니다."); return
    view = st.radio("기간 선택",["분기별","연도별"],horizontal=True,key="sga_view")
    df = add_margins(make_quarter_df(df_cum) if view=="분기별" else make_annual_df(df_cum))
    label = "분기별" if view=="분기별" else "연도별"

    st.subheader("① 총 판매관리비")
    if df["sga"].notna().any() and (df["sga"]!=0).any():
        valid = df[df["sga"].notna() & (df["sga"]!=0)]
        fig = make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=valid["period"],y=valid["sga"]/1e8,name="판관비 (억원)",
                             marker_color="#A23B72",opacity=0.85,text=(valid["sga"]/1e8).round(0),
                             textposition="outside",texttemplate="%{text:,.0f}"),secondary_y=False)
        fig.add_trace(go.Scatter(x=valid["period"],y=valid["sga_pct"].round(1),name="판관비율 (%)",
                                  mode="lines+markers",line=dict(color="#F18F01",width=2),marker=dict(size=7)),secondary_y=True)
        fig.update_layout(title=f"판매관리비 ({label})",hovermode="x unified",plot_bgcolor="white",height=380,
                          legend=dict(orientation="h",yanchor="bottom",y=1.02))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(title_text="금액 (억원)",showgrid=True,gridcolor="#f0f0f0",secondary_y=False)
        fig.update_yaxes(title_text="매출대비 (%)",showgrid=False,secondary_y=True)
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning("판관비 데이터 없음")

    st.subheader("② 판관비 세부 항목")
    with st.spinner("세부 항목 추출 중..."):
        df_detail = extract_sga_detail(statements)
    if df_detail.empty:
        st.info("📌 판관비 세부 항목을 추출할 수 없습니다.",icon="ℹ️")

    st.subheader("③ 임직원 현황")
    if df_emp is None or df_emp.empty:
        st.info("📌 임직원 현황 데이터를 가져올 수 없습니다.",icon="ℹ️")
    else:
        try:
            df_e = df_emp[df_emp["period"]=="Annual"].copy()
            for col in ["fyer_enpls_co"]:
                if col in df_e.columns:
                    df_e[col] = pd.to_numeric(df_e[col].astype(str).str.replace(",",""),errors="coerce")
            exec_df = df_e[df_e["fo_bbm"].astype(str).str.contains("임원|등기|사외",na=False)]
            emp_df  = df_e[~df_e["fo_bbm"].astype(str).str.contains("임원|등기|사외",na=False)]
            fig = go.Figure()
            for d, name, color in [(emp_df,"직원","#2E86AB"),(exec_df,"임원","#F18F01")]:
                t = d.groupby("year")["fyer_enpls_co"].sum().reset_index()
                t["year"] = t["year"].astype(str)
                fig.add_trace(go.Bar(x=t["year"],y=t["fyer_enpls_co"],name=name,marker_color=color))
            fig.update_layout(title="연도별 임직원 수",barmode="stack",hovermode="x unified",
                              plot_bgcolor="white",height=360,yaxis_title="인원 (명)")
            fig.update_xaxes(showgrid=False); fig.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
            st.plotly_chart(fig,use_container_width=True)
        except Exception as e:
            st.warning(f"임직원 데이터 오류: {e}")
