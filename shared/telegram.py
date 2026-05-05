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


def send_long(text: str, limit: int = 4000) -> None:
    """Send a message, splitting at newlines when it exceeds Telegram's 4096-char limit."""
    if len(text) <= limit:
        send_plain(text)
        return
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            send_plain(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunk = remaining[:split_at].rstrip()
        if chunk:
            send_plain(chunk)
        remaining = remaining[split_at:].lstrip("\n")


def send_error(source: str, error: Exception) -> None:
    """Send error notification — best-effort, never raises."""
    try:
        send_plain(f"[ERROR] {source}\n{type(error).__name__}: {error}")
    except Exception:
        pass
