import json
import re
import feedparser
import requests
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

DJINNI_FEEDS = [
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Science",
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Analytics",
    "https://djinni.co/jobs/rss/?primary_keyword=Business+Intelligence",
    "https://djinni.co/jobs/rss/?primary_keyword=Product+Management",
    "https://djinni.co/jobs/rss/?primary_keyword=Analytics",
    "https://djinni.co/jobs/rss/?primary_keyword=Data+Engineer",
]


def _get_company(url: str) -> str:
    """RSS has no company field — pull it from the job page's JobPosting JSON-LD."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            org = data.get("hiringOrganization")
            if isinstance(org, dict) and org.get("name"):
                return org["name"]
            if isinstance(org, str) and org:
                return org
    except Exception as e:
        print(f"[Djinni] Company lookup error for {url}: {e}")
    return "Djinni"


def scrape() -> tuple[list, int]:
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

                link = entry.get("link", "")
                jobs.append(Job(
                    id=f"djinni_{job_id}",
                    title=title,
                    company=_get_company(link),
                    url=link,
                    description=entry.get("summary", ""),
                    source="Djinni.co",
                ))
        except Exception as e:
            print(f"[Djinni] Error fetching {feed_url}: {e}")

    print(f"  [Djinni] {len(jobs)} jobs after title filter")
    return jobs, len(seen_ids)
