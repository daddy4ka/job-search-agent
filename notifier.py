import os
import time
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
    source_safe = job.source.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    title_safe = job.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    company_safe = job.company.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = (
        f"💼 <b>{title_safe}</b>\n"
        f"🏢 {company_safe} · <i>{source_safe}</i>\n"
        f"🔗 <a href=\"{job.url}\">Відкрити вакансію</a>"
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


def send_summary(source_counts, total_new, total_sent, started_at) -> None:
    total_scraped = sum(source_counts.values())
    finished_at = datetime.now(timezone.utc)
    duration_sec = int((finished_at - started_at).total_seconds())
    duration_str = f"{duration_sec // 60}хв {duration_sec % 60}с"
    finished_str = finished_at.strftime("%d.%m.%Y %H:%M UTC")

    lines = [
        f"📊 <b>Job scan complete</b>",
        f"🕐 {finished_str} · тривалість {duration_str}",
        "",
    ]

    source_icons = {
        "DOU.ua": "🟡", "Djinni.co": "🟣",
        "EPAM Systems": "🔵", "GlobalLogic": "🟢",
        "Intellias": "🔷", "ELEKS": "🟠",
        "Ciklum": "🔴", "N-iX": "⚪",
        "Relocate.me": "✈️", "WeWorkRemotely": "🌍", "Remote.co": "🌐",
    }

    for source, count in sorted(source_counts.items()):
        icon = next((v for k, v in source_icons.items() if k.lower() in source.lower()), "▪️")
        source_safe = source.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"{icon} {source_safe}: {count}")

    lines.append("")
    lines.append(f"🔢 Знайдено: {total_scraped} | Нових: {total_new} | Надіслано: {total_sent}")

    if total_sent == 0:
        lines.append("😶 Нових релевантних вакансій немає")
    else:
        lines.append(f"✅ {total_sent} вакансій надіслано вище")

    _post_html("\n".join(lines))
