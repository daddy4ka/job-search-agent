import feedparser
from scrapers.dou import Job


DJINNI_FEEDS = [
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Science",
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Analytics",
    "https://djinni.co/jobs/rss/?primary_keyword=Business+Intelligence",
]


def scrape() -> list[Job]:
    jobs = []
    seen_ids = set()

    for feed_url in DJINNI_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                job_id = entry.get("id") or entry.get("link", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                jobs.append(Job(
                    id=f"djinni_{job_id}",
                    title=entry.get("title", ""),
                    company=entry.get("author", "Djinni"),
                    url=entry.get("link", ""),
                    description=entry.get("summary", ""),
                    source="Djinni.co",
                ))
        except Exception as e:
            print(f"[Djinni] Error fetching {feed_url}: {e}")

    return jobs
