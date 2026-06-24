"""Scrape public Telegram job channels via t.me/s/channel web preview."""
import hashlib
import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "uk,en;q=0.9",
}

CHANNELS = [
    "dna325",       # NON-tech Jobs in IT & defense
    "workado_jobs", # Workado | Вакансії та карʼєра
    "Space_Job",    # SPACE JOB | IT
    "ymlnvjobs",    # Вакансії Ємельянова | IT / DIGITAL
]


def _make_id(channel: str, msg_id: str) -> str:
    return f"tg_{hashlib.md5(f'{channel}_{msg_id}'.encode()).hexdigest()[:12]}"


def _scrape_channel(channel: str) -> list[Job]:
    jobs = []
    try:
        url = f"https://t.me/s/{channel}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for msg in soup.select(".tgme_widget_message"):
            text_el = msg.select_one(".tgme_widget_message_text")
            if not text_el:
                continue

            text = text_el.get_text(separator=" ", strip=True)

            # Extract first line as title
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            title = lines[0][:120] if lines else text[:120]

            if not _title_match(title) and not _title_match(text[:300]):
                continue

            # Get message link
            link_el = msg.select_one(".tgme_widget_message_date a, a.tgme_widget_message_date")
            msg_url = link_el["href"] if link_el else f"https://t.me/{channel}"
            msg_id = msg_url.split("/")[-1] if "/" in msg_url else msg_url

            jobs.append(Job(
                id=_make_id(channel, msg_id),
                title=title,
                company=f"@{channel}",
                url=msg_url,
                description=text[:2000],
                source=f"Telegram/{channel}",
            ))
    except Exception as e:
        print(f"[Telegram/{channel}] Error: {e}")
    return jobs


def scrape() -> list[Job]:
    jobs = []
    for channel in CHANNELS:
        ch_jobs = _scrape_channel(channel)
        print(f"  [Telegram/{channel}] {len(ch_jobs)} relevant posts")
        jobs.extend(ch_jobs)
    return jobs
