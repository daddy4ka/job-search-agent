import feedparser
from scrapers.dou import Job, _title_match
import hashlib


def _make_id(url: str) -> str:
    return f"indeed_{hashlib.md5(url.encode()).hexdigest()[:12]}"


INDEED_FEEDS = [
    "https://ua.indeed.com/rss?q=head+of+data+analytics&l=Ukraine",
    "https://ua.indeed.com/rss?q=head+of+analytics&l=Ukraine",
    "https://ua.indeed.com/rss?q=business+intelligence+lead&l=Ukraine",
    "https://ua.indeed.com/rss?q=data+analytics+manager&l=Ukraine",
    "https://ua.indeed.com/rss?q=head+of+data+remote",
    "https://ua.indeed.com/rss?q=bi+lead+remote",
]


def scrape() -> list[Job]:
    jobs = []
    seen_ids = set()

    for feed_url in INDEED_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                job_id = entry.get("id") or entry.get("link", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = entry.get("title", "")
                if not _title_match(title):
                    continue

                jobs.append(Job(
                    id=_make_id(job_id),
                    title=title,
                    company=entry.get("author", "Indeed"),
                    url=entry.get("link", ""),
                    description=entry.get("summary", ""),
                    source="Indeed",
                ))
        except Exception as e:
            print(f"[Indeed] Error {feed_url}: {e}")

    return jobs
