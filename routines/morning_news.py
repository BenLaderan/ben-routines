import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yfinance as yf
from datetime import datetime, timedelta, timezone

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

STOCKS = ["AAV.BK", "GULF.BK", "BGRIM.BK"]
INDICES = ["^N225", "^HSI", "^STI", "^SET.BK"]
NEWS_QUERY = "Asia stock market economy"


def fetch_prices(tickers: list[str]) -> dict:
    results = {}
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                last = hist["Close"].iloc[-1]
                pct = ((last - prev_close) / prev_close) * 100
                results[symbol] = {"price": round(last, 2), "change_pct": round(pct, 2)}
            elif len(hist) == 1:
                results[symbol] = {"price": round(hist["Close"].iloc[-1], 2), "change_pct": None}
            else:
                results[symbol] = {"price": "N/A", "change_pct": None}
        except Exception as e:
            results[symbol] = {"price": "error", "change_pct": None, "error": str(e)}
    return results


def fetch_news(query: str, hours: int = 12) -> list[dict]:
    from_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_time,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 10,
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("articles", [])


def format_price_block(prices: dict) -> str:
    lines = []
    for symbol, data in prices.items():
        price = data.get("price", "N/A")
        pct = data.get("change_pct")
        if pct is not None:
            sign = "+" if pct >= 0 else ""
            lines.append(f"{symbol}: {price} ({sign}{pct}%)")
        else:
            lines.append(f"{symbol}: {price}")
    return "\n".join(lines)


def build_prompt(stock_block: str, index_block: str, articles: list[dict]) -> str:
    news_text = "\n".join(
        f"- {a['title']} | {a.get('description', '')}"
        for a in articles[:10]
    )
    return f"""
คุณคือนักวิเคราะห์การลงทุนที่สรุปข่าวตลาดให้เบน

ข้อมูลราคาหุ้นไทยที่เบนถืออยู่:
{stock_block}

ดัชนีตลาดหุ้นเอเชีย:
{index_block}

ข่าวล่าสุด (12 ชั่วโมงที่ผ่านมา):
{news_text if news_text else "ไม่มีข่าว"}

สรุปเป็นภาษาไทย โครงสร้างดังนี้ (ใช้หัวข้อและ emoji):

📰 ข่าวใหญ่วันนี้ (3-5 ข่าว)
[ชื่อข่าว]
[อธิบาย 2 บรรทัด]

📊 ตลาดหุ้นเอเชียเช้านี้
[แสดงราคาและ % เปลี่ยนแปลง]

⚡ ผลกระทบต่อ AAV, GULF, BGRIM
[วิเคราะห์แต่ละตัว 1-2 ประโยค]

👁️ สิ่งที่ต้องจับตาวันนี้
[bullet 2-3 ข้อ]

💡 โอกาสที่อาจเกิดขึ้น
[bullet 1-2 ข้อ]

กระชับ ตรงประเด็น ไม่ต้องมีคำนำหน้า
"""


def main():
    try:
        stock_prices = fetch_prices(STOCKS)
        index_prices = fetch_prices(INDICES)
        articles = fetch_news(NEWS_QUERY, hours=12)

        stock_block = format_price_block(stock_prices)
        index_block = format_price_block(index_prices)

        prompt = build_prompt(stock_block, index_block, articles)
        summary = ask(prompt)

        send_plain(f"🌅 สรุปตลาดเช้า — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n{summary.strip()}")
    except Exception as e:
        send_error("morning_news", e)
        raise


if __name__ == "__main__":
    main()
