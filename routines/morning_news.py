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

STOCKS = ["000660.KR", "005930.KR", "TSMC.TW"]
INDICES = ["^N225", "^HSI", "^STI", "^SET.BK"]

QUERIES = [
    "AI GPU demand NVIDIA AMD TSMC",
    "data center cloud capex hyperscaler",
    "AI electricity demand nuclear energy grid",
    "Samsung SK Hynix TSMC earnings guidance"
]

KEYWORDS = [
    "capex", "guidance", "demand", "data center",
    "AI", "GPU", "cloud", "energy", "electricity",
    "nuclear", "earnings"
]

CRITICAL_KEYWORDS = [
    "capex cut", "demand slowdown", "guidance lowered",
    "data center delay"
]


def fetch_prices(tickers):
    results = {}
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                last = hist["Close"].iloc[-1]
                pct = ((last - prev) / prev) * 100
                results[symbol] = {"price": round(last, 2), "pct": round(pct, 2)}
        except:
            results[symbol] = {"price": "N/A", "pct": None}
    return results


def fetch_news_multi(queries, hours=12):
    all_articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for e in feed.entries:
            try:
                pub = parsedate_to_datetime(e.published)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    continue
            except:
                continue

            title = e.get("title", "")
            desc = e.get("summary", "")[:150]

            all_articles.append({
                "title": title,
                "desc": desc
            })

    return all_articles


def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        text = (a["title"] + " " + a["desc"]).lower()

        if any(k in text for k in KEYWORDS):
            if a["title"] not in seen:
                seen.add(a["title"])
                filtered.append(a)

    return filtered[:6]


def detect_critical(articles):
    alerts = []
    for a in articles:
        text = (a["title"] + " " + a["desc"]).lower()
        if any(k in text for k in CRITICAL_KEYWORDS):
            alerts.append(a["title"])
    return alerts


def build_prompt(news):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in news
    )

    return f"""
คุณคือ analyst ที่โฟกัส “signal ไม่ใช่ข่าว”

ข่าว:
{news_text}

ตอบสั้น กระชับ:

🧠 AI Cycle
ยังแข็งแรง / เริ่มชะลอ / มีความเสี่ยง

🔄 Money Flow
เงินไหลไป sector ไหน (chip / infra / energy)

⚡ Key Signal
- bullet 2-4 ข้อ

🎯 Action
ควร: ถือ / เพิ่ม / ระวัง
"""


def main():
    try:
        stock_prices = fetch_prices(STOCKS)
        index_prices = fetch_prices(INDICES)

        raw_news = fetch_news_multi(QUERIES)
        news = filter_articles(raw_news)

        alerts = detect_critical(news)
        if alerts:
            send_plain("🚨 CRITICAL SIGNAL:\n" + "\n".join(alerts[:3]))

        prompt = build_prompt(news)
        summary = ask(prompt)

        send_plain(f"🌅 Morning Signal — {datetime.now().strftime('%d/%m %H:%M')}\n\n{summary.strip()}")

    except Exception as e:
        send_error("morning_news", e)
        raise


if __name__ == "__main__":
    main()
