import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.claude_client import ask
from shared.telegram import send_plain, send_error

PROMPT = """
คุณคือผู้ช่วยส่วนตัวของเบน

เขียนประโยคสร้างแรงบันดาลใจสำหรับเบน 1 ประโยค ไม่เกิน 3 บรรทัด โดย:
- พูดกับ "เบน" โดยตรง หรือหยิบ quote ที่น่าสนใจมาเล่า
- เน้นไปที่การสร้างแรงบันดาลใจ กระตุ้นให้ลงมือทำ
- กระชับ จริงใจ มีพลัง

ตอบเป็นภาษาไทย ไม่ต้องมีคำนำหรือคำอธิบายเพิ่มเติม
"""


def main():
    try:
        message = ask(PROMPT)
        send_plain(message.strip())
    except Exception as e:
        send_error("daily_intro", e)
        raise


if __name__ == "__main__":
    main()
