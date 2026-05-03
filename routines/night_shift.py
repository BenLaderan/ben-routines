import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
import yfinance as yf
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

STOCKS = ["NVDA", "AVGO", "DOCN", "MU", "CEG", "FN", "JBL", "ANET", "VST", "VRT"]
INDICES = ["^GSPC", "^DJI", "^IXIC"]
NEWS_QUERY = "Wall Street US stock market Europe economy"


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
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = []
    for entry in feed.entries:
        try:
            pub = parsedate_to_datetime(entry.published)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub < cutoff:
                continue
        except Exception:
            continue
        results.append({
            "title": entry.get("title", ""),
            "description": entry.get("summary", ""),
        })
    return results


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
คุณคือเพื่อนที่เข้าใจเรื่องการลงทุน กำลังเล่าข่าวตลาดคืนนี้ให้เบนฟังแบบสบายๆ

ราคาหุ้น US ที่เบนถืออยู่:
{stock_block}

ดัชนี Wall Street:
{index_block}

ข่าวล่าสุด (12 ชั่วโมงที่ผ่านมา):
{news_text if news_text else "ไม่มีข่าว"}

สรุปเป็นภาษาไทยทั้งหมด เขียนเหมือนเพื่อนเล่าให้ฟัง ไม่ต้องเป็นทางการ
ตัวเลขสำคัญและชื่อหุ้นให้ใส่ * ครอบทั้งสองข้าง เช่น *AVGO* หรือ *-1.2%* (Telegram bold)
โครงสร้าง:

📰 ข่าวใหญ่คืนนี้ (3-5 ข่าว)
แต่ละข่าวเล่าแบบนี้:
— เกิดอะไร → ทำไมถึงสำคัญ → กระทบเรายังไง (2-3 บรรทัด)

🇺🇸 Wall Street ปิดที่
*Dow Jones*: [ราคา] ([%])
*S&P 500*: [ราคา] ([%])
*Nasdaq*: [ราคา] ([%])
ตัวเลขทำ bold ทั้งหมด

🌏 ตลาดเอเชียพรุ่งนี้จะเป็นยังไง
วิเคราะห์ทิศทางแบบตรงๆ 2-3 ประโยค

⚡ ผลต่อพอร์ตเบน (*AVGO*, *NVDA*, *MRSH*, *CEG*, *FN*, *MU*, *JBL*, *ANET*, *VST*, *VRT*)
วิเคราะห์แต่ละตัวสั้นๆ แบบตรงไปตรงมา

⚠️ คืนนี้ต้องระวัง / มีโอกาสอะไร
จบด้วย 1 บรรทัดสรุปว่าคืนนี้ต้องระวังอะไร หรือมีโอกาสอะไรน่าสนใจ
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

        send_plain(f"🌙 Night Shift — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n{summary.strip()}")
    except Exception as e:
        send_error("night_shift", e)
        raise


if __name__ == "__main__":
    main()
