print("celeb_watch starting...")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from datetime import datetime
    from shared.claude_client import ask
    from shared.telegram import send_plain, send_error
except Exception as e:
    print(f"Import error: {e}")
    raise

PROMPT = """ค้นหาข่าวล่าสุดในรอบ 24 ชั่วโมงเกี่ยวกับหลิงหลิง (นักร้อง) และออมกรณ์นภัส (นักแสดงไทย) จาก social media และสื่อไทย

ถ้ามีข่าว ให้สรุปเป็นภาษาไทยเหมือนเพื่อนเล่าให้ฟัง แบ่งตามชื่อ ไม่เกิน 5 บรรทัดต่อคน
ถ้าไม่มีข่าวเลย ให้ตอบแค่คำว่า NO_NEWS เท่านั้น ห้ามมีข้อความอื่น"""


def main():
    try:
        response = ask(PROMPT).strip()
        print(f"Claude response preview: {response[:80]}")

        if response == "NO_NEWS" or response.startswith("NO_NEWS"):
            send_plain("⭐ Celeb Watch — วันนี้หลิงออมเงียบมากครับ ไม่มีอะไรอัพเดท")
        else:
            send_plain(f"⭐ Celeb Watch — {datetime.now().strftime('%d/%m/%Y')}\n\n{response}")
    except Exception as e:
        print(f"Runtime error: {e}")
        send_error("celeb_watch", e)
        raise


if __name__ == "__main__":
    main()
