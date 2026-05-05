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

# 🌏 กว้าง (กัน echo chamber)
MACRO_QUERIES = [
    "global economy news",
    "central bank inflation interest rate",
    "geopolitics US China economy",
    "stock market outlook analyst",
]

# ⚙️ theme คุณ
THEME_QUERIES = [
    "AI data center Nvidia Microsoft Google",
    "semiconductor AI chip demand",
    "electricity demand data center energy",
    "power grid data center capacity",
]


# ------------------ FETCH ------------------

def fetch_news(queries, hours=12):
    results = []
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

            results.append({
                "title": e.get("title", ""),
                "desc": e.get("summary", "")[:120],
            })

    return results


def dedupe(articles):
    seen = set()
    out = []

    for a in articles:
        key = a["title"][:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(a)

    return out[:8]


# ------------------ PROMPT ------------------

def build_prompt(macro, theme):
    macro_text = "\n".join(f"- {a['title']}" for a in macro[:5])
    theme_text = "\n".join(f"- {a['title']}" for a in theme[:5])

    return f"""
คุณคือ macro + thematic investor

ข่าวภาพใหญ่:
{macro_text}

ข่าว theme (AI / chip / energy):
{theme_text}

สรุปแบบ “เข้าใจง่าย + ครบ + ไม่ bias”

Format:

🌏 Market Pulse
- สรุป macro 2-3 ข้อ (rewrite ให้อ่านง่าย)

⚙️ AI / Infra / Energy
- สรุป theme 3-4 ข้อ (rewrite)

🧠 สรุปภาพ
AI: X/10 → อธิบายสั้น
Energy: X/10 → อธิบายสั้น

🔄 เงินกำลังไหล:
1 บรรทัด

📊 ผลต่อพอร์ต:
+ 
= 
- 

🎯 Action:
1 ประโยค

❗ ห้ามใช้ศัพท์ยาก
❗ rewrite ให้อ่านเหมือนคนเล่า
❗ ไม่ต้องยาว
"""


# ------------------ MAIN ------------------

def main():
    try:
        macro_raw = fetch_news(MACRO_QUERIES)
        theme_raw = fetch_news(THEME_QUERIES)

        macro = dedupe(macro_raw)
        theme = dedupe(theme_raw)

        if not macro and not theme:
            send_plain("🌙 Night Signal — ไม่มีข่าวสำคัญ")
            return

        summary = ask(build_prompt(macro, theme))

        send_plain(
            f"🌙 Night Signal — {datetime.now().strftime('%d/%m %H:%M')}\n\n"
            f"{summary.strip()}"
        )

    except Exception as e:
        send_error("night_news", e)
        raise


if __name__ == "__main__":
    main()
