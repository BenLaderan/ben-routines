import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error


# ✅ query ใหม่ (balanced: ไม่แคบเกิน / ไม่กว้างเกิน)
QUERIES = [
    "AI data center Nvidia Microsoft Google",
    "cloud computing AI demand data center",
    "semiconductor chip industry AI",
    "electricity demand data center power",
]

# ✅ fallback กันข่าวหาย
FALLBACK_QUERIES = [
    "AI technology news",
    "energy market news",
]

# ✅ keyword ลดความ strict
KEYWORDS = [
    "ai", "data center", "cloud", "gpu",
    "chip", "semiconductor",
    "energy", "electricity", "power",
    "demand", "growth", "investment",
    "capacity", "infrastructure"
]


# ------------------ FETCH ------------------

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


# ------------------ FILTER ------------------

def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        text = (a["title"] + " " + a["desc"]).lower()
        key = a["title"][:80]

        if key in seen:
            continue

        # ✅ ลด strict → กันข่าวหาย
        if any(k in text for k in KEYWORDS) or len(text) > 60:
            seen.add(key)
            filtered.append(a)

    return filtered[:8]  # ไม่เยอะเกิน → ประหยัด token


# ------------------ PROMPT ------------------

def build_prompt(articles):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in articles
    )

    return f"""
คุณคือ analyst ที่โฟกัส AI + Energy

ข่าว:
{news_text}

ตอบแบบ "signal เท่านั้น" (ไม่เล่าข่าว):

🧠 AI Cycle
- ยังไป / เริ่มชะลอ / เสี่ยง
- AI_SCORE: X/10 (มีเหตุผลสั้นๆ)

🔄 Rotation
- เงินไหลไปไหน (chip / infra / energy)

⚡ Energy Theme
- ENERGY_SCORE: X/10 (มีเหตุผลสั้นๆ)

📊 Impact
- chip:
- infra:
- energy:

🎯 Action (1 บรรทัด)
"""


# ------------------ SCORE PARSER ------------------

import re

def extract_score(text, label):
    try:
        pattern = rf"{label}:\s*(\d+)/10"
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    except:
        pass
    return None


# ------------------ MAIN ------------------

def main():
    try:
        raw = fetch_news_multi(QUERIES)
        news = filter_articles(raw)

        print(f"[DEBUG] RAW: {len(raw)} | FILTERED: {len(news)}")

        # ✅ fallback ถ้าข่าวน้อย
        if len(news) < 3:
            print("[DEBUG] Using fallback queries...")
            raw = fetch_news_multi(FALLBACK_QUERIES)
            news = filter_articles(raw)

        # ✅ guard กัน Claude ตอบมั่ว
        if not news:
            send_plain("🌙 Night Signal — ไม่มีข่าวสำคัญในรอบนี้")
            return

        prompt = build_prompt(news)
        summary = ask(prompt)

        ai_score = extract_score(summary, "AI_SCORE")
        energy_score = extract_score(summary, "ENERGY_SCORE")

        score_line = ""
        if ai_score is not None and energy_score is not None:
            score_line = f"\n\n📊 Score → AI: {ai_score}/10 | Energy: {energy_score}/10"

        send_plain(
            f"🌙 Night Signal — {datetime.now().strftime('%d/%m %H:%M')}\n\n"
            f"{summary.strip()}{score_line}"
        )

    except Exception as e:
        send_error("night_news", e)
        raise


if __name__ == "__main__":
    main()