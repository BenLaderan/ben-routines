import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error


# ------------------ CONFIG ------------------

QUERIES = [
    "AI data center Nvidia Microsoft Google",
    "cloud computing AI demand data center",
    "semiconductor industry AI chip demand",
    "electricity demand data center energy",
]

FALLBACK_QUERIES = [
    "AI technology news",
    "energy market news",
]

KEYWORDS = [
    "ai", "data center", "cloud", "gpu",
    "chip", "semiconductor",
    "energy", "electricity", "power",
    "demand", "growth", "investment",
    "capacity", "infrastructure"
]

BAD_WORDS = ["celebrity", "movie", "sports"]


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
            desc = e.get("summary", "")[:120]
            link = e.get("link", "")

            all_articles.append({
                "title": title,
                "desc": desc,
                "link": link
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

        if any(b in text for b in BAD_WORDS):
            continue

        if any(k in text for k in KEYWORDS) or len(text) > 60:
            seen.add(key)
            filtered.append(a)

    return filtered[:6]  # จำกัดให้สั้น


# ------------------ FORMAT HEADLINES ------------------

def format_headlines(articles):
    lines = []

    for a in articles:
        title = a["title"]
        link = a["link"]

        lines.append(f"- {title}\n  🔗 {link}")

    return "\n".join(lines)


# ------------------ PROMPT ------------------

def build_prompt(articles):
    news_text = "\n".join(
        f"- {a['title']}" for a in articles
    )

    return f"""
คุณคือ hedge fund analyst

ข่าว:
{news_text}

สรุปแบบ “สั้น + ใช้ตัดสินใจได้ทันที”

Format:

📰 ข่าวสำคัญ (3-5 ข้อ)
- headline → context สั้นๆ (เช่น เพิ่มลงทุน / ลดงบ / demand โต)

🧠 AI: X/10 → (ยังไป / ชะลอ / เสี่ยง) + เหตุผลสั้น
⚡ Energy: X/10 → (แรง / กลาง / อ่อน) + เหตุผลสั้น

🔄 เงินไหล:
1 บรรทัด

📊 ผลต่อพอร์ต:
+ (เพิ่ม)
= (ถือ)
- (ลด)

🎯 วันนี้:
1 ประโยคสั่งการ

❗ ห้ามยาว
❗ ห้ามเล่าข่าวยาว
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

        # fallback ถ้าข่าวน้อย
        if len(news) < 3:
            print("[DEBUG] Using fallback...")
            raw = fetch_news_multi(FALLBACK_QUERIES)
            news = filter_articles(raw)

        if not news:
            send_plain("🌙 Night Signal — ไม่มีข่าวสำคัญในรอบนี้")
            return

        # 📰 headline + link
        headline_block = format_headlines(news)

        # 🤖 summary
        summary = ask(build_prompt(news))

        ai_score = extract_score(summary, "AI")
        energy_score = extract_score(summary, "Energy")

        score_line = ""
        if ai_score is not None and energy_score is not None:
            score_line = f"\n📊 Score → AI: {ai_score}/10 | Energy: {energy_score}/10"

        send_plain(
            f"🌙 Night Signal — {datetime.now().strftime('%d/%m %H:%M')}\n\n"
            f"📰 Headlines:\n{headline_block}\n\n"
            f"{summary.strip()}\n"
            f"{score_line}"
        )

    except Exception as e:
        send_error("night_news", e)
        raise


if __name__ == "__main__":
    main()