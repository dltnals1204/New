import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render(corp_name):
    st.subheader("📝 Peer 기업 수기 입력")
    default_peers = pd.DataFrame({"기업명":[corp_name,"","",""],"매출액(억원)":["","","",""],
                                   "영업이익률(%)":["","","",""],"매출총이익률(%)":["","","",""]})
    edited = st.data_editor(default_peers,use_container_width=True,num_rows="dynamic",key="peer_input")
    if st.button("📊 차트 생성",key="peer_chart_btn"):
        try:
            df = edited.copy()
            for col in ["매출총이익률(%)","영업이익률(%)"]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",",""),errors="coerce")
            df = df[df["기업명"].str.strip()!=""].dropna(subset=["기업명"])
            if df.empty: st.warning("데이터 입력 필요")
            else:
                fig = go.Figure()
                for _, row in df.iterrows():
                    fig.add_trace(go.Bar(name=row["기업명"],x=["매출총이익률(%)","영업이익률(%)"],
                                         y=[row.get("매출총이익률(%)"),row.get("영업이익률(%)")]))
                fig.update_layout(title="Peer 비교",barmode="group",plot_bgcolor="white",height=400,yaxis_title="%")
                st.plotly_chart(fig,use_container_width=True)
        except Exception as e:
            st.error(f"오류: {e}")
