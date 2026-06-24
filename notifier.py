import os
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.dou import Job


def _get_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)


def send_job(job: Job, score: int, reason: str) -> bool:
    score_bar = "🟢" * min(score, 5) + ("🟡" if score >= 5 else "🔴") * max(0, min(score - 5, 5))

    text = (
        f"💼 *{job.title}*\n"
        f"🏢 {job.company} · {job.source}\n"
        f"⭐ Score: {score}/10 {score_bar}\n"
        f"💡 {reason}\n"
        f"🔗 [Open Job]({job.url})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": _get_chat_id(),
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send for {job.id}: {e}")
        return False


def send_summary(total_scraped: int, total_new: int, total_sent: int) -> None:
    if total_sent == 0:
        text = f"🔍 Job scan complete. {total_scraped} scraped, {total_new} new — no relevant matches this run."
    else:
        text = f"✅ Job scan done. {total_scraped} scraped · {total_new} new · {total_sent} sent to you."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": _get_chat_id(), "text": text}, timeout=10)
