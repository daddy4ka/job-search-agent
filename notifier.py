import os
import requests
from datetime import datetime, timezone
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.dou import Job


def _get_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)


def _post_html(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": _get_chat_id(),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notifier] _post_html failed: {e}")
        return False


def send_job(job: Job) -> bool:
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = (
        f"💼 <b>{esc(job.title)}</b>\n"
        f"🏢 {esc(job.company)} · <i>{esc(job.source)}</i>\n"
        f'🔗 <a href="{job.url}">Відкрити вакансію</a>'
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": _get_chat_id(),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send for {job.id}: {e}")
        return False


def send_summary(source_counts, new_counts, started_at) -> None:
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    total_scraped = sum(source_counts.values())
    total_new = sum(new_counts.values())
    finished_at = datetime.now(timezone.utc)
    duration_sec = int((finished_at - started_at).total_seconds())
    duration_str = f"{duration_sec // 60}хв {duration_sec % 60}с"
    finished_str = finished_at.strftime("%d.%m.%Y %H:%M UTC")

    lines = [
        f"📊 Job scan · {finished_str} · {duration_str}",
        "",
    ]

    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        new_c = new_counts.get(source, 0)
        new_str = f" / {new_c}" if new_c > 0 else " / 0"
        lines.append(f"{esc(source):<20} {count}{new_str}")

    lines.append("")
    lines.append(f"всього / нових: {total_scraped} / {total_new}")

    _post_html("\n".join(lines))
