import feedparser
from dataclasses import dataclass


@dataclass
class Job:
    id: str
    title: str
    company: str
    url: str
    description: str
    source: str


DOU_FEEDS = [
    "https://jobs.dou.ua/vacancies/feeds/?category=Data+Science",
    "https://jobs.dou.ua/vacancies/feeds/?category=Management",
    "https://jobs.dou.ua/vacancies/feeds/?category=Analytics",
]


def scrape() -> list[Job]:
    jobs = []
    seen_ids = set()

    for feed_url in DOU_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                job_id = entry.get("id") or entry.get("link", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                jobs.append(Job(
                    id=f"dou_{job_id}",
                    title=entry.get("title", ""),
                    company=entry.get("author", "DOU"),
                    url=entry.get("link", ""),
                    description=entry.get("summary", ""),
                    source="DOU.ua",
                ))
        except Exception as e:
            print(f"[DOU] Error fetching {feed_url}: {e}")

    return jobs
