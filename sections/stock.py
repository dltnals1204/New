import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


def _suffix(corp_cls: str) -> str:
    return ".KQ" if corp_cls == "K" else ".KS"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock(stock_code: str, corp_cls: str, period: str = "3y") -> pd.DataFrame:
    if not YF_AVAILABLE or not stock_code:
        return pd.DataFrame()
    ticker = stock_code + _suffix(corp_cls)
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def _price_chart(df_price: pd.DataFrame, corp_name: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_price.index, y=df_price["Close"],
        name="종가", mode="lines",
        line=dict(color="#2E86AB", width=1.5),
        fill="tozeroy", fillcolor="rgba(46,134,171,0.08)",
    ))
    fig.update_layout(
        title=f"{corp_name} 주가 추이",
        yaxis_title="주가 (원)", hovermode="x unified",
        plot_bgcolor="white", height=380,
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def _valuation_chart(df_val: pd.DataFrame):
    """PER / PBR 시계열"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=["PER (배)", "PBR (배)"], vertical_spacing=0.1)
    if "per" in df_val.columns:
        fig.add_trace(go.Scatter(x=df_val["date"], y=df_val["per"],
                                  name="PER", mode="lines+markers",
                                  line=dict(color="#2E86AB")), row=1, col=1)
    if "pbr" in df_val.columns:
        fig.add_trace(go.Scatter(x=df_val["date"], y=df_val["pbr"],
                                  name="PBR", mode="lines+markers",
                                  line=dict(color="#A23B72")), row=2, col=1)
    fig.update_layout(plot_bgcolor="white", height=450, showlegend=False,
                      hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


def render(stock_code: str, corp_cls: str, corp_name: str):
    # ── 주가 데이터 ────────────────────────────────────────────────────────
    st.subheader("① 주가 트렌드")

    if not stock_code or stock_code.strip() == "":
        st.info("비상장 기업이거나 주식 코드 정보가 없습니다.", icon="ℹ️")
    elif not YF_AVAILABLE:
        st.warning("yfinance 라이브러리가 설치되지 않았습니다. `pip install yfinance`")
    else:
        period_opt = st.radio("조회 기간", ["1y", "3y", "5y", "max"],
                               horizontal=True, key="stock_period")
        with st.spinner("주가 데이터 로딩 중..."):
            df_price = fetch_stock(stock_code, corp_cls, period_opt)

        if df_price.empty:
            st.warning(f"주가 데이터를 가져올 수 없습니다. (코드: {stock_code}{_suffix(corp_cls)})")
        else:
            # 기본 지표
            cur_price = float(df_price["Close"].iloc[-1])
            chg_1y    = float((df_price["Close"].iloc[-1] / df_price["Close"].iloc[0] - 1) * 100)
            hi_52     = float(df_price["High"].max())
            lo_52     = float(df_price["Low"].min())

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"{cur_price:,.0f}원")
            c2.metric("기간 수익률", f"{chg_1y:+.1f}%")
            c3.metric("52주 최고", f"{hi_52:,.0f}원")
            c4.metric("52주 최저", f"{lo_52:,.0f}원")

            st.plotly_chart(_price_chart(df_price, corp_name), use_container_width=True)

    # ── Valuation ────────────────────────────────────────────────────────
    st.subheader("② 시계열 Valuation (PER / PBR)")
    st.info(
        "📌 시계열 PER/PBR은 **주가 × 발행주식수 / EPS(BPS)** 계산이 필요하며, "
        "발행주식수 및 EPS/BPS 시계열 데이터 연동 후 자동 산출됩니다.",
        icon="ℹ️",
    )

    # ── Consensus ─────────────────────────────────────────────────────────
    st.subheader("③ Consensus 기반 Forward Valuation")
    st.markdown("""
    증권사 컨센서스 수치를 아래 표에 직접 입력하면 Forward PER이 자동 계산됩니다.

    > 컨센서스 출처: FnGuide, Bloomberg, 각 증권사 리포트
    """)

    with st.expander("📝 컨센서스 데이터 입력 (수기)", expanded=True):
        fy_cols = ["FY+1E", "FY+2E"]
        default_data = pd.DataFrame({
            "항목":     ["매출액 (억원)", "영업이익 (억원)", "영업이익률 (%)", "EPS (원)"],
            "FY+1E":   ["", "", "", ""],
            "FY+2E":   ["", "", "", ""],
        })
        edited = st.data_editor(default_data, use_container_width=True,
                                 num_rows="fixed", key="consensus_input",
                                 column_config={
                                     "항목": st.column_config.TextColumn("항목", disabled=True),
                                     "FY+1E": st.column_config.TextColumn("FY+1E"),
                                     "FY+2E": st.column_config.TextColumn("FY+2E"),
                                 })

        if stock_code and not df_price.empty if YF_AVAILABLE and stock_code else False:
            cur_p = float(df_price["Close"].iloc[-1])
            for fy in fy_cols:
                eps_row = edited[edited["항목"] == "EPS (원)"][fy].values
                if len(eps_row) > 0 and eps_row[0]:
                    try:
                        eps = float(str(eps_row[0]).replace(",", ""))
                        fwd_per = cur_p / eps if eps != 0 else np.nan
                        st.metric(f"Forward PER ({fy})", f"{fwd_per:.1f}x" if not np.isnan(fwd_per) else "—")
                    except (ValueError, TypeError):
                        pass
