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


TITLE_MUST_HAVE = [
    # Generic
    "analyst", "analytics",
    # Head-level
    "head of data", "head of analytics", "head of bi", "head of business intelligence",
    "head of r&d", "head of research", "head of insight", "head of insights",
    "head of growth", "head of strategy", "head of performance",
    "head of product analytics", "head of data science",
    # Lead-level
    "bi lead", "data lead", "analytics lead",
    "business intelligence lead", "business intelligence manager",
    "analytics chapter lead", "growth lead", "strategy lead", "insights lead",
    "insight lead",
    # Manager/Director/VP
    "data analytics manager", "analytics manager",
    "director of data", "director of analytics",
    "chief data", "cdo", "vp of data", "vp of analytics",
    "growth manager", "insights manager", "insight manager",
    "performance manager", "revenue operations manager",
    "product analytics manager", "data science manager",
    "marketing strategy manager", "marketing manager", "strategy manager",
    # Governance & strategy
    "data governance lead", "data office",
    "strategic analytics", "decision science", "decision analytics",
    "revenue analytics",
    # Analyst roles
    "lead data analyst", "senior data analyst", "principal data",
    "data analyst", "bi analyst", "business intelligence analyst",
    "analytics analyst", "marketing analyst", "product analyst",
    "growth analyst", "insights analyst", "insight analyst",
    "аналітик", "дата аналітик", "бі аналітик",
    # R&D
    "r&d team lead", "r&d lead", "research and development lead",
]

# Each feed returns latest 25 jobs — combine keywords + categories for broader coverage
DOU_FEEDS = [
    # Keyword search
    "https://jobs.dou.ua/vacancies/feeds/?search=analyst",
    "https://jobs.dou.ua/vacancies/feeds/?search=analytics",
    "https://jobs.dou.ua/vacancies/feeds/?search=head+of+data",
    "https://jobs.dou.ua/vacancies/feeds/?search=head+of+analytics",
    "https://jobs.dou.ua/vacancies/feeds/?search=bi+analyst",
    "https://jobs.dou.ua/vacancies/feeds/?search=data+lead",
    "https://jobs.dou.ua/vacancies/feeds/?search=bi+lead",
    "https://jobs.dou.ua/vacancies/feeds/?search=data+manager",
    "https://jobs.dou.ua/vacancies/feeds/?search=head+of+bi",
    "https://jobs.dou.ua/vacancies/feeds/?search=analytics+manager",
    "https://jobs.dou.ua/vacancies/feeds/?search=%D0%B0%D0%BD%D0%B0%D0%BB%D1%96%D1%82%D0%B8%D0%BA",
    "https://jobs.dou.ua/vacancies/feeds/?search=%D0%B0%D0%BD%D0%B0%D0%BB%D1%96%D1%82%D0%B8%D0%BA%D0%B0",
    # Category feeds
    "https://jobs.dou.ua/vacancies/feeds/?category=Analytics+%2F+BI",
    "https://jobs.dou.ua/vacancies/feeds/?category=Data+Science",
    "https://jobs.dou.ua/vacancies/feeds/?category=Management",
]


def _title_match(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TITLE_MUST_HAVE)


def scrape() -> list:
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

    print(f"  [DOU] {len(jobs)} jobs after title filter")
    return jobs
