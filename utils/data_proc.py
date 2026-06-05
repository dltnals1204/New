"""
재무 데이터 처리 유틸리티
- DART 계정명 → 표준 항목 매핑
- 누적 분기 → 실제 분기 변환
- 파생 지표 계산 (EBITDA, 성장률, NWC)
"""

import pandas as pd
import numpy as np

# ── 계정명 키워드 매핑 ───────────────────────────────────────────────────────
ACCOUNT_MAP = {
    "revenue":         ["수익(매출액)", "매출액", "영업수익", "순매출액"],
    "cogs":            ["매출원가", "영업비용"],
    "gross_profit":    ["매출총이익"],
    "sga":             ["판매비와관리비", "판매관리비", "영업비용합계"],
    "op_income":       ["영업이익"],
    "depreciation":    ["감가상각비", "유형자산감가상각비"],
    "amortization":    ["무형자산상각비", "상각비"],
    "trade_rec":       ["매출채권", "매출채권 및 기타채권", "매출채권및기타채권"],
    "inventory":       ["재고자산"],
    "trade_pay":       ["매입채무", "매입채무 및 기타채무", "매입채무및기타채무"],
}


def _find_account(df: pd.DataFrame, keywords: list[str]) -> float:
    """계정명 키워드로 thstrm_amount 합산"""
    mask = df["account_nm"].astype(str).apply(
        lambda x: any(kw in x for kw in keywords)
    )
    matched = df[mask]
    if matched.empty:
        return np.nan
    # ord가 낮은 (상위) 행 우선 — 합계 행 하나만 취함
    matched = matched.sort_values("ord").iloc[0]
    return float(matched.get("thstrm_amount", 0))


def extract_row(df: pd.DataFrame, key: str) -> float:
    keywords = ACCOUNT_MAP.get(key, [])
    return _find_account(df, keywords)


def build_period_series(statements: dict, fs_map: dict = None) -> pd.DataFrame:
    """
    {(year, period): stmt_df} → 기간별 재무항목 DataFrame (누적 기준 그대로)
    fs_map: sj_div별 필터 {'IS': is_df, 'BS': bs_df, 'CF': cf_df}
    """
    rows = []
    for (year, period), df in statements.items():
        if df.empty:
            continue
        is_df = df[df["sj_div"] == "IS"]
        bs_df = df[df["sj_div"] == "BS"]
        cf_df = df[df["sj_div"] == "CF"]

        row = {
            "year": year,
            "period": period,
            "revenue":       extract_row(is_df, "revenue"),
            "cogs":          extract_row(is_df, "cogs"),
            "gross_profit":  extract_row(is_df, "gross_profit"),
            "sga":           extract_row(is_df, "sga"),
            "op_income":     extract_row(is_df, "op_income"),
            "depreciation":  extract_row(cf_df, "depreciation"),
            "amortization":  extract_row(cf_df, "amortization"),
            "trade_rec":     extract_row(bs_df, "trade_rec"),
            "inventory":     extract_row(bs_df, "inventory"),
            "trade_pay":     extract_row(bs_df, "trade_pay"),
        }
        # Gross profit 역산
        if np.isnan(row["gross_profit"]) and not (np.isnan(row["revenue"]) or np.isnan(row["cogs"])):
            row["gross_profit"] = row["revenue"] - row["cogs"]

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df_all = pd.DataFrame(rows)
    df_all = df_all.sort_values(["year", "period"], key=lambda s: s.map(
        lambda x: x if isinstance(x, int) else {"Q1": 1, "Q2": 2, "Q3": 3, "Annual": 4}.get(x, 99)
    )).reset_index(drop=True)
    return df_all


PERIOD_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Annual": 4}
PERIOD_QTR_QUARTERS = {"Q1": 1, "Q2": 2, "Q3": 3}  # 누적 분기수


def cumulative_to_actual(df_cum: pd.DataFrame) -> pd.DataFrame:
    """
    DART 분기보고서는 YTD 누적값을 제공함.
    Q1: actual = Q1_cum
    Q2: actual = Q2_cum - Q1_cum
    Q3: actual = Q3_cum - Q2_cum
    Q4: actual = Annual - Q3_cum
    수치 컬럼에만 적용 (year, period 제외)
    """
    numeric_cols = [c for c in df_cum.columns if c not in ("year", "period")]
    rows = []
    for year, grp in df_cum.groupby("year"):
        grp = grp.set_index("period")
        for period in ["Q1", "Q2", "Q3", "Annual"]:
            if period not in grp.index:
                continue
            row = {"year": year, "period": period}
            for col in numeric_cols:
                cur = grp.loc[period, col]
                if period == "Q1":
                    row[col] = cur
                elif period == "Q2":
                    prev = grp.loc["Q1", col] if "Q1" in grp.index else np.nan
                    row[col] = cur - prev if not np.isnan(prev) else cur
                elif period == "Q3":
                    prev = grp.loc["Q2", col] if "Q2" in grp.index else np.nan
                    row[col] = cur - prev if not np.isnan(prev) else cur
                elif period == "Annual":
                    prev = grp.loc["Q3", col] if "Q3" in grp.index else np.nan
                    row[col] = cur - prev if not np.isnan(prev) else cur
            rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def make_quarter_df(df_cum: pd.DataFrame) -> pd.DataFrame:
    """분기별 실적 DataFrame (Q1~Q4)"""
    df_act = cumulative_to_actual(df_cum)
    df_q = df_act[df_act["period"] != "Annual"].copy()
    _qmap = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    df_q["period"] = df_q.apply(
        lambda r: f"{r['year']}Q{_qmap.get(r['period'], r['period'])}",
        axis=1,
    )
    # Q4 → Annual에서 파생
    df_q4 = df_act[df_act["period"] == "Annual"].copy()
    df_q4["period"] = df_q4["year"].astype(str) + "Q4"
    df_q = pd.concat([df_q, df_q4], ignore_index=True)
    df_q = df_q.sort_values("period").reset_index(drop=True)
    return df_q


