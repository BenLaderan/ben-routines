print("market_pulse starting...")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import json
    import feedparser
    import anthropic
    import yfinance as yf
    from datetime import datetime, timedelta, timezone
    from email.utils import parsedate_to_datetime
    from urllib.parse import quote_plus
    from pathlib import Path
    from shared.telegram import send_plain, send_error
except Exception as e:
    print(f"Import error: {e}")
    raise

# ── Portfolio ────────────────────────────────────────────────────────────────
PORTFOLIO = {
    "NVDA":  {"theme": "AI_compute",    "shares": 1.872474,  "cost": 203.1804},
    "AVGO":  {"theme": "semiconductor", "shares": 0.7831552, "cost": 406.3945},
    "MU":    {"theme": "memory",        "shares": 0.2768732, "cost": 508.2108},
    "VRT":   {"theme": "data_center",   "shares": 0.3311679, "cost": 310.3259},
    "VST":   {"theme": "power",         "shares": 0.8928541, "cost": 159.8357},
    "CEG":   {"theme": "power",         "shares": 0.2996938, "cost": 309.6160},
    "JBL":   {"theme": "electronics",   "shares": 0.2752514, "cost": 337.11},
    "FN":    {"theme": "electronics",   "shares": 0.2754655, "cost": 663.0593},
    "ANET":  {"theme": "network",       "shares": 0.5440922, "cost": 165.3580},
    "MRSH":  {"theme": "industrial",    "shares": 0.5103396, "cost": 167.1240},
    "CW":    {"theme": "industrial",    "shares": 0.0449886, "cost": 720.6260},
    "BWXT":  {"theme": "nuclear",       "shares": 0.1077252, "cost": 214.62},
    "CCJ":   {"theme": "uranium",       "shares": 0.1520284, "cost": 121.6220},
    "NXE":   {"theme": "uranium",       "shares": 0.7462084, "cost": 12.3960},
    "LEU":   {"theme": "uranium",       "shares": 0.0427672, "cost": 204.1280},
    "PLPC":  {"theme": "grid",          "shares": 0.3853151, "cost": 315.4820},
    "WMB":   {"theme": "gas",           "shares": 1.6178662, "cost": 75.1360},
    "BKV":   {"theme": "gas",           "shares": 3.8608198, "cost": 31.47},
}

# ── News RSS ─────────────────────────────────────────────────────────────────
RSS_QUERIES = [
    ("macro",    "Federal Reserve interest rates CPI inflation GDP economy"),
    ("energy",   "oil gas nuclear uranium energy power grid"),
    ("ai_infra", "artificial intelligence data center semiconductor nvidia chips"),
    ("markets",  "S&P500 NASDAQ stock market risk sentiment earnings"),
]

MODEL = "claude-haiku-4-5-20251001"
STATE_FILE = Path("data/market_state.json")
DEFAULT_STATE = {
    "regime": "unknown",
    "fed_stance": "unknown",
    "liquidity": "unknown",
    "date": "never",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ask(prompt: str, max_tokens: int = 1024) -> str:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── Layer 1: News Ingestion ───────────────────────────────────────────────────
def fetch_news(hours: int = 20) -> list[dict]:
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for label, query in RSS_QUERIES:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            try:
                pub = parsedate_to_datetime(entry.published)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    continue
            except Exception:
                continue
            articles.append({
                "cat": label,
                "title": entry.get("title", ""),
                "summary": (entry.get("summary", "") or "")[:150],
                "time": pub.strftime("%H:%M UTC"),
            })
            count += 1
            if count >= 6:
                break
        print(f"[RSS] {label}: {count} articles")
    return articles


# ── Portfolio prices ──────────────────────────────────────────────────────────
def fetch_prices() -> dict:
    results = {}
    for ticker, meta in PORTFOLIO.items():
        try:
            hist = yf.Ticker(ticker).history(period="3d")
            hist = hist["Close"].dropna()
            if len(hist) >= 2:
                prev, last = float(hist.iloc[-2]), float(hist.iloc[-1])
                pct = ((last - prev) / prev) * 100
                pnl = ((last - meta["cost"]) / meta["cost"]) * 100
                results[ticker] = {"price": round(last, 2), "chg": round(pct, 2), "pnl": round(pnl, 2)}
            elif len(hist) == 1:
                last = float(hist.iloc[-1])
                pnl = ((last - meta["cost"]) / meta["cost"]) * 100
                results[ticker] = {"price": round(last, 2), "chg": None, "pnl": round(pnl, 2)}
            else:
                results[ticker] = {"price": None, "chg": None, "pnl": None}
        except Exception as ex:
            print(f"[price] {ticker}: {ex}")
            results[ticker] = {"price": None, "chg": None, "pnl": None}
    return results


# ── State persistence ─────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_STATE.copy()


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"[state] saved: {state}")


