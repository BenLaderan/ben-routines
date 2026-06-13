"""
setup_crons.py — ลบ job ทั้งหมดของ ben-routines ออกจาก cron-job.org

การใช้งาน:
  CRONJOB_API_KEY=xxx python scripts/setup_crons.py
"""

import os
import sys
import requests

CRONJOB_API_KEY = os.environ.get("CRONJOB_API_KEY")

def list_existing_jobs() -> list[dict]:
    resp = requests.get(
        "https://api.cron-job.org/jobs",
        headers={"Authorization": f"Bearer {CRONJOB_API_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("jobs", [])

def delete_job(job_id: int) -> None:
    requests.delete(
        f"https://api.cron-job.org/jobs/{job_id}",
        headers={"Authorization": f"Bearer {CRONJOB_API_KEY}"},
        timeout=15,
    )

def main():
    if not CRONJOB_API_KEY:
        print("Error: ต้องตั้ง environment variable CRONJOB_API_KEY ก่อน")
        sys.exit(1)

    print("── ลบ job ของ ben-routines ─────────────────")
    existing = list_existing_jobs()
    deleted = 0
    for j in existing:
        if "ben-routines" in j.get("title", ""):
            delete_job(j["jobId"])
            print(f"  ลบ: {j['title']} (id={j['jobId']})")
            deleted += 1
    
    if deleted == 0:
        print("  ไม่พบ job ที่เกี่ยวข้อง")
    else:
        print(f"\n✅ ลบเสร็จสิ้นทั้งหมด {deleted} jobs")

if __name__ == "__main__":
    main()