def make_annual_df(df_cum: pd.DataFrame) -> pd.DataFrame:
    """연도별 실적 DataFrame"""
    df_a = df_cum[df_cum["period"] == "Annual"].copy()
    df_a["period"] = df_a["year"].astype(str)
    return df_a.reset_index(drop=True)


def add_ebitda(df: pd.DataFrame) -> pd.DataFrame:
    """EBITDA = 영업이익 + 감가상각비 + 무형자산상각비"""
    df = df.copy()
    da = df["depreciation"].fillna(0) + df["amortization"].fillna(0)
    df["ebitda"] = df["op_income"].fillna(0) + da
    df["ebitda"] = df["ebitda"].where(da > 0, np.nan)  # D&A 없으면 NaN
    return df


def add_margins(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rev = df["revenue"].replace(0, np.nan)
    df["gross_margin"] = df["gross_profit"] / rev * 100
    df["op_margin"]    = df["op_income"]    / rev * 100
    df["ebitda_margin"] = df.get("ebitda", pd.Series(np.nan, index=df.index)) / rev * 100
    df["sga_pct"]      = df["sga"]          / rev * 100
    return df


def add_growth(df: pd.DataFrame) -> pd.DataFrame:
    """QoQ, YoY 성장률 추가 (period 컬럼이 'YYYYQn' 형태인 분기 DF에 적용)"""
    df = df.copy().sort_values("period").reset_index(drop=True)
    df["qoq"] = df["revenue"].pct_change(1) * 100
    df["yoy"] = df["revenue"].pct_change(4) * 100
    return df


def add_annual_yoy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("period").reset_index(drop=True)
    df["yoy"] = df["revenue"].pct_change(1) * 100
    return df


def extract_sga_detail(statements: dict) -> pd.DataFrame:
    """
    SG&A 세부 항목 추출.
    DART IS 항목 중 판매관리비 하위 계정을 추출.
    """
    rows = []
    for (year, period), df in statements.items():
        if df.empty:
            continue
        is_df = df[df["sj_div"] == "IS"].copy()
        # 판매관리비 총계 ord 찾기
        sga_mask = is_df["account_nm"].astype(str).apply(
            lambda x: any(kw in x for kw in ACCOUNT_MAP["sga"])
        )
        sga_rows = is_df[sga_mask].sort_values("ord")
        if sga_rows.empty:
            continue
        sga_ord = int(sga_rows.iloc[0]["ord"])
        # 하위 항목: ord가 sga_ord 다음부터 다음 대분류 전까지
        is_df["ord"] = pd.to_numeric(is_df["ord"], errors="coerce")
        sub = is_df[(is_df["ord"] > sga_ord) & (is_df["ord"] < sga_ord + 100)]
        # 진짜 세부항목인지 확인 (account_nm이 비어있지 않고 금액이 있는 것)
        sub = sub[sub["thstrm_amount"] != 0]
        for _, r in sub.iterrows():
            rows.append({
                "year": year,
                "period": period,
                "account": r["account_nm"],
                "amount": float(r.get("thstrm_amount", 0)),
            })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def calc_nwc(df_cum: pd.DataFrame) -> pd.DataFrame:
    """
    연도별 NWC 회전일 계산.
    DSO = (매출채권 / 매출액) * 365
    DIO = (재고자산 / 매출원가) * 365
    DPO = (매입채무 / 매출원가) * 365
    CCC = DSO + DIO - DPO
    """
    df_a = make_annual_df(df_cum).copy()
    rev  = df_a["revenue"].replace(0, np.nan)
    cogs = df_a["cogs"].replace(0, np.nan)
    df_a["dso"] = df_a["trade_rec"]  / rev  * 365
    df_a["dio"] = df_a["inventory"]  / cogs * 365
    df_a["dpo"] = df_a["trade_pay"]  / cogs * 365
    df_a["ccc"] = df_a["dso"] + df_a["dio"] - df_a["dpo"]
    return df_a


def detect_ytd(df_cum: pd.DataFrame) -> tuple[int | None, str | None]:
    """최신 데이터가 온기(Annual)가 아닌 경우 (year, period) 반환"""
    if df_cum.empty:
        return None, None
    latest = df_cum.sort_values(
        ["year", "period"],
        key=lambda s: s.map(lambda x: x if isinstance(x, int) else PERIOD_ORDER.get(x, 0))
    ).iloc[-1]
    if latest["period"] != "Annual":
        return int(latest["year"]), latest["period"]
    return None, None
