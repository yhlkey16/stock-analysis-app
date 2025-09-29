import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import streamlit as st
import yfinance as yf # 導入 yfinance
import pandas as pd   # 導入 pandas 用於數據處理

# --- (initialize_model 函式和之前完全一樣) ---
# @st.cache_data
def initialize_model():
    """從環境變數讀取 API 金鑰並初始化 Gemini 模型"""
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

# --- AI 新聞分析函式 (升級版) ---
def analyze_stock_news(url, model):
    """接收一個新聞網址，爬取內容，並使用 Gemini 分析情緒和股票代碼。"""
    if not model:
        st.error("模型未初始化，無法進行分析。")
        return None

    try:
        # (爬蟲部分和之前一樣)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article_body = soup.find('div', class_='content-main')
        if not article_body:
            st.warning("❌ 解析失敗：在網頁中找不到新聞內文區塊。請確認網址是鉅亨網的文章頁面。")
            return None
        article_text = article_body.get_text(strip=True, separator='\n')
    except requests.exceptions.RequestException as e:
        st.error(f"❌ 爬取網頁失敗：{e}")
        return None

    # --- 升級版的 Prompt ---
    # 我們新增了一個指令，要求 AI 找出股票代碼
    prompt = f"""
    請你扮演一位專業的台灣股市金融分析師。
    請閱讀以下這篇財經新聞，並完全遵循以下指示：
    1.  找出這篇新聞主要報導的台灣上市公司股票代碼 (ticker)。如果找不到，請回傳 "N/A"。
    2.  判斷新聞對股價的潛在情緒是「正面」、「負面」還是「中性」。
    3.  用 3-4 句話，以條列式的方式，總結新聞的關鍵重點。
    4.  提取新聞中最重要的 3 到 5 個關鍵字。
    5.  將你的分析結果以一個標準的 JSON 格式回傳，不要有任何多餘的文字。
        JSON 必須包含以下四個鍵(key)：
        - "ticker": (string) 股票代碼，例如 "2330" 或 "N/A"
        - "sentiment": (string) 情緒判斷 ("正面", "負面", "中性")
        - "summary": (string) 重點摘要
        - "keywords": (array of strings) 關鍵字列表

    新聞內文如下：
    ---
    {article_text[:4000]} 
    ---
    """

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        analysis_result = json.loads(cleaned_response)
        return analysis_result
    except Exception as e:
        st.error(f"❌ AI 分析或 JSON 解析失敗：{e}")
        return None

# --- 新功能：抓取股價並繪圖 ---
def get_stock_data_and_plot(ticker):
    """使用 yfinance 抓取股票資料並顯示指標與圖表"""
    try:
        # yfinance 需要台灣股票代碼後面加上 ".TW"
        stock_ticker = f"{ticker}.TW"
        stock = yf.Ticker(stock_ticker)

        # 獲取今日的詳細資訊
        info = stock.info
        
        # 獲取近三個月的歷史股價
        hist = stock.history(period="3mo")

        if hist.empty:
            st.warning(f"找不到股票代碼 {ticker} 的歷史股價數據。")
            return

        st.subheader(f"📈 {info.get('longName', ticker)} 即時股價資訊")

        # 使用欄位來並排顯示指標
        col1, col2, col3 = st.columns(3)
        current_price = info.get('regularMarketPrice', 'N/A')
        previous_close = info.get('previousClose', 0)
        
        # 計算漲跌幅
        price_change = "N/A"
        price_change_percent = "N/A"
        if isinstance(current_price, (int, float)) and previous_close > 0:
            price_change = current_price - previous_close
            price_change_percent = (price_change / previous_close) * 100
            
        with col1:
            st.metric("目前股價", f"{current_price:.2f}", f"{price_change:.2f} ({price_change_percent:.2f}%)")
        with col2:
            st.metric("成交量", f"{info.get('regularMarketVolume', 0):,}")
        with col3:
            st.metric("開盤價", f"{info.get('regularMarketOpen', 'N/A'):.2f}")

        # 顯示近三個月股價走勢圖
        st.subheader("近三個月股價走勢")
        # 我們只畫出收盤價
        st.line_chart(hist['Close'])

    except Exception as e:
        st.error(f"❌ 抓取股價資訊時發生錯誤：{e}")


# --- Streamlit App 的主體介面 (升級版) ---

st.set_page_config(page_title="AI 個股儀表板", page_icon="📊")
st.title("📊 AI 個股新聞儀表板")
st.markdown("結合新聞情緒分析與即時股價數據，提供更全面的個股洞察。")
st.markdown("---")

url = st.text_input("請在此貼上鉅亨網(cnyes)的新聞網址：", placeholder="例如：關於台積電、聯發科等公司的新聞...")

if st.button("啟動分析引擎"):
    if url:
        gemini_model = initialize_model()
        if gemini_model:
            with st.spinner("正在進行 AI 新聞分析..."):
                analysis_result = analyze_stock_news(url, gemini_model)
            
            if analysis_result:
                st.success("新聞分析完成！")
                st.subheader("📰 AI 質化分析結果")

                # (顯示新聞分析結果的部分和之前類似)
                sentiment = analysis_result.get('sentiment', 'N/A')
                if sentiment == "正面":
                    st.metric(label="新聞情緒", value=sentiment, delta="利多 👍")
                elif sentiment == "負面":
                    st.metric(label="新聞情緒", value=sentiment, delta="利空 👎", delta_color="inverse")
                else:
                    st.metric(label="新聞情緒", value=sentiment)

                with st.expander("重點摘要", expanded=True):
                    summary_points = analysis_result.get('summary', 'N/A').split('\n')
                    for point in summary_points:
                        st.markdown(f"- {point.strip()}")
                
                st.info(f"🔑 **關 鍵 字**： {', '.join(analysis_result.get('keywords', []))}")
                
                # --- 新增的區塊：處理股價數據 ---
                st.markdown("---")
                ticker = analysis_result.get("ticker", "N/A")
                
                if ticker != "N/A":
                    with st.spinner(f"正在抓取股票 {ticker} 的量化數據..."):
                        get_stock_data_and_plot(ticker)
                else:
                    st.info("AI 未能從此篇新聞中識別出有效的股票代碼。")
    else:
        st.warning("請先輸入新聞網址！")