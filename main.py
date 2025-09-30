import streamlit as st
import pandas as pd
import yfinance as yf
import os
import pandas_ta as ta
import google.generativeai as genai

@st.cache_data
def initialize_model():
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("錯誤：找不到 GOOGLE_API_KEY 環境變數。")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        return model
    except Exception as e:
        st.error(f"❌ AI 模型初始化失敗：{e}")
        return None

@st.cache_data
def get_stock_data(ticker):
    try:
        stock_ticker = f"{ticker}.TW"
        stock = yf.Ticker(stock_ticker)
        info = stock.info
        hist = stock.history(period="1y")
        if hist.empty:
            return None, None, None
        
        financials = stock.financials
        
        hist.ta.sma(length=50, append=True)
        hist.ta.sma(length=200, append=True)
        hist.ta.rsi(length=14, append=True)
        
        return info, hist, financials
    except Exception as e:
        st.error(f"抓取 {ticker} 股價資訊時發生錯誤: {e}")
        return None, None

def get_ai_overall_analysis(model, ticker, news_sentiment, news_summary, info, hist):
    st.subheader("🤖 AI 總體健診")

    if st.button(f"產生 {ticker} 的 AI 總體健診報告"):
        with st.spinner("AI 正在深度分析所有數據，請稍候..."):
            try:
                latest_data = hist.iloc[-1]
                current_price = latest_data['Close']
                sma50 = latest_data['SMA_50']
                sma200 = latest_data['SMA_200']
                rsi_value = latest_data['RSI_14']
                pe_ratio = info.get('trailingPE', 'N/A')
                pb_ratio = info.get('priceToBook', 'N/A')
                held_percent_institutions = info.get('heldPercentInstitutions', 0)
                
                price_vs_sma50 = "高於" if current_price > sma50 else "低於"
                price_vs_sma200 = "高於" if current_price > sma200 else "低於"

                mega_prompt = f"""
                請扮演一位資深、客觀、數據驅動的避險基金分析師。
                你的任務是根據我提供的多面向數據，為股票 {ticker} 生成一份均衡的「看漲理由」與「看跌理由」分析報告。
                請嚴格僅使用我提供的數據，不要引入任何外部資訊或個人觀點。
                分析應簡潔、專業，並以條列式呈現。不要提供任何直接的投資建議。

                [數據點]
                1.  消息面分析：
                    -   相關新聞情緒：「{news_sentiment}」
                    -   新聞摘要：{news_summary}

                2.  技術面分析：
                    -   目前股價：{current_price:.2f}
                    -   股價與50日均線關係：目前股價「{price_vs_sma50}」50日線 ({sma50:.2f})
                    -   股價與200日均線關係：目前股價「{price_vs_sma200}」200日線 ({sma200:.2f})
                    -   14日 RSI 指數：{rsi_value:.2f}

                3.  基本面分析：
                    -   本益比 (P/E Ratio)：{pe_ratio}
                    -   股價淨值比 (P/B Ratio)：{pb_ratio}

                4.  籌碼面分析：
                    -   機構持股比例：{held_percent_institutions:.2%}

                請根據以上數據，生成你的分析報告。
                """

                response = model.generate_content(mega_prompt)
                
                bull_case = "找不到看漲理由"
                bear_case = "找不到看跌理由"

                if "看漲理由" in response.text and "看跌理由" in response.text:
                    parts = response.text.split("看跌理由")
                    bull_case = parts[0].replace("看漲理由", "").strip()
                    bear_case = parts[1].strip()
                else:
                    st.warning("AI 回應格式非預期，顯示原始文字。")
                    st.write(response.text)

                bull_col, bear_col = st.columns(2)
                with bull_col:
                    st.markdown("#### 🐂 看漲理由 (Bull Case)")
                    st.success(bull_case)
                with bear_col:
                    st.markdown("#### 🐻 看跌理由 (Bear Case)")
                    st.error(bear_case)

            except Exception as e:
                st.error(f"產生 AI 總體健診時發生錯誤：{e}")


