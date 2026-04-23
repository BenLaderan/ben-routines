import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime, timedelta, timezone

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
SEARCH_TERMS = ["หลิงหลิง", "ออม กรณ์นภัส", "หลิงออม"]


def fetch_news(query: str, hours: int = 24) -> list[dict]:
    from_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_time,
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("articles", [])


def build_prompt(all_articles: dict[str, list[dict]]) -> str:
    sections = []
    for term, articles in all_articles.items():
        if articles:
            news_lines = "\n".join(
                f"- {a['title']} | {a.get('description', '')}" for a in articles
            )
            sections.append(f"ข่าวเกี่ยวกับ '{term}':\n{news_lines}")

    combined = "\n\n".join(sections)
    return f"""
คุณคือผู้ช่วยส่วนตัวที่ติดตามข่าวดาราให้เบน

ข่าวที่พบ (24 ชั่วโมงที่ผ่านมา):
{combined}

สรุปสั้นๆ เป็นภาษาไทย แบ่งตามชื่อ ว่าเกิดอะไรขึ้นบ้าง
ถ้าข่าวซ้ำกัน (เช่น หลิงหลิง และ หลิงออม คือคนเดียวกัน) ให้รวมเป็นหัวข้อเดียว
ไม่ต้องมีคำนำ กระชับ ไม่เกิน 5 บรรทัดต่อคน
"""


def main():
    try:
        all_articles: dict[str, list[dict]] = {}
        for term in SEARCH_TERMS:
            articles = fetch_news(term, hours=24)
            all_articles[term] = articles

        total = sum(len(v) for v in all_articles.values())
        if total == 0:
            # No news — exit silently
            return

        prompt = build_prompt(all_articles)
        summary = ask(prompt)

        send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{summary.strip()}")
    except Exception as e:
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()
