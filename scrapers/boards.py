"""Scrapers for remote job boards."""
import hashlib
import feedparser
import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


# ── We Work Remotely ──────────────────────────────────────────────────────────

def scrape_weworkremotely() -> list:
    """Category pages + keyword search on WeWorkRemotely."""
    jobs = []
    seen = set()
    base = "https://weworkremotely.com"
    URLS = [
        f"{base}/categories/remote-management-and-finance-jobs",
        f"{base}/categories/remote-product-jobs",
        f"{base}/remote-jobs/search?term=data+analyst",
        f"{base}/remote-jobs/search?term=business+analyst",
        f"{base}/remote-jobs/search?term=head+of+data",
        f"{base}/remote-jobs/search?term=analytics+lead",
    ]
    try:
        for url in URLS:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            for li in soup.select("section.jobs li.new-listing-container"):
                title_el = li.select_one("span.new-listing__header__title__text")
                link_el = li.select_one("a.listing-link--unlocked, a[class*=listing-link]")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_match(title):
                    continue
                href = link_el["href"]
                if not href.startswith("http"):
                    href = base + href
                if href in seen:
                    continue
                seen.add(href)
                dedup_key = (title.lower(), href.split("/")[-1][:30])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                company_a = li.select_one("a[href*='/company/']")
                company = (
                    company_a["href"].split("/")[-1].replace("-", " ").title()
                    if company_a else "WWR"
                )
                jobs.append(Job(
                    id=_make_id("wwr", href),
                    title=title,
                    company=company,
                    url=href,
                    description="",
                    source="WeWorkRemotely",
                ))
    except Exception as e:
        print(f"[WWR] Error: {e}")
    print(f"  [WWR] {len(jobs)} matched")
    return jobs


# ── Otta (deprecated — returns empty) ────────────────────────────────────────

def scrape_otta() -> list:
    return []