# ── Layer 2+3: Market Pulse + Regime Detection ────────────────────────────────
def analyze_regime(articles: list[dict], prev: dict) -> dict:
    news_text = "\n".join(
        f"[{a['cat'].upper()} {a['time']}] {a['title']}"
        + (f" — {a['summary']}" if a["summary"] else "")
        for a in articles
    )

    prompt = f"""คุณคือนักวิเคราะห์ macro ให้วิเคราะห์หัวข้อข่าวในช่วง 20 ชั่วโมงที่ผ่านมา

ข่าว:
{news_text}

สภาวะเมื่อวาน:
regime={prev['regime']} | fed_stance={prev['fed_stance']} | liquidity={prev['liquidity']} | date={prev['date']}

ตอบเป็น JSON เท่านั้น (ห้ามใส่ markdown):
{{
  "regime": "risk_on" | "risk_off" | "neutral",
  "fed_stance": "hawkish" | "dovish" | "neutral",
  "liquidity": "expanding" | "tightening" | "neutral",
  "regime_changed": true | false,
  "change_reason": "เหตุผล 1 ประโยคภาษาไทยถ้าเปลี่ยน ถ้าไม่เปลี่ยนให้ใส่ null",
  "macro_summary": "สรุปภาพรวม macro วันนี้ 2 ประโยคภาษาไทย",
  "key_drivers": ["ปัจจัยที่1", "ปัจจัยที่2", "ปัจจัยที่3"]
}}

ตั้ง regime_changed=true เฉพาะเมื่อ regime/fed_stance/liquidity เปลี่ยนอย่างมีนัยสำคัญจากเมื่อวาน
ถ้า date เมื่อวานคือ 'never' ให้ตั้ง regime_changed=false"""

    raw = _ask(prompt, max_tokens=700)
    print(f"[regime raw] {raw[:400]}")

    try:
        clean = raw.strip()
        if "```" in clean:
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else parts[0]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"[regime parse error] {e}")
        return {
            "regime": "neutral",
            "fed_stance": "neutral",
            "liquidity": "neutral",
            "regime_changed": False,
            "change_reason": None,
            "macro_summary": raw[:300],
            "key_drivers": [],
        }


