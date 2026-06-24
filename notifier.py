import os
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.dou import Job


def _get_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)


def _post(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": _get_chat_id(),
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }, timeout=10)


def send_job(job: Job) -> bool:
    text = (
        f"💼 *{job.title}*\n"
        f"🏢 {job.company} · _{job.source}_\n"
        f"🔗 [Відкрити вакансію]({job.url})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": _get_chat_id(),
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send for {job.id}: {e}")
        return False


def send_summary(source_counts, total_new, total_sent) -> None:
    total_scraped = sum(source_counts.values())

    lines = ["📊 *Job scan complete*\n"]

    # Per-source breakdown
    source_icons = {
        "DOU.ua": "🟡", "Djinni.co": "🟣", "EPAM": "🔵",
        "GlobalLogic": "🟢", "Intellias": "🔷", "ELEKS": "🟠",
        "Ciklum": "🔴", "N-iX": "⚪", "LinkedIn": "🔗",
    }
    for source, count in sorted(source_counts.items()):
        icon = source_icons.get(source, "▪️")
        lines.append(f"{icon} {source}: {count}")

    lines.append(f"\n🔢 Всього: {total_scraped} | Нових: {total_new} | Надіслано: {total_sent}")

    if total_sent == 0:
        lines.append("\n😶 Релевантних вакансій не знайдено")
    else:
        lines.append(f"\n✅ {total_sent} вакансій надіслано вище")

    _post("\n".join(lines))
