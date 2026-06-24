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


# Keywords that must appear in job title (case-insensitive)
TITLE_MUST_HAVE = [
    # Head-level
    "head of data", "head of analytics", "head of bi", "head of business intelligence",
    "head of r&d", "head of research", "head of insight",
    # Lead-level
    "bi lead", "data lead", "analytics lead",
    "business intelligence lead", "business intelligence manager",
    "analytics chapter lead",
    # Manager/Director/VP
    "data analytics manager", "analytics manager",
    "director of data", "director of analytics",
    "chief data", "cdo", "vp of data", "vp of analytics",
    # Governance & strategy
    "data governance lead", "data office",
    # Analyst roles (Claude scoring filters seniority at level 2)
    "lead data analyst", "senior data analyst", "principal data",
    "data analyst", "bi analyst", "business intelligence analyst",
    "analytics analyst", "marketing analyst", "product analyst",
    "аналітик", "дата аналітик", "бі аналітик",
]

DOU_FEEDS = [
    "https://jobs.dou.ua/vacancies/feeds/?category=Data+Science",
    "https://jobs.dou.ua/vacancies/feeds/?category=Management",
    "https://jobs.dou.ua/vacancies/feeds/?category=Analytics",
    "https://jobs.dou.ua/vacancies/feeds/?category=Product+Management",
]


def _title_match(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TITLE_MUST_HAVE)


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

                title = entry.get("title", "")
                if not _title_match(title):
                    continue

                jobs.append(Job(
                    id=f"dou_{job_id}",
                    title=title,
                    company=entry.get("author", "DOU"),
                    url=entry.get("link", ""),
                    description=entry.get("summary", ""),
                    source="DOU.ua",
                ))
        except Exception as e:
            print(f"[DOU] Error fetching {feed_url}: {e}")

    return jobs
