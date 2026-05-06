import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_long, send_error


# ✅ query ใหม่ (กว้าง + ไทย + อังกฤษ)
QUERIES = [
    # 🇹🇭 ไทย
    "ข่าวเศรษฐกิจ ไทย",
    "ข่าวเทคโนโลยี ไทย",
    "ข่าวธุรกิจ ไทย",
    "ข่าวบันเทิง ไทย",

    # 🌏 เอเชีย + global
    "Asia economy news",
    "Asia technology news",
    "consumer trend Asia",
]

# ✅ fallback กันข่าวหาย
FALLBACK_QUERIES = [
    "Thailand news",
    "world news economy technology",
]


# ------------------ FETCH ------------------

def fetch_news_multi(queries, hours=12):
    all_articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=th&gl=TH&ceid=TH:th"
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


# ------------------ FILTER (เบามาก) ------------------

def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        key = a["title"][:80]

        if key in seen:
            continue

        # ✅ เอาเกือบหมด กันข่าวหาย
        seen.add(key)
        filtered.append(a)

    return filtered[:12]


# ------------------ PROMPT ------------------

def build_prompt(articles):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in articles
    )

    return f"""
คุณคือคนอ่านข่าวเช้าเก่งมาก

ข่าว:
{news_text}

สรุปเป็นภาษาไทย ฟีล “หนังสือพิมพ์ + เพื่อนเล่า”

📰 ข่าวเด่น (5 ข่าว)
- เกิดอะไร
- ทำไมคนสนใจ

🌏 เทรนด์
- คนกำลังสนใจอะไร
- พฤติกรรมเปลี่ยนยังไง

💡 มุมคิด
- ถ้าเป็นนักลงทุน/เจ้าของธุรกิจ ควรเห็นอะไร

❗ ห้ามบอกว่าไม่มีข่าว
"""


# ------------------ MAIN ------------------

def main():
    try:
        raw = fetch_news_multi(QUERIES)
        news = filter_articles(raw)

        print(f"[DEBUG] RAW: {len(raw)} | FILTERED: {len(news)}")

        # ✅ fallback ถ้าข่าวน้อย
        if len(news) < 5:
            print("[DEBUG] Using fallback...")
            raw = fetch_news_multi(FALLBACK_QUERIES)
            news = filter_articles(raw)

        # ✅ กัน empty
        if not news:
            send_long("🌅 Morning Brief — วันนี้ข่าวน้อย แต่ตลาดยังปกติ ไม่มี event ใหญ่")
            return

        prompt = build_prompt(news)
        summary = ask(prompt)

        send_long(
            f"🌅 Morning Brief — {datetime.now().strftime('%d/%m %H:%M')}\n\n"
            f"{summary.strip()}"
        )

    except Exception as e:
        send_error("morning_news", e)
        raise


if __name__ == "__main__":
    main()