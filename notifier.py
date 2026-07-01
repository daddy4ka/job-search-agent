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


def send_summary(raw_counts, source_counts, new_counts, started_at, all_sources=None) -> None:
    total_scraped = sum(source_counts.values())
    total_new = sum(new_counts.values())
    finished_at = datetime.now(timezone.utc)
    duration_sec = int((finished_at - started_at).total_seconds())
    duration_str = f"{duration_sec // 60}хв {duration_sec % 60}с"
    date_str = finished_at.strftime("%d.%m")

    NAME_W = 14
    SEP = "─" * 34

    sources = list(all_sources or source_counts.keys())
    rows = [
        (src, raw_counts.get(src, 0), source_counts.get(src, 0), new_counts.get(src, 0))
        for src in sources
    ]
    rows.sort(key=lambda x: -x[1])

    lines = [f"Job scan · {date_str} · {duration_str}", ""]
    lines.append(f"  {'':<{NAME_W}}{'всі':>5}{'ок':>4}{'нові':>5}")

    broken = []
    for src, raw, matched, new in rows:
        name = src[:NAME_W]
        row = f"{name:<{NAME_W}}{raw:>5}{matched:>4}{new:>5}"
        if raw == 0:
            lines.append(f"🔴{row} 🔴")
            broken.append(src)
        else:
            lines.append(f"  {row}")

    lines += ["", SEP, f"знайдено {total_scraped} · нових {total_new}"]
    if broken:
        lines.append(f"🔴 не працює: {', '.join(broken)}")

    _post_html("<pre>" + "\n".join(lines) + "</pre>")
