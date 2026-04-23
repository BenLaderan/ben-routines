import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

SEARCH_TERMS = {
    "หลิงหลิง": "หลิงหลิง",
    "ออมกรณ์นภัส": "ออมกรณ์นภัส",
}


def fetch_rss(query: str, hours: int = 24) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=th&gl=TH&ceid=TH:th"
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
            "source": entry.get("source", {}).get("title", ""),
            "published": pub.strftime("%d/%m %H:%M"),
        })
    return results


def build_prompt(all_articles: dict[str, list[dict]]) -> str:
    sections = []
    for term, articles in all_articles.items():
        if articles:
            lines = "\n".join(
                f"- [{a['published']}] {a['title']} ({a['source']})"
                for a in articles
            )
            sections.append(f"ข่าวเกี่ยวกับ {term}:\n{lines}")

    combined = "\n\n".join(sections)
    return f"""
คุณคือผู้ช่วยส่วนตัวที่ติดตามข่าวดาราให้เบน

ข่าวที่พบจาก Google News (24 ชั่วโมงที่ผ่านมา):
{combined}

สรุปเป็นภาษาไทย เขียนเหมือนเพื่อนเล่าให้ฟัง:
- แบ่งตามชื่อดารา
- เล่าว่าเกิดอะไรขึ้น บรรยากาศเป็นยังไง
- ถ้าข่าวหลิงหลิงกับออมกรณ์นภัสเชื่อมกัน ให้รวมเล่าด้วยกัน
- ไม่ต้องมีคำนำ กระชับ ไม่เกิน 5 บรรทัดต่อคน
"""


def main():
    try:
        all_articles: dict[str, list[dict]] = {}
        for label, query in SEARCH_TERMS.items():
            all_articles[label] = fetch_rss(query, hours=24)

        total = sum(len(v) for v in all_articles.values())
        if total == 0:
            return  # no news — exit silently

        prompt = build_prompt(all_articles)
        summary = ask(prompt)

        send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{summary.strip()}")
    except Exception as e:
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()
