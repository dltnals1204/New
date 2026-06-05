import pandas as pd
import numpy as np

ACCOUNT_MAP = {
    "revenue":       ["수익(매출액)", "매출액", "영업수익", "순매출액"],
    "cogs":          ["매출원가", "영업비용"],
    "gross_profit":  ["매출총이익"],
    "sga":           ["판매비와관리비", "판매관리비", "영업비용합계"],
    "op_income":     ["영업이익"],
    "net_income":    ["당기순이익", "분기순이익"],
    "cfo":           ["영업활동현금흐름", "영업활동으로인한현금흐름", "영업활동으로 인한 현금흐름"],
    "cfi":           ["투자활동현금흐름", "투자활동으로인한현금흐름", "투자활동으로 인한 현금흐름"],
    "cff":           ["재무활동현금흐름", "재무활동으로인한현금흐름", "재무활동으로 인한 현금흐름"],
    "capex":         ["유형자산의취득", "유형자산취득"],
    "net_cash_chg":  ["현금및현금성자산의순증가", "현금및현금성자산의증가(감소)", "현금의증가(감소)"],
    "depreciation":  ["감가상각비", "유형자산감가상각비"],
    "amortization":  ["무형자산상각비", "상각비"],
    "cash":          ["현금및현금성자산"],
    "trade_rec":     ["매출채권", "매출채권 및 기타채권", "매출채권및기타채권"],
    "ar_other":      ["미수금", "미수수익"],
    "inventory":     ["재고자산"],
    "trade_pay":     ["매입채무", "매입채무 및 기타채무", "매입채무및기타채무"],
    "ap_other":      ["미지급금", "미지급비용"],
    "total_assets":  ["자산총계", "자산 총계"],
    "total_equity":  ["자본총계", "자본 총계"],
    "total_liab":    ["부채총계", "부채 총계"],
    "st_debt":       ["단기차입금", "유동성장기부채"],
    "lt_debt":       ["장기차입금", "사채"],
}

PERIOD_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Annual": 4}


def _find_account(df, keywords):
    if df.empty: return np.nan
    mask = df["account_nm"].astype(str).apply(lambda x: any(kw in x for kw in keywords))
    matched = df[mask]
    if matched.empty: return np.nan
    return float(matched.sort_values("ord").iloc[0].get("thstrm_amount", 0))


def extract_row(df, key):
    return _find_account(df, ACCOUNT_MAP.get(key, []))


def build_period_series(statements):
    rows = []
    for (year, period), df in statements.items():
        if df.empty: continue
        is_df = df[df["sj_div"] == "IS"]
        bs_df = df[df["sj_div"] == "BS"]
        cf_df = df[df["sj_div"] == "CF"]
        row = {"year": year, "period": period,
               "revenue": extract_row(is_df,"revenue"), "cogs": extract_row(is_df,"cogs"),
               "gross_profit": extract_row(is_df,"gross_profit"), "sga": extract_row(is_df,"sga"),
               "op_income": extract_row(is_df,"op_income"), "net_income": extract_row(is_df,"net_income"),
               "depreciation": extract_row(cf_df,"depreciation"), "amortization": extract_row(cf_df,"amortization"),
               "cfo": extract_row(cf_df,"cfo"), "cfi": extract_row(cf_df,"cfi"),
               "cff": extract_row(cf_df,"cff"), "capex": extract_row(cf_df,"capex"),
               "net_cash_chg": extract_row(cf_df,"net_cash_chg"),
               "cash": extract_row(bs_df,"cash"), "trade_rec": extract_row(bs_df,"trade_rec"),
               "ar_other": extract_row(bs_df,"ar_other"), "inventory": extract_row(bs_df,"inventory"),
               "trade_pay": extract_row(bs_df,"trade_pay"), "ap_other": extract_row(bs_df,"ap_other"),
               "total_assets": extract_row(bs_df,"total_assets"), "total_equity": extract_row(bs_df,"total_equity"),
               "total_liab": extract_row(bs_df,"total_liab"), "st_debt": extract_row(bs_df,"st_debt"),
               "lt_debt": extract_row(bs_df,"lt_debt")}
        if np.isnan(row["gross_profit"]) and not (np.isnan(row["revenue"]) or np.isnan(row["cogs"])):
            row["gross_profit"] = row["revenue"] - row["cogs"]
        if not np.isnan(row["capex"]) and row["capex"] < 0:
            row["capex"] = abs(row["capex"])
        rows.append(row)
    if not rows: return pd.DataFrame()
    df_all = pd.DataFrame(rows)
    df_all = df_all.sort_values(["year","period"], key=lambda s: s.map(
        lambda x: x if isinstance(x, int) else {"Q1":1,"Q2":2,"Q3":3,"Annual":4}.get(x,99)
    )).reset_index(drop=True)
    return df_all


