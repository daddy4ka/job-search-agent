import feedparser
from scrapers.dou import Job, _title_match


DJINNI_FEEDS = [
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Science",
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Analytics",
    "https://djinni.co/jobs/rss/?primary_keyword=Business+Intelligence",
    "https://djinni.co/jobs/rss/?primary_keyword=Product+Management",
    "https://djinni.co/jobs/rss/?primary_keyword=Analytics",
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Engineer",
]


def scrape() -> list:
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

                title = entry.get("title", "")
                if not _title_match(title):
                    continue

                jobs.append(Job(
                    id=f"djinni_{job_id}",
                    title=title,
                    company=entry.get("author", "Djinni"),
                    url=entry.get("link", ""),
                    description=entry.get("summary", ""),
                    source="Djinni.co",
                ))
        except Exception as e:
            print(f"[Djinni] Error fetching {feed_url}: {e}")

    print(f"  [Djinni] {len(jobs)} jobs after title filter")
    return jobs
