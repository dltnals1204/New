import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.data_proc import make_annual_df, build_indirect_cashflow

C = {"cfo":"#2E86AB","cfi":"#A23B72","cff":"#F18F01","fcf":"#44BBA4"}
D = 1e8


def render(df_cum):
    if df_cum.empty: st.warning("재무 데이터가 없습니다."); return
    df_icf = build_indirect_cashflow(df_cum)
    df_a   = make_annual_df(df_cum)
    t1, t2, t3 = st.tabs(["📋 간접법 테이블","📈 직접법 차트","🌊 Bridge 차트"])

    with t1:
        st.subheader("간접법 현금흐름표 (억원)")
        if df_icf.empty or df_icf["ebitda"].isna().all():
            st.info("계산에 필요한 데이터가 부족합니다.",icon="ℹ️")
        else:
            cols_def = [("ebitda","EBITDA"),("nwc_movement","  + NWC"),("ebitda_after_nwc","= EBITDA after NWC"),
                        ("ccr_nwc","  CCR NWC (%)"),("capex_neg","  - Capex"),("cff_val","  - 재무CF"),
                        ("other_op","  - 기타"),("fcf","= FCF"),("ccr_fcf","  CCR FCF (%)"),("net_cash_chg","  현금변동")]
            pct_rows = {"ccr_nwc","ccr_fcf"}
            periods = sorted(df_icf["period"].dropna().unique())
            df_idx = df_icf.set_index("period")
            table_data = {}
            for col, label in cols_def:
                if col not in df_idx.columns: continue
                row = {}
                for p in periods:
                    val = df_idx.loc[p, col] if p in df_idx.index else np.nan
                    if isinstance(val, float) and np.isnan(val): row[p] = "—"
                    elif col in pct_rows: row[p] = f"{val:.1f}%"
                    else: row[p] = f"{val/D:,.0f}"
                table_data[label] = row
            tdf = pd.DataFrame(table_data).T
            tdf.index.name = "항목"
            bold = {"= EBITDA after NWC","= FCF"}
            st.dataframe(tdf.style.apply(lambda r: ["font-weight:bold;background:#f0f4f8" if r.name in bold else "" for _ in r],axis=1),use_container_width=True,height=380)

    with t2:
        st.subheader("현금흐름 추이 (직접법)")
        fig = go.Figure()
        for col,name,color in [("cfo","영업CF",C["cfo"]),("cfi","투자CF",C["cfi"]),("cff","재무CF",C["cff"])]:
            if col in df_a.columns and df_a[col].notna().any():
                fig.add_trace(go.Scatter(x=df_a["period"],y=df_a[col]/D,name=name,mode="lines+markers",
                                          line=dict(color=color,width=2),marker=dict(size=7)))
        if "cfo" in df_a.columns and "cfi" in df_a.columns:
            fig.add_trace(go.Bar(x=df_a["period"],y=(df_a["cfo"].fillna(0)+df_a["cfi"].fillna(0))/D,
                                  name="FCF",marker_color=C["fcf"],opacity=0.6))
        fig.update_layout(title="현금흐름 (직접법)",hovermode="x unified",plot_bgcolor="white",height=420,barmode="overlay")
        fig.update_xaxes(showgrid=False); fig.update_yaxes(title_text="억원",showgrid=True,gridcolor="#f0f0f0")
        st.plotly_chart(fig,use_container_width=True)

    with t3:
        st.subheader("FCF 브리지 (Waterfall)")
        periods = sorted(df_icf["period"].dropna().unique(),reverse=True)
        if not periods: st.info("데이터 없음")
        else:
            sel = st.selectbox("연도",periods,key="cf_wf_year")
            row = df_icf[df_icf["period"]==sel].iloc[0]
            items = [("EBITDA",row.get("ebitda",np.nan)),("NWC",row.get("nwc_movement",np.nan)),
                     ("Capex",row.get("capex_neg",np.nan)),("재무CF",row.get("cff_val",np.nan)),
                     ("기타",row.get("other_op",np.nan)),("FCF",row.get("fcf",np.nan))]
            vals = [i[1]/D if not(isinstance(i[1],float) and np.isnan(i[1])) else 0 for i in items]
            fig_wf = go.Figure(go.Waterfall(
                measure=["absolute","relative","relative","relative","relative","total"],
                x=[i[0] for i in items],y=vals,connector=dict(line=dict(color="#aaa")),
                increasing=dict(marker_color="#44BBA4"),decreasing=dict(marker_color="#C73E1D"),
                totals=dict(marker_color="#2E86AB"),texttemplate="%{y:,.0f}억",textposition="outside"))
            fig_wf.update_layout(title=f"{sel} FCF 브리지",plot_bgcolor="white",height=380,showlegend=False)
            fig_wf.update_xaxes(showgrid=False); fig_wf.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
            st.plotly_chart(fig_wf,use_container_width=True)
