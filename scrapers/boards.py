"""Scrapers for remote job boards: We Work Remotely, Remote.co, Otta, Relocate.me"""
import hashlib
import feedparser
import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match
from proxy import get_session

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


# ── We Work Remotely ──────────────────────────────────────────────────────────

def scrape_weworkremotely() -> list[Job]:
    jobs = []
    session = get_session()
    feeds = [
        "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
        "https://weworkremotely.com/categories/remote-management-jobs.rss",
        "https://weworkremotely.com/categories/remote-business-jobs.rss",
    ]
    seen = set()
    for feed_url in feeds:
        try:
            resp = session.get(feed_url, timeout=20)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                title = entry.get("title", "")
                if not _title_match(title):
                    continue
                url = entry.get("link", "")
                if url in seen:
                    continue
                seen.add(url)
                jobs.append(Job(
                    id=_make_id("wwr", url),
                    title=title,
                    company=entry.get("author", "WWR"),
                    url=url,
                    description=entry.get("summary", ""),
                    source="WeWorkRemotely",
                ))
        except Exception as e:
            print(f"[WWR] Error: {e}")
    return jobs


# ── Remote.co ─────────────────────────────────────────────────────────────────

def scrape_remoteco() -> list[Job]:
    jobs = []
    session = get_session()
    searches = [
        "https://remote.co/remote-jobs/search/?search_keywords=data+analytics",
        "https://remote.co/remote-jobs/search/?search_keywords=business+intelligence",
        "https://remote.co/remote-jobs/search/?search_keywords=head+of+data",
    ]
    seen = set()
    for url in searches:
        try:
            resp = session.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".job_listings li, .job-listing, article, .listing"):
                title_el = item.select_one("h3, h4, .position, a")
                link_el = item.select_one("a[href]")
                company_el = item.select_one(".company, .employer")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_match(title):
                    continue
                href = link_el["href"]
                if not href.startswith("http"):
                    href = "https://remote.co" + href
                if href in seen:
                    continue
                seen.add(href)
                jobs.append(Job(
                    id=_make_id("remoteco", href),
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "Remote.co",
                    url=href,
                    description=item.get_text(separator=" ", strip=True)[:2000],
                    source="Remote.co",
                ))
        except Exception as e:
            print(f"[Remote.co] Error: {e}")
    return jobs


# ── Otta ──────────────────────────────────────────────────────────────────────

def scrape_otta() -> list[Job]:
    jobs = []
    session = get_session()
    try:
        url = "https://api.otta.com/graphql"
        query = '{ jobs(filters: {query: "data analytics head lead director"}) { edges { node { id title externalUrl company { name } jobDescription } } } }'
        resp = session.post(url, json={"query": query}, timeout=20)
        data = resp.json()
        for edge in data.get("data", {}).get("jobs", {}).get("edges", []):
            node = edge.get("node", {})
            title = node.get("title", "")
            if not _title_match(title):
                continue
            job_url = node.get("externalUrl", "")
            jobs.append(Job(
                id=_make_id("otta", job_url or node.get("id", "")),
                title=title,
                company=node.get("company", {}).get("name", "Otta"),
                url=job_url,
                description=node.get("jobDescription", "")[:2000],
                source="Otta",
            ))
    except Exception as e:
        print(f"[Otta] Error: {e}")
    return jobs


# ── Relocate.me ───────────────────────────────────────────────────────────────

def scrape_relocate() -> list[Job]:
    jobs = []
    session = get_session()
    queries = ["head of data", "data analytics", "business intelligence lead"]
    seen = set()
    for q in queries:
        try:
            url = f"https://relocate.me/search?q={q.replace(' ', '+')}"
            resp = session.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".job-card, .vacancy, article, [class*='job']"):
                title_el = item.select_one("h2, h3, h4, .title, a")
                link_el = item.select_one("a[href]")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_match(title):
                    continue
                href = link_el["href"] if link_el else ""
                if not href.startswith("http"):
                    href = "https://relocate.me" + href
                if href in seen:
                    continue
                seen.add(href)
                jobs.append(Job(
                    id=_make_id("relocate", href),
                    title=title,
                    company=item.select_one(".company, .employer, [class*='company']") and
                            item.select_one(".company, .employer, [class*='company']").get_text(strip=True) or "Relocate.me",
                    url=href,
                    description=item.get_text(separator=" ", strip=True)[:2000],
                    source="Relocate.me",
                ))
        except Exception as e:
            print(f"[Relocate.me] Error: {e}")
    return jobs