# ── Layer 4: Portfolio Impact Mapping ────────────────────────────────────────
def map_portfolio_impact(regime: dict, prices: dict) -> str:
    rows = []
    for ticker, meta in PORTFOLIO.items():
        p = prices.get(ticker, {})
        price_str = f"${p['price']:.2f}" if p.get("price") else "N/A"
        chg_str = (f"{'+' if p['chg'] >= 0 else ''}{p['chg']:.1f}%" if p.get("chg") is not None else "N/A")
        pnl_str = (f"{'+' if p['pnl'] >= 0 else ''}{p['pnl']:.1f}%" if p.get("pnl") is not None else "N/A")
        rows.append(f"{ticker}({meta['theme']}): {price_str} chg={chg_str} P&L={pnl_str}")

    prompt = f"""คุณคือนักวิเคราะห์พอร์ตการลงทุน ให้ map สภาวะ macro วันนี้ไปยังผลกระทบต่อหุ้นแต่ละตัว

สภาวะตลาดวันนี้:
- โหมด: {regime['regime']}
- Fed: {regime['fed_stance']}
- สภาพคล่อง: {regime['liquidity']}
- ภาพรวม: {regime['macro_summary']}
- ปัจจัยหลัก: {', '.join(regime.get('key_drivers', []))}

พอร์ตหุ้น (Ticker / theme / ราคาล่าสุด / เปลี่ยนแปลง / กำไร-ขาดทุนจากต้นทุน):
{chr(10).join(rows)}

ตอบเป็นภาษาไทย ใช้รูปแบบนี้เท่านั้น:

🟢 ได้ประโยชน์
• TICKER (theme) — เหตุผล

🔴 เสียประโยชน์
• TICKER (theme) — เหตุผล

⚪ เฉย ๆ
• TICKER (theme) — เหตุผล

สรุป: 1-2 ประโยค บอกสิ่งที่ต้องระวังหรือโอกาสที่น่าสนใจสำหรับพอร์ตนี้วันนี้
(ศัพท์เทคนิคอย่าง risk-on, hawkish, liquidity ใช้ภาษาอังกฤษได้)"""

    return _ask(prompt, max_tokens=2000)


# ── Format Telegram message ───────────────────────────────────────────────────
def format_message(regime: dict, impact: str, now: datetime) -> str:
    date_str = now.strftime("%d/%m/%Y")

    regime_th = {"risk_on": "🟢 Risk-On (รับความเสี่ยง)", "risk_off": "🔴 Risk-Off (หลีกเลี่ยงความเสี่ยง)", "neutral": "🟡 Neutral (เฝ้าดู)"}.get(regime["regime"], "⚪ ไม่ชัดเจน")
    fed_th    = {"hawkish": "🦅 Hawkish (คุมเข้ม)", "dovish": "🕊️ Dovish (ผ่อนคลาย)", "neutral": "⚖️ Neutral"}.get(regime["fed_stance"], regime["fed_stance"])
    liq_th    = {"expanding": "💧↑ ขยายตัว", "tightening": "💧↓ ตึงตัว", "neutral": "💧 Neutral"}.get(regime["liquidity"], regime["liquidity"])

    lines = [
        f"📊 Market Pulse — {date_str}",
        "━━━━━━━━━━━━━━━━━━",
        "🌡️ ภาพรวม Macro วันนี้",
        f"สภาวะตลาด:  {regime_th}",
        f"ท่าที Fed:   {fed_th}",
        f"สภาพคล่อง: {liq_th}",
        "",
        f"📝 {regime['macro_summary']}",
        "",
    ]

    if regime.get("regime_changed"):
        lines += [
            "━━━━━━━━━━━━━━━━━━",
            "🚨 สัญญาณ Regime เปลี่ยน!",
            regime.get("change_reason") or "สภาวะตลาดเปลี่ยนจากเมื่อวาน",
            "",
        ]

    lines += [
        "━━━━━━━━━━━━━━━━━━",
        "💼 ผลกระทบต่อพอร์ต",
        "",
        impact.strip(),
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now(timezone.utc)
    print(f"[market_pulse] {now.isoformat()}")

    try:
        articles = fetch_news(hours=20)
        print(f"[market_pulse] {len(articles)} articles fetched")

        prices = fetch_prices()

        prev_state = load_state()
        print(f"[market_pulse] prev_state: {prev_state}")

        regime = analyze_regime(articles, prev_state)
        print(f"[market_pulse] regime: {regime}")

        save_state({
            "regime":     regime["regime"],
            "fed_stance": regime["fed_stance"],
            "liquidity":  regime["liquidity"],
            "date":       now.strftime("%Y-%m-%d"),
        })

        impact = map_portfolio_impact(regime, prices)

        message = format_message(regime, impact, now)
        send_plain(message)
        print("[market_pulse] sent")

    except Exception as e:
        print(f"[market_pulse] error: {e}")
        send_error("market_pulse", e)
        raise


if __name__ == "__main__":
    main()
