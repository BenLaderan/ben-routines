print("celeb_watch starting...")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
    from datetime import datetime, timedelta, timezone
    from shared.claude_client import ask
    from shared.telegram import send_plain, send_error
except Exception as e:
    print(f"Import error: {e}")
    raise

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

SEARCH_TERMS = {
    "หลิงหลิง": '"Ling Ling" OR "หลิงหลิง"',
    "ออมกรณ์นภัส": '"Oumkornnaphat" OR "ออมกรณ์นภัส"',
}


def fetch_news(query: str, hours: int = 24) -> list[dict]:
    from_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_time,
        "language": "th",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("articles", [])


def build_prompt(all_articles: dict[str, list[dict]]) -> str:
    sections = []
    for term, articles in all_articles.items():
        if articles:
            lines = "\n".join(
                f"- {a['title']} | {a.get('description', '')}"
                for a in articles
            )
            sections.append(f"ข่าวเกี่ยวกับ {term}:\n{lines}")

    combined = "\n\n".join(sections)
    return f"""
คุณคือผู้ช่วยส่วนตัวที่ติดตามข่าวดาราให้เบน

ข่าวที่พบ (24 ชั่วโมงที่ผ่านมา):
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
            all_articles[label] = fetch_news(query, hours=24)

        total = sum(len(v) for v in all_articles.values())
        if total == 0:
            send_plain("⭐ Celeb Watch — วันนี้หลิงออมเงียบมากครับ ไม่มีอะไรอัพเดท")
            return

        prompt = build_prompt(all_articles)
        summary = ask(prompt)

        send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{summary.strip()}")
    except Exception as e:
        print(f"Runtime error: {e}")
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()