def display_quantitative_data(ticker, info, hist, financials):
    st.subheader(f"📈 {ticker} 量化分析")
    st.markdown("#### 技術面")
    latest_data = hist.iloc[-1]
    current_price = latest_data['Close']
    previous_close = hist.iloc[-2]['Close']
    price_change = current_price - previous_close
    price_change_percent = (price_change / previous_close) * 100
    sub_col1, sub_col2 = st.columns(2)
    sub_col1.metric("目前股價", f"{current_price:.2f}", f"{price_change:.2f} ({price_change_percent:.2f}%)")
    rsi_value = latest_data['RSI_14']
    sub_col2.metric("14日 RSI", f"{rsi_value:.2f}")
    st.line_chart(hist[['Close', 'SMA_50', 'SMA_200']])
    st.markdown("#### 基本面 (年度)")
    if financials is not None and not financials.empty:
        if all(item in financials.index for item in ['Total Revenue', 'Net Income']):
            financial_summary = financials.loc[['Total Revenue', 'Net Income']].transpose()
            financial_summary.index = financial_summary.index.year
            st.bar_chart(financial_summary)
        else:
            st.info("部分年度財報數據欄位缺失。")
    else:
        st.info("找不到詳細的年度財報數據。")
    st.markdown("#### 籌碼面")
    ownership_data = {'機構持股比例': info.get('heldPercentInstitutions', 0),'內部人士持股比例': info.get('heldPercentInsiders', 0),'機構總數': info.get('institutionCount', 0)}
    ownership_df = pd.DataFrame(list(ownership_data.items()),columns=['指標', '數值'])
    ownership_df.loc[ownership_df['指標'].str.contains('比例'), '數值'] = pd.to_numeric(ownership_df['數值'], errors='coerce').map('{:.2%}'.format)
    st.dataframe(ownership_df, hide_index=True, use_container_width=True)


st.set_page_config(page_title="AI 多因子分析儀表板", page_icon="💡", layout="wide")
st.title("💡 AI 多因子分析儀表板")
st.markdown("自動分析最新新聞，並整合基本面、技術面數據，提供全方位決策輔助。")

gemini_model = initialize_model()
DATA_FILE = "news_analysis.csv"

if os.path.exists(DATA_FILE):
    st.success("成功讀取到新聞分析數據！")
    df = pd.read_csv(DATA_FILE, dtype={'ticker': str})
    for index, row in df.iterrows():
        st.markdown("---")
        title = row.get('title', '標題不存在')
        sentiment = row.get('sentiment', 'N/A')
        summary = row.get('summary', '')
        ticker = str(row.get('ticker', 'N/A')).strip()
        is_valid_ticker = (ticker != "N/A" and ticker.lower() != "nan" and ticker.isdigit() and len(ticker) >= 4)
        
        with st.expander(f"**{sentiment}** | **{ticker if is_valid_ticker else '市場新聞'}** | {title}", expanded=index == 0):
            if is_valid_ticker:
                col1, col2 = st.columns([1, 1.2])
                with col1:
                    st.subheader("📰 AI 新聞質化分析")
                    summary_points = summary.split('\n')
                    for point in summary_points:
                        st.markdown(f"- {point.strip()}")
                    st.info(f"**🔑 關 鍵 字**： {row.get('keywords', '')}")
                    st.markdown(f"[閱讀原文]({row.get('url', '#')})")
                with col2:
                    info, hist, financials = get_stock_data(ticker)
                    if info and not hist.empty:
                        display_quantitative_data(ticker, info, hist, financials)
                        get_ai_overall_analysis(gemini_model, ticker, sentiment, summary, info, hist)
            else:
                st.subheader("📰 AI 新聞質化分析")
                summary_points = str(row.get('summary', '')).split('\n')
                for point in summary_points:
                    st.markdown(f"- {point.strip()}")
                st.info(f"**🔑 關 鍵 字**： {row.get('keywords', '')}")
                st.markdown(f"[閱讀原文]({row.get('url', '#')})")
                st.info("此篇新聞為市場宏觀分析，或未識別出有效的股票代碼。")
else:
    st.warning("⚠️ 找不到 `news_analysis.csv` 檔案。")
    st.info("請先在您的終端機中執行 `python collector.py` 來產生分析數據。")