import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

# 🔥 แยก query ตาม “ฟีลหนังสือพิมพ์”
QUERIES = [
    # 🇹🇭 ไทย
    "Thailand economy inflation tourism digital economy",
    "Thailand technology startup ecommerce AI Thailand",
    "Thailand consumer trend shopping behavior Gen Z Thailand",
    "Thailand entertainment celebrity news trend Thailand",

    # 🌏 เอเชีย
    "Asia economy China Japan Korea growth inflation",
    "Asia technology AI semiconductor China Japan Korea",
    "Asia consumer trend ecommerce China Southeast Asia",
    "Asia entertainment trend Kpop China media industry"
]

KEYWORDS = [
    "economy", "inflation", "tourism", "technology", "AI",
    "startup", "consumer", "trend", "ecommerce",
    "entertainment", "media", "policy", "รัฐบาล"
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
            desc = e.get("summary", "")[:120]

            all_articles.append({
                "title": title,
                "desc": desc
            })

    return all_articles


# ------------------ FILTER ------------------

def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        text = (a["title"] + " " + a["desc"]).lower()

        if any(k in text for k in KEYWORDS):
            if a["title"] not in seen:
                seen.add(a["title"])
                filtered.append(a)

    return filtered[:10]  # ให้ข่าวเยอะขึ้นหน่อยสำหรับ morning


# ------------------ PROMPT ------------------

def build_prompt(news):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in news
    )

    return f"""
คุณคือคนอ่านข่าวเก่ง ที่เล่าเหมือน “สรุปหนังสือพิมพ์เช้า”

ข่าว:
{news_text}

สรุปเป็นภาษาไทยทั้งหมด
โทนเหมือนอ่าน ไทยรัฐ + เดลินิวส์ + กรุงเทพธุรกิจ
แต่มีมุมมอง “คนมองเทรนด์”

โครงสร้าง:

📰 ข่าวเด่นเช้านี้ (5-7 ข่าว)
เล่าแบบ:
- เกิดอะไร
- ทำไมคนถึงสนใจ
- มันสะท้อนอะไรในสังคมหรือเศรษฐกิจ

🌏 เทรนด์ที่น่าจับตา (2-3 ข้อ)
เช่น:
- คนกำลังใช้เงินกับอะไร
- เทคโนโลยีอะไรเริ่มมา
- พฤติกรรมคนเปลี่ยนยังไง

💡 มุมคิด (สำคัญ)
สรุป 2-3 บรรทัดว่า:
“ถ้าคิดแบบนักลงทุน / คนทำธุรกิจ ควรเห็นอะไรจากข่าววันนี้”
"""


# ------------------ MAIN ------------------

def main():
    try:
        raw_news = fetch_news_multi(QUERIES)
        news = filter_articles(raw_news)

        prompt = build_prompt(news)
        summary = ask(prompt)

        send_plain(
            f"🌅 Morning Brief — {datetime.now().strftime('%d/%m %H:%M')}\n\n"
            f"{summary.strip()}"
        )

    except Exception as e:
        send_error("morning_news", e)
        raise


if __name__ == "__main__":
    main()