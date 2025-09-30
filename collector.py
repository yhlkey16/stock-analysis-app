import os
import google.generativeai as genai
import json
import pandas as pd
import time
from newsapi import NewsApiClient

def initialize_model():
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("❌ 錯誤：在環境變數中找不到 GOOGLE_API_KEY。")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        print("✅ AI 模型初始化成功！")
        return model
    except Exception as e:
        print(f"❌ AI 模型初始化失敗：{e}")
        return None

def analyze_news_content(article_content, article_url, model):
    if not model or not article_content:
        return None
    prompt = f"""
    請你扮演一位專業的台灣股市金融分析師。
    你的任務是閱讀一篇財經新聞，並以標準的 JSON 格式回傳你的分析。

    **成功範例**：
    輸入新聞：「台積電(2330)今日宣布，其位於高雄的2奈米廠將如期於明年開始裝機...法人看好此舉將鞏固其領先地位。」
    輸出JSON：
    {{
        "ticker": "2330",
        "sentiment": "正面",
        "summary": "1. 台積電宣布高雄2奈米廠將如期裝機。\n2. 法人看好此舉能鞏固其市場領先地位。",
        "keywords": ["台積電", "2330", "2奈米", "高雄廠", "法人"]
    }}

    請嚴格遵循以上範例的格式，分析以下這篇真實新聞。如果新聞內容廣泛，與特定某支台股無關，則 "ticker" 欄位應回傳 "N/A"。

    **真實新聞內文如下**：
    ---
    {article_content[:4000]}
    ---
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        analysis_result = json.loads(cleaned_response)
        analysis_result['url'] = article_url
        return analysis_result
    except Exception as e:
        print(f"❌ 對於網址 {article_url} 的 AI 分析或 JSON 解析失敗：{e}")
        return None

if __name__ == "__main__":
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
    if not NEWS_API_KEY:
        print("❌ 錯誤：在環境變數中找不到 NEWS_API_KEY。")
        exit()
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    print("🚀 正在初始化 NewsAPI 客戶端...")
    try:
        query = '"台積電" OR "聯發科" OR "鴻海" OR "長榮" OR "富邦金" OR "國泰金"'
        all_articles = newsapi.get_everything(q=query, language='zh', sort_by='publishedAt', page_size=10)
        articles = all_articles.get('articles', [])
        if not articles:
            print("⚠️ 從 NewsAPI 未找到符合條件的文章。")
            exit()
        print(f"✅ 從 NewsAPI 成功找到 {len(articles)} 篇文章。")
    except Exception as e:
        print(f"❌ 從 NewsAPI 獲取新聞失敗：{e}")
        exit()
    model = initialize_model()
    if not model:
        exit()
    all_analysis_results = []
    for i, article in enumerate(articles):
        print(f"\n--- 正在分析第 {i+1}/{len(articles)} 篇文章 ---")
        title = article['title']
        print(f"🔗 標題: {title}")
        content = article.get('content') or article.get('description')
        url = article.get('url')
        if content:
            result = analyze_news_content(content, url, model)
            if result:
                result['title'] = title
                all_analysis_results.append(result)
                print("✅ 分析成功並已儲存。")
            else:
                print("❌ 分析失敗，跳過此篇。")
        else:
            print("⚠️ 此篇文章沒有可用的內容，跳過。")
        if i < len(articles) - 1:
             print("\n⏳ 為遵守 API 速率限制，等待 31 秒後繼續...")
             time.sleep(31)
    if all_analysis_results:
        print("\n💾 正在將所有分析結果儲存至 news_analysis.csv ...")
        df = pd.DataFrame(all_analysis_results)
        df.to_csv('news_analysis.csv', index=False, encoding='utf--sig')
        print("🎉🎉🎉 任務完成！已成功產生 news_analysis.csv 檔案。")
    else:
        print("🤷‍♂️ 本次執行未成功分析任何新聞。")