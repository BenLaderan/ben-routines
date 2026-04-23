print("celeb_watch starting...")

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

RSS_FEEDS = {
    "หลิงหลิง": "https://news.google.com/rss/search?q=หลิงหลิง+นักร้อง&hl=th&gl=TH&ceid=TH:th",
    "ออมกรณ์นภัส": "https://news.google.com/rss/search?q=ออมกรณ์นภัส&hl=th&gl=TH&ceid=TH:th",
}

CLAUDE_FALLBACK_PROMPT = """ค้นหาข่าวล่าสุดในรอบ 24 ชั่วโมงเกี่ยวกับหลิงหลิง (นักร้อง) และออมกรณ์นภัส (นักแสดงไทย)

ถ้ามีข่าว ให้สรุปเป็นภาษาไทยเหมือนเพื่อนเล่าให้ฟัง แบ่งตามชื่อ ไม่เกิน 5 บรรทัดต่อคน
ถ้าไม่มีข่าวเลย ให้ตอบแค่คำว่า NO_NEWS เท่านั้น"""


def fetch_rss(label: str, url: str, hours: int = 24) -> list[dict]:
    feed = feedparser.parse(url)
    status = getattr(feed, "status", None)
    print(f"[RSS] {label}: entries={len(feed.entries)} status={status}")

    if status in (429, 403) or len(feed.entries) == 0:
        return None  # signal to use fallback

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = []
    for entry in feed.entries:
        try:
            pub = parsedate_to_datetime(entry.published)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub < cutoff:
                continue
        except Exception:
            continue
        results.append({
            "title": entry.get("title", ""),
            "source": entry.get("source", {}).get("title", ""),
            "published": pub.strftime("%d/%m %H:%M"),
        })
    return results


def build_prompt(all_articles: dict[str, list[dict]]) -> str:
    sections = []
    for label, articles in all_articles.items():
        if articles:
            lines = "\n".join(
                f"- [{a['published']}] {a['title']} ({a['source']})"
                for a in articles
            )
            sections.append(f"ข่าวเกี่ยวกับ {label}:\n{lines}")
    combined = "\n\n".join(sections)
    return f"""คุณคือผู้ช่วยส่วนตัวที่ติดตามข่าวดาราให้เบน

ข่าวที่พบจาก Google News (24 ชั่วโมงที่ผ่านมา):
{combined}

สรุปเป็นภาษาไทย เขียนเหมือนเพื่อนเล่าให้ฟัง:
- แบ่งตามชื่อดารา
- เล่าว่าเกิดอะไรขึ้น บรรยากาศเป็นยังไง
- ถ้าข่าวหลิงหลิงกับออมกรณ์นภัสเชื่อมกัน ให้รวมเล่าด้วยกัน
- ไม่ต้องมีคำนำ กระชับ ไม่เกิน 5 บรรทัดต่อคน"""


def main():
    try:
        all_articles: dict[str, list[dict]] = {}
        use_fallback = False

        for label, url in RSS_FEEDS.items():
            result = fetch_rss(label, url, hours=24)
            if result is None:
                print(f"[RSS] {label}: blocked or empty — will use Claude fallback")
                use_fallback = True
                break
            all_articles[label] = result

        if use_fallback:
            print("Using Claude API fallback...")
            response = ask(CLAUDE_FALLBACK_PROMPT).strip()
            if response.upper().startswith("NO_NEWS"):
                send_plain("⭐ Celeb Watch — วันนี้หลิงออมเงียบมากครับ ไม่มีอะไรอัพเดท")
            else:
                send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{response}")
            return

        total = sum(len(v) for v in all_articles.values())
        print(f"Total articles after filter: {total}")

        if total == 0:
            send_plain("⭐ Celeb Watch — วันนี้หลิงออมเงียบมากครับ ไม่มีอะไรอัพเดท")
            return

        summary = ask(build_prompt(all_articles))
        send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{summary.strip()}")

    except Exception as e:
        print(f"Runtime error: {e}")
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()
