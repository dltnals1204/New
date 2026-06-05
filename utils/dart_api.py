import io
import os
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://opendart.fss.or.kr/api"
REPORT_CODES = {"Q1": "11013", "Q2": "11012", "Q3": "11014", "Annual": "11011"}


def _api_key():
    return os.environ.get("DART_API_KEY", "")


def _get(endpoint, params):
    params = {**params, "crtfc_key": _api_key()}
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("000", "013"):
        raise ValueError(f"DART API 오류: {data.get('message', '알 수 없는 오류')}")
    return data


@st.cache_data(ttl=86400, show_spinner=False)
def _load_corp_codes() -> pd.DataFrame:
    """DART 전체 기업 목록 다운로드 (corpCode.xml ZIP)"""
    resp = requests.get(
        f"{BASE_URL}/corpCode.xml",
        params={"crtfc_key": _api_key()},
        timeout=60,
    )
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read("CORPCODE.xml")
    root = ET.fromstring(xml_bytes)
    rows = [
        {
            "corp_code":  item.findtext("corp_code", ""),
            "corp_name":  item.findtext("corp_name", ""),
            "stock_code": item.findtext("stock_code", "").strip(),
        }
        for item in root.findall("list")
    ]
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(keyword: str) -> pd.DataFrame:
    df = _load_corp_codes()
    result = df[df["corp_name"].str.contains(keyword, na=False, case=False)].copy()
    # stock_code 없으면 비상장
    result["corp_cls"] = result["stock_code"].apply(lambda x: "Y" if x else "")
    return result.reset_index(drop=True)


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
    data = _get("empSttus.json", {
        "corp_code": corp_code, "bsns_year": str(year), "reprt_code": report_code
    })
    if not data.get("list"):
        return pd.DataFrame()
    return pd.DataFrame(data["list"])


@st.cache_data(ttl=3600, show_spinner=False)
def search_disclosures(corp_code, bgn_de=None, pblntf_ty=None):
    params = {"corp_code": corp_code, "page_count": "40"}
    if bgn_de:
        params["bgn_de"] = bgn_de
    if pblntf_ty:
        params["pblntf_ty"] = pblntf_ty
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
