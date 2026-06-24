"""Scrapers for remote job boards: We Work Remotely, Remote.co, Otta, Relocate.me"""
import feedparser
import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}


def _make_id(source: str, url: str) -> str:
    import hashlib
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


# ── We Work Remotely (RSS) ────────────────────────────────────────────────────

def scrape_weworkremotely() -> list[Job]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
        "https://weworkremotely.com/categories/remote-management-jobs.rss",
        "https://weworkremotely.com/categories/remote-business-jobs.rss",
    ]
    seen = set()
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
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


# ── Remote.co (scraping) ─────────────────────────────────────────────────────

def scrape_remoteco() -> list[Job]:
    jobs = []
    searches = [
        "https://remote.co/remote-jobs/search/?search_keywords=data+analytics",
        "https://remote.co/remote-jobs/search/?search_keywords=business+intelligence",
    ]
    seen = set()
    for url in searches:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".job_listings li, .job-listing, article"):
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


# ── Otta (public API) ─────────────────────────────────────────────────────────

def scrape_otta() -> list[Job]:
    jobs = []
    try:
        url = "https://api.otta.com/graphql"
        query = """
        {
          jobs(filters: {query: "data analytics head lead director"}) {
            edges {
              node {
                id
                title
                externalUrl
                company { name }
                jobDescription
              }
            }
          }
        }
        """
        resp = requests.post(url, json={"query": query}, headers=HEADERS, timeout=15)
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


# ── Relocate.me (RSS/scraping) ────────────────────────────────────────────────

def scrape_relocate() -> list[Job]:
    jobs = []
    searches = [
        "https://relocate.me/search#q=data+analytics&remote=true",
        "https://relocate.me/search#q=business+intelligence",
        "https://relocate.me/search#q=head+of+data",
    ]
    seen = set()
    for url in searches:
        try:
            # Relocate.me loads via JS, try their search API directly
            api_url = url.replace("https://relocate.me/search#", "https://relocate.me/api/jobs?")
            resp = requests.get(api_url, headers=HEADERS, timeout=15)
            data = resp.json() if resp.ok else {}
            items = data.get("jobs", data.get("results", data.get("data", [])))
            for item in items:
                title = item.get("title", item.get("position", ""))
                if not _title_match(title):
                    continue
                job_url = item.get("url", item.get("link", ""))
                if job_url in seen:
                    continue
                seen.add(job_url)
                jobs.append(Job(
                    id=_make_id("relocate", job_url),
                    title=title,
                    company=item.get("company", {}).get("name", "") if isinstance(item.get("company"), dict) else item.get("company", "Relocate.me"),
                    url=job_url,
                    description=item.get("description", "")[:2000],
                    source="Relocate.me",
                ))
        except Exception as e:
            print(f"[Relocate.me] Error for {url}: {e}")
    return jobs
