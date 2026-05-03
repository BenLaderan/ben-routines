import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

# ✅ เพิ่ม nuclear เข้าไป
STOCKS = [
    "NVDA", "AVGO", "MU", "ANET", "VRT", "VST",
    "FN", "JBL", "CEG",
    "CW", "BWXT", "CCJ", "NXE", "LEU"
]

QUERIES = [
    "NVIDIA earnings guidance AI demand",
    "hyperscaler capex Microsoft Amazon Google cloud",
    "data center electricity nuclear power AI",
    "uranium nuclear energy demand AI data center",
    "AVGO MU ANET VRT earnings outlook"
]

KEYWORDS = [
    "capex", "guidance", "demand", "data center",
    "AI", "GPU", "cloud", "energy", "electricity",
    "nuclear", "uranium", "power", "earnings"
]

CRITICAL_KEYWORDS = [
    "capex cut", "demand slowdown",
    "guidance lowered", "data center delay"
]


# ------------------ NEWS ------------------

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


# ------------------ PROMPT ------------------

def build_prompt(news):
    news_text = "\n".join(
        f"- {a['title']} | {a['desc']}" for a in news
    )

    return f"""
คุณคือ analyst ที่โฟกัส AI + Energy theme

ข่าว:
{news_text}

ให้วิเคราะห์และ "ให้คะแนน" โดยใช้ logic การลงทุนจริง

ตอบตาม format นี้เท่านั้น:

🧠 AI Cycle
สรุป: ยังไป / เริ่มชะลอ / เสี่ยง

AI_SCORE: X/10
(ให้เหตุผล 1-2 บรรทัด)

🔄 Rotation
เงินกำลังไหลไป sector ไหน (chip / infra / energy / อื่นๆ ที่โดดเด่น)

⚡ Energy Theme
ENERGY_SCORE: X/10
(ให้เหตุผล 1-2 บรรทัด)

📊 Impact ต่อพอร์ต:
NVDA, AVGO, MU, ANET, VRT, VST, FN, JBL, CEG, CW, BWXT, CCJ, NXE, LEU

→ สรุปเป็นกลุ่ม:
- chip:
- infra:
- energy:
- นอกเหนือจาก 3 กลุ่มด้านบนและโดดเด่นที่สุด

🎯 สรุป 1 บรรทัด (action ชัดๆ)
"""


# ------------------ SCORE PARSER ------------------

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
        raw_news = fetch_news_multi(QUERIES)
        news = filter_articles(raw_news)

        alerts = detect_critical(news)
        if alerts:
            send_plain("🚨 NIGHT WARNING:\n" + "\n".join(alerts[:3]))

        prompt = build_prompt(news)
        summary = ask(prompt)

        # ✅ extract score (optional ใช้ต่อยอดได้)
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
