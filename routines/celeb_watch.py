print("celeb_watch optimized starting...")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import feedparser
    from datetime import datetime, timedelta, timezone
    from email.utils import parsedate_to_datetime
    from shared.claude_client import ask
    from shared.telegram import send_plain, send_error
except Exception as e:
    print(f"Import error: {e}")
    raise


# 🔥 เพิ่ม query “คู่”
RSS_FEEDS = {
    "หลิง": "https://news.google.com/rss/search?q=หลิงหลิงควอง&hl=th&gl=TH&ceid=TH:th",
    "ออม": "https://news.google.com/rss/search?q=ออมกรณ์นภัส&hl=th&gl=TH&ceid=TH:th",
    "หลิงออม": "https://news.google.com/rss/search?q=หลิงออม&hl=th&gl=TH&ceid=TH:th",
}

KEYWORDS = [
    "แฟนมีต", "ซีรีส์", "สัมภาษณ์", "กระแส",
    "ไวรัล", "ดราม่า", "งานอีเวนต์", "ประกาศ",
    "เจ้าความรัก", "แฟนคลับ", "คู่จิ้น", "พรีเซนเตอร์", 
    "BA", "live", "วาดฝันวันวิวาห์"
]


# ------------------ FETCH ------------------

def fetch_rss(label: str, url: str, hours: int = 24):
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
        except:
            continue

        title = entry.get("title", "")
        source = entry.get("source", {}).get("title", "")
        desc = entry.get("summary", "")[:120]

        results.append({
            "title": title,
            "desc": desc,
            "source": source,
            "published": pub.strftime("%d/%m %H:%M"),
        })

    return results


# ------------------ FILTER + DEDUPE ------------------

def filter_articles(articles):
    seen = set()
    filtered = []

    for a in articles:
        key = a["title"][:80]  # กันข่าวซ้ำ
        text = (a["title"] + " " + a["desc"]).lower()

        if key in seen:
            continue

        # 🔥 filter ให้เหลือข่าวที่ “มีสาระ”
        if any(k in text for k in KEYWORDS):
            seen.add(key)
            filtered.append(a)

    return filtered[:5]  # จำกัดไม่ให้ Claude อ่านเยอะเกิน


# ------------------ CLASSIFY ------------------

def classify_articles(all_articles):
    ling = []
    orm = []
    couple = []

    for label, articles in all_articles.items():
        for a in articles:
            text = (a["title"] + " " + a["desc"]).lower()

            if "หลิงออม" in text or ("หลิง" in text and "ออม" in text):
                couple.append(a)
            elif label == "หลิง":
                ling.append(a)
            elif label == "ออม":
                orm.append(a)

    return ling, orm, couple


# ------------------ PROMPT ------------------

def build_prompt(ling, orm, couple):
    def format_block(name, articles):
        if not articles:
            return f"{name}: ไม่มีข่าวสำคัญ"
        return name + ":\n" + "\n".join(
            f"- {a['title']}" for a in articles
        )

    text = "\n\n".join([
        format_block("หลิง", ling),
        format_block("ออม", orm),
        format_block("หลิงออม", couple),
    ])

    return f"""
คุณคือเพื่อนที่อัปเดตข่าวดาราให้แบบ “อินกระแส”

ข่าว:
{text}

สรุปเป็นภาษาไทยแบบสนุก อ่านง่าย แต่คม:

⭐ หลิง
- สรุป vibe + สิ่งที่เกิดขึ้น

⭐ ออม
- สรุป vibe + สิ่งที่เกิดขึ้น

💞 หลิงออม
- ถ้ามี interaction / โมเมนต์ ให้เล่า

🔥 กระแสวันนี้
- สรุปว่า: เงียบ / เริ่มมา / กำลังพีค
- ถ้ามีอะไรไวรัลให้บอก

❗ ไม่ต้องยาว (รวมไม่เกิน 10 บรรทัด)
"""


# ------------------ MAIN ------------------

def main():
    try:
        all_articles = {}

        for label, url in RSS_FEEDS.items():
            raw = fetch_rss(label, url)
            filtered = filter_articles(raw)
            all_articles[label] = filtered

        ling, orm, couple = classify_articles(all_articles)

        total = len(ling) + len(orm) + len(couple)

        if total == 0:
            send_plain("⭐ Celeb Watch — วันนี้หลิงออมเงียบ ไม่มีประเด็นใหญ่")
            return

        prompt = build_prompt(ling, orm, couple)
        summary = ask(prompt)

        send_plain(
            f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n"
            f"{summary.strip()}"
        )

    except Exception as e:
        print(f"Runtime error: {e}")
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()