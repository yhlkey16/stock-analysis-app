import os
import google.generativeai as genai

# 讀取你的 API 金鑰
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("錯誤：找不到 GOOGLE_API_KEY 環境變數。")
    exit()

genai.configure(api_key=api_key)

print("正在查詢您帳戶可用的模型...\n")

for m in genai.list_models():
  # 我們只關心支援 'generateContent' 方法的模型
  if 'generateContent' in m.supported_generation_methods:
    print(f"- {m.name}")

print("\n查詢完畢。")