import os
import re
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", str(text))


def send_message(text: str) -> dict:
    """Send a MarkdownV2-formatted message."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
    }
    resp = requests.post(f"{_BASE_URL}/sendMessage", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_plain(text: str) -> dict:
    """Send a plain-text message (no parse mode)."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }
    resp = requests.post(f"{_BASE_URL}/sendMessage", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_error(source: str, error: Exception) -> None:
    """Send error notification — best-effort, never raises."""
    try:
        send_plain(f"[ERROR] {source}\n{type(error).__name__}: {error}")
    except Exception:
        pass
