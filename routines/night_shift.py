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

PORTFOLIO_THEMES = “””
AI / ชิป: NVDA, AVGO, MU, ANET
Data Center / ไฟฟ้า: VRT, VST, CEG, PLPC
ยูเรเนียม / นิวเคลียร์: CCJ, NXE, LEU, BWXT
อุตสาหกรรม / อิเล็กทรอนิกส์: JBL, FN, MRSH, CW
ก๊าซธรรมชาติ: WMB, BKV
“””


def build_prompt(macro, theme):
    macro_text = “\n”.join(f”- {a['title']}” for a in macro[:5])
    theme_text = “\n”.join(f”- {a['title']}” for a in theme[:5])

    return f”””คุณคือเพื่อนที่ติดตามตลาดหุ้นอย่างใกล้ชิด กำลังสรุปข่าวก่อนนอนให้ฟัง
เขียนภาษาไทยธรรมชาติ เหมือนคุยกัน ไม่ใช่รายงานทางการ
ห้ามแปลข่าวตรงๆ — ให้เล่าว่าเกิดอะไรขึ้นและมันหมายความว่าอะไรสำหรับเรา
ศัพท์เทคนิคอย่าง Fed, AI, chip, hawkish ใช้ภาษาอังกฤษได้ แต่ต้องอธิบายให้เข้าใจเสมอ

ข่าวภาพใหญ่คืนนี้:
{macro_text}

ข่าว AI / Chip / พลังงาน:
{theme_text}

พอร์ตที่ถืออยู่ (แบ่งตามกลุ่ม):
{PORTFOLIO_THEMES}

เขียนให้ครบทุกหัวข้อนี้:

🌏 ภาพใหญ่คืนนี้
เล่า 2-3 เรื่องที่สำคัญ บอกว่าเกิดอะไรและทำไมถึงน่าสนใจ

⚙️ AI / Chip / พลังงาน
เล่า 2-3 เรื่องในกลุ่มนี้ โยงกับกระแสที่เห็นอยู่

🧠 ภาพรวม
AI ตอนนี้ร้อนแค่ไหน: X/10 — อธิบาย 1 บรรทัด
พลังงาน/นิวเคลียร์: X/10 — อธิบาย 1 บรรทัด

💸 เงินกำลังไหลไปทางไหน
1 บรรทัด บอกตรงๆ

📊 พอร์ตเราได้รับผลยังไง
🟢 กลุ่มที่น่าจะได้ประโยชน์ — บอก ticker และเหตุผลสั้นๆ
🔴 กลุ่มที่อาจถูกกดดัน — บอก ticker และเหตุผลสั้นๆ
⚪ กลุ่มที่ทรงตัว

🎯 คืนนี้ต้องรู้อะไร
1 ประโยคสรุปสิ่งที่สำคัญที่สุด”””


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
