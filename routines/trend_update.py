import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error


# 🔥 แยก query เป็น “signal จริง”
QUERIES = [
    # 🇹🇭 Thailand
    "Thailand consumer behavior trend ecommerce lifestyle",
    "Thailand food trend shopping trend Gen Z Thailand",
    "Thailand technology trend AI app social media usage",

    # 🌏 Global
    "global consumer trend ecommerce TikTok trend Gen Z",
    "consumer behavior shift digital trend 2025",
    "viral product trend social media global",
]

KEYWORDS = [
    "trend", "consumer", "shopping", "ecommerce",
    "AI", "app", "social media", "lifestyle",
    "food", "Gen Z", "behavior", "digital"
]

STRONG_SIGNALS = [
    "ยอดขาย", "growth", "เพิ่มขึ้น", "surge",
    "demand", "นิยม", "ฮิต", "viral", "ล้านวิว"
]


# ------------------ FETCH ------------------

def fetch_news_multi(queries, hours=48):
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


# ------------------ FILTER ------------------

def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        text = (a["title"] + " " + a["desc"]).lower()
        key = a["title"][:80]

        if key in seen:
            continue

        if any(k in text for k in KEYWORDS):
            seen.add(key)
            filtered.append(a)

    return filtered[:12]  # เพิ่ม data ให้ Claude เห็น pattern


# ------------------ SCORING ------------------

def score_signal(article):
    text = (article["title"] + " " + article["desc"]).lower()
    score = 0

    for k in STRONG_SIGNALS:
        if k in text:
            score += 1

    return score


def sort_by_signal(articles):
    return sorted(articles, key=score_signal, reverse=True)


# ------------------ PROMPT ------------------

def build_prompt(articles):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in articles
    )

    return f"""
คุณไม่ใช่คนสรุปข่าว แต่เป็น “trend analyst”

ข้อมูล:
{news_text}

วิเคราะห์ให้ลึกและ “เอาไปใช้ได้จริง”

ตอบเป็นภาษาไทย:

🔥 (1) Key Trends (3 เรื่อง)
- สรุป trend เป็น “pattern” ไม่ใช่ข่าว
- เช่น: คนเริ่มซื้อของ X เพราะ Y

🧠 (2) Behavior Insight
- คนกำลังเปลี่ยนพฤติกรรมยังไง
- pain point หรือ desire คืออะไร

📡 (3) Signal Strength
ให้แต่ละ trend:
- Mainstream (เริ่มใหญ่)
- Emerging (กำลังมา)
- Noise (แค่ไวรัล)

💼 (4) Monetization
- ทำเงินยังไง (สำคัญมาก)
- ธุรกิจ / content / product

🌏 (5) Local vs Global
- อะไรเกิดในไทย
- อะไรเป็น trend โลก

❗ ห้ามเล่าข่าว
❗ ต้องสรุปเป็น insight เท่านั้น
"""


# ------------------ MAIN ------------------

def main():
    try:
        raw = fetch_news_multi(QUERIES)
        filtered = filter_articles(raw)
        sorted_articles = sort_by_signal(filtered)

        if not sorted_articles:
            send_plain("📈 Trend Update — วันนี้ยังไม่มี signal ชัด")
            return

        prompt = build_prompt(sorted_articles)
        summary = ask(prompt)

        send_plain(
            f"📈 Trend Intelligence — {datetime.now().strftime('%d/%m/%Y')}\n\n"
            f"{summary.strip()}"
        )

    except Exception as e:
        send_error("trend_update", e)
        raise


if __name__ == "__main__":
    main()