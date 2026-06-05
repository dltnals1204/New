import os
import requests
import pandas as pd
import streamlit as st
from typing import Optional

DART_API_KEY = os.environ.get("DART_API_KEY", "")
BASE_URL = "https://opendart.fss.or.kr/api"

REPORT_CODES = {
    "Q1": "11013",
    "Q2": "11012",
    "Q3": "11014",
    "Annual": "11011",
}


def _get(endpoint: str, params: dict) -> dict:
    params = {**params, "crtfc_key": DART_API_KEY}
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("000", "013"):
        raise ValueError(f"DART API 오류: {data.get('message', '알 수 없는 오류')}")
    return data


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(keyword: str) -> pd.DataFrame:
    data = _get("company.json", {"corp_name": keyword})
    if not data.get("list"):
        return pd.DataFrame()
    df = pd.DataFrame(data["list"])
    return df[["corp_code", "corp_name", "corp_cls", "stock_code"]].drop_duplicates()


@st.cache_data(ttl=3600, show_spinner=False)
def get_statements(
    corp_code: str,
    year: int,
    report_code: str,
    fs_div: str = "CFS",
) -> pd.DataFrame:
    """단일기업 전체 재무제표 (fnlttSinglAcntAll)"""
    data = _get(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
            "fs_div": fs_div,
        },
    )
    if not data.get("list"):
        return pd.DataFrame()
    df = pd.DataFrame(data["list"])
    amount_cols = [c for c in df.columns if "amount" in c or "amt" in c]
    for col in amount_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
            .replace({"": "0", "-": "0", "None": "0"})
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def fetch_all_statements(
    corp_code: str,
    years: list[int],
    fs_div: str = "CFS",
) -> dict:
    """
    여러 연도의 분기/연도별 재무제표를 한번에 수집.
    반환: {(year, period): DataFrame}
        period in ['Q1','Q2','Q3','Annual']
    """
    result = {}
    for year in years:
        for period, rcode in REPORT_CODES.items():
            df = get_statements(corp_code, year, rcode, fs_div)
            if not df.empty:
                result[(year, period)] = df
    return result
