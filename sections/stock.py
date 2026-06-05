import streamlit as st
import pandas as pd
import plotly.graph_objects as go

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


def _suffix(corp_cls):
    return ".KQ" if corp_cls == "K" else ".KS"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock(stock_code, corp_cls, period="3y"):
    if not YF_AVAILABLE or not stock_code: return pd.DataFrame()
    try:
        df = yf.download(stock_code+_suffix(corp_cls), period=period, progress=False, auto_adjust=True)
        return pd.DataFrame() if df.empty else df
    except Exception:
        return pd.DataFrame()


def render(stock_code, corp_cls, corp_name):
    st.subheader("① 주가 트렌드")
    if not stock_code or not stock_code.strip():
        st.info("비상장 기업이거나 주식 코드가 없습니다.",icon="ℹ️")
    elif not YF_AVAILABLE:
        st.warning("yfinance 설치 필요: pip install yfinance")
    else:
        period_opt = st.radio("조회 기간",["1y","3y","5y","max"],horizontal=True,key="stock_period")
        with st.spinner("주가 로딩 중..."):
            df_price = fetch_stock(stock_code, corp_cls, period_opt)
        if df_price.empty:
            st.warning(f"주가 데이터 없음 ({stock_code}{_suffix(corp_cls)})")
        else:
            cur = float(df_price["Close"].iloc[-1])
            chg = float((df_price["Close"].iloc[-1]/df_price["Close"].iloc[0]-1)*100)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("현재가",f"{cur:,.0f}원"); c2.metric("수익률",f"{chg:+.1f}%")
            c3.metric("52주최고",f"{float(df_price['High'].max()):,.0f}원")
            c4.metric("52주최저",f"{float(df_price['Low'].min()):,.0f}원")
            fig = go.Figure(go.Scatter(x=df_price.index,y=df_price["Close"],name="종가",mode="lines",
                                       line=dict(color="#2E86AB",width=1.5),fill="tozeroy",fillcolor="rgba(46,134,171,0.08)"))
            fig.update_layout(title=f"{corp_name} 주가",yaxis_title="원",hovermode="x unified",plot_bgcolor="white",height=380)
            fig.update_xaxes(showgrid=False); fig.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
            st.plotly_chart(fig,use_container_width=True)
    st.subheader("② Consensus 입력")
    default_data = pd.DataFrame({"항목":["매출액(억원)","영업이익(억원)","영업이익률(%)","EPS(원)"],"FY+1E":["","","",""],"FY+2E":["","","",""]})
    st.data_editor(default_data,use_container_width=True,num_rows="fixed",key="consensus_input")
