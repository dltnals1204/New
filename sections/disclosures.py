import streamlit as st
import pandas as pd
from utils.dart_api import search_disclosures


def render(corp_code, corp_name):
    t1, t2, t3 = st.tabs(["📋 주요 공시","📦 수주 잔고","🏭 Capacity"])
    with t1:
        st.subheader(f"{corp_name} 주요 공시")
        col1, col2 = st.columns([2,1])
        with col1: bgn_de = st.text_input("시작일 (YYYYMMDD)",value="20240101",key="disc_bgn")
        with col2: pblntf_ty = st.selectbox("공시유형",["전체","A","B","C"],key="disc_ty")
        ty_map = {"전체":None,"A":"A","B":"B","C":"C"}
        if st.button("공시 조회",key="disc_btn"):
            with st.spinner("조회 중..."):
                df_disc = search_disclosures(corp_code,bgn_de=bgn_de,pblntf_ty=ty_map[pblntf_ty])
            if df_disc.empty: st.info("조회된 공시가 없습니다.")
            else:
                df_show = df_disc[[c for c in ["rcept_dt","report_nm","flr_nm","rm"] if c in df_disc.columns]]
                df_show = df_show.rename(columns={"rcept_dt":"접수일","report_nm":"공시명","flr_nm":"제출인","rm":"비고"})
                st.dataframe(df_show,use_container_width=True,height=400)
    with t2:
        st.subheader("수주 잔고")
        st.info("📌 공시 원문 파싱 기능 개발 후 자동화 예정",icon="ℹ️")
        st.data_editor(pd.DataFrame({"기간":["","","",""],"수주잔고(억원)":["","","",""],"신규수주(억원)":["","","",""],"매출(억원)":["","","",""]}),use_container_width=True,num_rows="dynamic",key="orders_input")
    with t3:
        st.subheader("Capacity & Utilization")
        st.info("📌 공시 원문 파싱 기능 개발 후 자동화 예정",icon="ℹ️")
        st.data_editor(pd.DataFrame({"기간":["","","",""],"생산능력":["","","",""],"실제생산량":["","","",""],"가동률(%)":["","","",""]}),use_container_width=True,num_rows="dynamic",key="cap_input")
