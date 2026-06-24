"""Scrapers for remote job boards."""
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

def scrape_weworkremotely() -> list:
    """Main RSS feed — 100 most recent remote jobs, filtered by title."""
    jobs = []
    seen = set()
    try:
        resp = requests.get(
            "https://weworkremotely.com/remote-jobs.rss",
            headers=HEADERS, timeout=20
        )
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            title = entry.get("title", "")
            if not _title_match(title):
                continue
            url = entry.get("link", "")
            if url in seen:
                continue
            seen.add(url)
            # title format: "Company: Job Title" — split it
            parts = title.split(": ", 1)
            company = parts[0].strip() if len(parts) > 1 else "WWR"
            job_title = parts[1].strip() if len(parts) > 1 else title
            jobs.append(Job(
                id=_make_id("wwr", url),
                title=job_title,
                company=company,
                url=url,
                description=entry.get("summary", ""),
                source="WeWorkRemotely",
            ))
    except Exception as e:
        print(f"[WWR] Error: {e}")
    print(f"  [WWR] {len(jobs)} matched")
    return jobs


# ── Remote.co ─────────────────────────────────────────────────────────────────

def scrape_remoteco() -> list:
    """Search pages via BrightData proxy."""
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
            for item in soup.select(".job_listings li, .job-listing, article, .listing-item"):
                title_el = item.select_one("h3, h4, .position, .title, a")
                link_el = item.select_one("a[href]")
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
                    company="Remote.co",
                    url=href,
                    description=item.get_text(separator=" ", strip=True)[:2000],
                    source="Remote.co",
                ))
        except Exception as e:
            print(f"[Remote.co] Error: {e}")
    print(f"  [Remote.co] {len(jobs)} matched")
    return jobs


# ── Relocate.me ───────────────────────────────────────────────────────────────

def scrape_relocate() -> list:
    """Search via BrightData proxy."""
    jobs = []
    session = get_session()
    queries = ["analyst", "head of data", "analytics lead", "data lead"]
    seen = set()
    for q in queries:
        try:
            url = f"https://relocate.me/search?q={q.replace(' ', '+')}"
            resp = session.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Try multiple possible selectors
            items = soup.select(".job, .vacancy, article, [data-job-id], li[class*='job']")
            if not items:
                items = soup.select("li, article")
            for item in items:
                link_el = item.select_one("a[href]")
                if not link_el:
                    continue
                title = link_el.get_text(strip=True)
                if not title or len(title) < 5:
                    # try h2/h3 inside
                    h = item.select_one("h2, h3, h4")
                    if h:
                        title = h.get_text(strip=True)
                if not _title_match(title):
                    continue
                href = link_el["href"]
                if not href.startswith("http"):
                    href = "https://relocate.me" + href
                if href in seen:
                    continue
                seen.add(href)
                jobs.append(Job(
                    id=_make_id("relocate", href),
                    title=title,
                    company="Relocate.me",
                    url=href,
                    description=item.get_text(separator=" ", strip=True)[:2000],
                    source="Relocate.me",
                ))
        except Exception as e:
            print(f"[Relocate.me] Error: {e}")
    print(f"  [Relocate.me] {len(jobs)} matched")
    return jobs


# ── Otta (deprecated — returns empty) ────────────────────────────────────────

def scrape_otta() -> list:
    return []
