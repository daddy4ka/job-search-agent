import os
import requests
from datetime import datetime, timezone
from scrapers.dou import Job


def _get_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")

def _get_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "")


def _post_html(text: str) -> bool:
    url = f"https://api.telegram.org/bot{_get_token()}/sendMessage"
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

    location_line = f"\n📍 {esc(job.location)}" if job.location else ""
    text = (
        f"💼 <b>{esc(job.title)}</b>\n"
        f"🏢 {esc(job.company)} · <i>{esc(job.source)}</i>"
        f"{location_line}\n"
        f'🔗 <a href="{job.url}">Відкрити вакансію</a>'
    )

    url = f"https://api.telegram.org/bot{_get_token()}/sendMessage"
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


def send_summary(source_counts, new_counts, started_at, all_sources=None) -> None:
    total_scraped = sum(source_counts.values())
    total_new = sum(new_counts.values())
    finished_at = datetime.now(timezone.utc)
    duration_sec = int((finished_at - started_at).total_seconds())
    duration_str = f"{duration_sec // 60}хв {duration_sec % 60}с"
    date_str = finished_at.strftime("%d.%m")

    def _bar(new, total, width=9):
        if total == 0 or new == 0:
            return "░" * width
        filled = max(1, round(new / total * width))
        return "█" * filled + "░" * (width - filled)

    NAME_W = 13
    SEP = "─" * 32

    rows = [
        (src, cnt, new_counts.get(src, 0))
        for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1])
    ]

    zero_sources = [s for s in (all_sources or []) if source_counts.get(s, 0) == 0]

    lines = [f"Job scan · {date_str} · {duration_str}", ""]
    for src, total, new in rows:
        name = src[:NAME_W]
        lines.append(f"{name:<{NAME_W}} {total:>3} {_bar(new, total)}  {new:>3}")

    lines += ["", SEP, f"знайдено {total_scraped} · нових {total_new}"]

    if zero_sources:
        lines.append(f"нуль: {', '.join(zero_sources)}")

    _post_html("<pre>" + "\n".join(lines) + "</pre>")