IS_CF_COLS = ["revenue","cogs","gross_profit","sga","op_income","net_income",
              "depreciation","amortization","cfo","cfi","cff","capex","net_cash_chg"]
BS_COLS    = ["cash","trade_rec","ar_other","inventory","trade_pay","ap_other",
              "total_assets","total_equity","total_liab","st_debt","lt_debt"]


def _valid(v):
    return not (isinstance(v, float) and np.isnan(v))


def cumulative_to_actual(df_cum):
    rows = []
    for year, grp in df_cum.groupby("year"):
        grp = grp.set_index("period")
        for period in ["Q1","Q2","Q3","Annual"]:
            if period not in grp.index: continue
            row = {"year": year, "period": period}
            for col in IS_CF_COLS:
                if col not in grp.columns: row[col] = np.nan; continue
                cur = grp.loc[period, col]
                if period == "Q1": row[col] = cur
                elif period == "Q2":
                    prev = grp.loc["Q1",col] if "Q1" in grp.index else np.nan
                    row[col] = cur - prev if _valid(prev) else cur
                elif period == "Q3":
                    prev = grp.loc["Q2",col] if "Q2" in grp.index else np.nan
                    row[col] = cur - prev if _valid(prev) else cur
                elif period == "Annual":
                    prev = grp.loc["Q3",col] if "Q3" in grp.index else np.nan
                    row[col] = cur - prev if _valid(prev) else cur
            for col in BS_COLS:
                row[col] = grp.loc[period,col] if col in grp.columns else np.nan
            rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def make_quarter_df(df_cum):
    df_act = cumulative_to_actual(df_cum)
    df_q = df_act[df_act["period"] != "Annual"].copy()
    _qmap = {"Q1":1,"Q2":2,"Q3":3}
    df_q["period"] = df_q.apply(lambda r: f"{r['year']}Q{_qmap.get(r['period'],r['period'])}", axis=1)
    df_q4 = df_act[df_act["period"] == "Annual"].copy()
    df_q4["period"] = df_q4["year"].astype(str) + "Q4"
    return pd.concat([df_q, df_q4], ignore_index=True).sort_values("period").reset_index(drop=True)


def make_annual_df(df_cum):
    df_a = df_cum[df_cum["period"] == "Annual"].copy()
    df_a["period"] = df_a["year"].astype(str)
    return df_a.reset_index(drop=True)


def add_ebitda(df):
    df = df.copy()
    da = df["depreciation"].fillna(0) + df["amortization"].fillna(0)
    df["ebitda"] = df["op_income"].fillna(0) + da
    df["ebitda"] = df["ebitda"].where(da > 0, np.nan)
    return df


def add_margins(df):
    df = df.copy()
    rev = df["revenue"].replace(0, np.nan)
    df["gross_margin"]  = df["gross_profit"] / rev * 100
    df["op_margin"]     = df["op_income"]    / rev * 100
    df["ebitda_margin"] = df.get("ebitda", pd.Series(np.nan, index=df.index)) / rev * 100
    df["sga_pct"]       = df["sga"]          / rev * 100
    return df


def add_growth(df):
    df = df.copy().sort_values("period").reset_index(drop=True)
    df["qoq"] = df["revenue"].pct_change(1) * 100
    df["yoy"] = df["revenue"].pct_change(4) * 100
    return df


def add_annual_yoy(df):
    df = df.copy().sort_values("period").reset_index(drop=True)
    df["yoy"] = df["revenue"].pct_change(1) * 100
    return df


def detect_ytd(df_cum):
    if df_cum.empty: return None, None
    latest = df_cum.sort_values(["year","period"],
        key=lambda s: s.map(lambda x: x if isinstance(x,int) else PERIOD_ORDER.get(x,0))).iloc[-1]
    if latest["period"] != "Annual":
        return int(latest["year"]), latest["period"]
    return None, None


