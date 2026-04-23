import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

QUERIES = [
    "trending social media TikTok Thailand",
    "viral trend Thailand",
]


def fetch_news(query: str, hours: int = 48) -> list[dict]:
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


def build_prompt(articles: list[dict]) -> str:
    if not articles:
        news_text = "ไม่พบข่าวในช่วงนี้"
    else:
        news_text = "\n".join(
            f"- {a['title']} | {a.get('description', '')}" for a in articles[:15]
        )
    return f"""
คุณคือนักวิเคราะห์ trend และพฤติกรรมผู้บริโภคในไทย

ข่าวและเนื้อหาที่พบ:
{news_text}

วิเคราะห์และสรุปเป็นภาษาไทย โดยต้องมีครบ 4 ส่วนนี้เสมอ:

🔥 (1) What's happening
วันนี้คนพูดถึงอะไร — สรุป trend หลัก 2-3 เรื่อง

🧠 (2) Why it matters
สะท้อน behavior หรือ pain point อะไรของคนไทยในตอนนี้

📡 (3) Signal type
ระบุแต่ละเรื่องว่าเป็น Mainstream (กระแสหลัก) หรือ Emerging (กำลังโต)

💼 (4) Opportunity
แบรนด์หรือผู้สร้างคอนเทนต์เอาไปทำอะไรได้บ้าง (1-3 ข้อ)

ไม่ต้องมีคำนำ ตอบตรงๆ แต่ละส่วนไม่เกิน 4 บรรทัด
"""


def main():
    try:
        all_articles: list[dict] = []
        seen_titles: set[str] = set()

        for query in QUERIES:
            for article in fetch_news(query, hours=48):
                title = article.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_articles.append(article)

        prompt = build_prompt(all_articles)
        summary = ask(prompt)

        send_plain(f"📈 Trend Update — {datetime.now().strftime('%d/%m/%Y')}\n\n{summary.strip()}")
    except Exception as e:
        send_error("trend_update", e)
        raise


if __name__ == "__main__":
    main()
