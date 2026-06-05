import os
import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://opendart.fss.or.kr/api"
REPORT_CODES = {"Q1": "11013", "Q2": "11012", "Q3": "11014", "Annual": "11011"}


def _get(endpoint, params):
    api_key = os.environ.get("DART_API_KEY", "")
    params = {**params, "crtfc_key": api_key}
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("000", "013"):
        raise ValueError(f"DART API 오류: {data.get('message', '알 수 없는 오류')}")
    return data


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(keyword):
    data = _get("company.json", {"corp_name": keyword})
    if not data.get("list"):
        return pd.DataFrame()
    df = pd.DataFrame(data["list"])
    return df[["corp_code", "corp_name", "corp_cls", "stock_code"]].drop_duplicates()


@st.cache_data(ttl=3600, show_spinner=False)
def get_statements(corp_code, year, report_code, fs_div="CFS"):
    data = _get("fnlttSinglAcntAll.json", {
        "corp_code": corp_code, "bsns_year": str(year),
        "reprt_code": report_code, "fs_div": fs_div,
    })
    if not data.get("list"):
        return pd.DataFrame()
    df = pd.DataFrame(data["list"])
    for col in [c for c in df.columns if "amount" in c or "amt" in c]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False).str.strip()
            .replace({"": "0", "-": "0", "None": "0"}), errors="coerce"
        ).fillna(0)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def get_employees(corp_code, year, report_code):
    data = _get("empSttus.json", {"corp_code": corp_code, "bsns_year": str(year), "reprt_code": report_code})
    if not data.get("list"):
        return pd.DataFrame()
    return pd.DataFrame(data["list"])


@st.cache_data(ttl=3600, show_spinner=False)
def search_disclosures(corp_code, bgn_de=None, pblntf_ty=None):
    params = {"corp_code": corp_code, "page_count": "40"}
    if bgn_de: params["bgn_de"] = bgn_de
    if pblntf_ty: params["pblntf_ty"] = pblntf_ty
    data = _get("list.json", params)
    if not data.get("list"):
        return pd.DataFrame()
    return pd.DataFrame(data["list"])


def fetch_all_statements(corp_code, years, fs_div="CFS"):
    result = {}
    for year in years:
        for period, rcode in REPORT_CODES.items():
            df = get_statements(corp_code, year, rcode, fs_div)
            if not df.empty:
                result[(year, period)] = df
    return result


def fetch_employees_all(corp_code, years):
    rows = []
    for year in years:
        for period, rcode in REPORT_CODES.items():
            df = get_employees(corp_code, year, rcode)
            if not df.empty:
                df["year"] = year
                df["period"] = period
                rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
