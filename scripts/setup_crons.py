"""
setup_crons.py — สร้าง cron jobs ทั้งหมดบน cron-job.org ครั้งเดียวจบ

การใช้งาน:
  GITHUB_TOKEN=ghp_xxx CRONJOB_API_KEY=xxx python scripts/setup_crons.py

ขั้นตอนเตรียม:
  1. GitHub PAT → https://github.com/settings/tokens
     สร้าง token ใหม่ (Classic) ติ๊ก scope: workflow
  2. cron-job.org API key → https://console.cron-job.org/settings
     Sign up ฟรี → Settings → API
"""

import os
import sys
import json
import requests

GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN")
CRONJOB_API_KEY = os.environ.get("CRONJOB_API_KEY")

REPO     = "BenLaderan/ben-routines"
WORKFLOW = "routines.yml"

GITHUB_DISPATCH_URL = (
    f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
)

# ── Job definitions ──────────────────────────────────────────────────────────
# schedule: เวลา UTC, wdays: [-1]=ทุกวัน, [0,3]=อาทิตย์+พุธ
JOBS = [
    {
        "title":    "ben-routines: daily_intro (07:00 TH)",
        "job_name": "daily_intro",
        "hours":    [0],
        "minutes":  [0],
        "wdays":    [-1],
    },
    {
        "title":    "ben-routines: morning_news (09:00 TH)",
        "job_name": "morning_news",
        "hours":    [2],
        "minutes":  [0],
        "wdays":    [-1],
    },
    {
        "title":    "ben-routines: celeb_watch (20:00 TH)",
        "job_name": "celeb_watch",
        "hours":    [13],
        "minutes":  [0],
        "wdays":    [-1],
    },
    {
        "title":    "ben-routines: market_pulse (20:00 TH)",
        "job_name": "market_pulse",
        "hours":    [13],
        "minutes":  [5],   # 5 นาทีหลัง celeb_watch กัน race
        "wdays":    [-1],
    },
    {
        "title":    "ben-routines: night_shift (23:00 TH)",
        "job_name": "night_shift",
        "hours":    [16],
        "minutes":  [0],
        "wdays":    [-1],
    },
    {
        "title":    "ben-routines: trend_update (14:00 TH Wed+Sun)",
        "job_name": "trend_update",
        "hours":    [7],
        "minutes":  [0],
        "wdays":    [0, 3],   # 0=อาทิตย์, 3=พุธ
    },
]


def build_cronjob_payload(job: dict) -> dict:
    body = json.dumps({"ref": "main", "inputs": {"job": job["job_name"]}})
    return {
        "job": {
            "url": GITHUB_DISPATCH_URL,
            "enabled": True,
            "title": job["title"],
            "saveResponses": True,
            "schedule": {
                "timezone": "UTC",
                "expiresAt": 0,
                "hours":    job["hours"],
                "mdays":    [-1],
                "minutes":  job["minutes"],
                "months":   [-1],
                "wdays":    job["wdays"],
            },
            "requestMethod": 1,  # POST
            "extendedData": {
                "body": body,
                "headers": [
                    {"name": "Authorization",  "value": f"Bearer {GITHUB_TOKEN}"},
                    {"name": "Content-Type",   "value": "application/json"},
                    {"name": "Accept",         "value": "application/vnd.github+json"},
                    {"name": "X-GitHub-Api-Version", "value": "2022-11-28"},
                ],
            },
        }
    }


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


def create_job(payload: dict) -> dict:
    resp = requests.put(
        "https://api.cron-job.org/jobs",
        headers={
            "Authorization": f"Bearer {CRONJOB_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    if not GITHUB_TOKEN or not CRONJOB_API_KEY:
        print("Error: ต้องตั้ง environment variables ก่อน")
        print("  export GITHUB_TOKEN=ghp_xxx")
        print("  export CRONJOB_API_KEY=xxx")
        sys.exit(1)

    print("── ลบ job เก่าของ ben-routines (ถ้ามี) ─────────────────")
    existing = list_existing_jobs()
    deleted = 0
    for j in existing:
        if "ben-routines" in j.get("title", ""):
            delete_job(j["jobId"])
            print(f"  ลบ: {j['title']} (id={j['jobId']})")
            deleted += 1
    if deleted == 0:
        print("  ไม่มี job เก่า")

    print("\n── สร้าง job ใหม่ ────────────────────────────────────────")
    for job in JOBS:
        payload = build_cronjob_payload(job)
        result  = create_job(payload)
        job_id  = result.get("jobId", "?")
        h, m    = job["hours"][0], job["minutes"][0]
        wday_str = "ทุกวัน" if job["wdays"] == [-1] else "พุธ+อาทิตย์"
        print(f"  ✓ {job['title']}")
        print(f"    → รัน {h:02d}:{m:02d} UTC ({wday_str})  |  job id: {job_id}")

    print("\n✅ เสร็จ — cron jobs พร้อมใช้งานแล้ว")
    print("   ดูได้ที่ https://console.cron-job.org")


if __name__ == "__main__":
    main()