def extract_sga_detail(statements):
    rows = []
    for (year, period), df in statements.items():
        if df.empty: continue
        is_df = df[df["sj_div"] == "IS"].copy()
        sga_mask = is_df["account_nm"].astype(str).apply(
            lambda x: any(kw in x for kw in ACCOUNT_MAP["sga"]))
        sga_rows = is_df[sga_mask].sort_values("ord")
        if sga_rows.empty: continue
        sga_ord = int(sga_rows.iloc[0]["ord"])
        is_df["ord"] = pd.to_numeric(is_df["ord"], errors="coerce")
        sub = is_df[(is_df["ord"] > sga_ord) & (is_df["ord"] < sga_ord + 100)]
        sub = sub[sub["thstrm_amount"] != 0]
        for _, r in sub.iterrows():
            rows.append({"year":year,"period":period,"account":r["account_nm"],
                         "amount":float(r.get("thstrm_amount",0))})
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def calc_nwc(df_cum):
    df_a = make_annual_df(df_cum).copy()
    rev  = df_a["revenue"].replace(0, np.nan)
    cogs = df_a["cogs"].replace(0, np.nan)
    df_a["receivables"] = (df_a["trade_rec"].fillna(0) + df_a["ar_other"].fillna(0)).replace(0, np.nan)
    df_a["payables"]    = (df_a["trade_pay"].fillna(0) + df_a["ap_other"].fillna(0)).replace(0, np.nan)
    df_a["inventory_v"] = df_a["inventory"].fillna(0).replace(0, np.nan)
    df_a["dso"] = df_a["receivables"] / rev  * 365
    df_a["dio"] = df_a["inventory_v"] / cogs * 365
    df_a["dpo"] = df_a["payables"]    / cogs * 365
    df_a["ccc"] = df_a["dso"] + df_a["dio"] - df_a["dpo"]
    df_a["ar_turnover"]  = rev  / df_a["receivables"]
    df_a["inv_turnover"] = cogs / df_a["inventory_v"]
    df_a["ap_turnover"]  = cogs / df_a["payables"]
    return df_a


def calc_nwc_movement(df_cum):
    df_a = make_annual_df(df_cum).copy()
    df_a["receivables"] = df_a["trade_rec"].fillna(0) + df_a["ar_other"].fillna(0)
    df_a["payables"]    = df_a["trade_pay"].fillna(0) + df_a["ap_other"].fillna(0)
    df_a["inventory_v"] = df_a["inventory"].fillna(0)
    df_a = df_a.sort_values("period").reset_index(drop=True)
    df_a["d_receivables"] = df_a["receivables"].diff()
    df_a["d_inventory"]   = df_a["inventory_v"].diff()
    df_a["d_payables"]    = df_a["payables"].diff()
    df_a["nwc_movement"]  = df_a["d_payables"] - df_a["d_receivables"] - df_a["d_inventory"]
    return df_a


def build_indirect_cashflow(df_cum):
    df_act = make_annual_df(df_cum).copy()
    nwc = calc_nwc_movement(df_cum)[["period","nwc_movement"]]
    df = df_act.merge(nwc, on="period", how="left")
    df["da"] = df["depreciation"].fillna(0) + df["amortization"].fillna(0)
    df["ebitda"] = df["op_income"].fillna(0) + df["da"]
    df["ebitda"] = df["ebitda"].where(df["da"] > 0, np.nan)
    df["ebitda_after_nwc"] = df["ebitda"] + df["nwc_movement"].fillna(0)
    df["ccr_nwc"]  = df["ebitda_after_nwc"] / df["ebitda"].replace(0,np.nan) * 100
    df["capex_neg"] = -df["capex"].fillna(0)
    df["cff_val"]   = df["cff"].fillna(0)
    df["fcf_base"]  = df["ebitda_after_nwc"] + df["capex_neg"] + df["cff_val"]
    df["other_op"]  = df["net_cash_chg"].fillna(np.nan) - df["fcf_base"]
    df["fcf"]       = df["fcf_base"] + df["other_op"].fillna(0)
    df["ccr_fcf"]   = df["fcf"] / df["ebitda"].replace(0,np.nan) * 100
    return df


def calc_metrics(df_cum):
    df = make_annual_df(df_cum).copy()
    equity = df["total_equity"].replace(0, np.nan)
    assets = df["total_assets"].replace(0, np.nan)
    liab   = df["total_liab"].replace(0, np.nan)
    df["roe"]   = df["net_income"] / equity * 100
    df["roa"]   = df["net_income"] / assets * 100
    df["nopat"] = df["op_income"] * 0.78
    net_debt = (df["st_debt"].fillna(0) + df["lt_debt"].fillna(0)) - df["cash"].fillna(0)
    df["roic"]      = df["nopat"] / (equity + net_debt).replace(0,np.nan) * 100
    df["de_ratio"]  = liab / equity * 100
    df["debt_ratio"]= liab / assets * 100
    df["net_debt"]  = net_debt
    return df
