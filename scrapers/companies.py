"""Scrapers for company career pages using Lever/Greenhouse public APIs."""
import hashlib
import requests
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


# ── Lever public API ──────────────────────────────────────────────────────────
# URL: https://api.lever.co/v0/postings/SLUG?mode=json

def _scrape_lever(company_slug: str, company_name: str, source_label: str) -> list[Job]:
    jobs = []
    try:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        for item in resp.json():
            title = item.get("text", "")
            if not _title_match(title):
                continue
            job_url = item.get("hostedUrl", "")
            description = item.get("descriptionPlain", "") or item.get("description", "")
            jobs.append(Job(
                id=_make_id(source_label, job_url),
                title=title,
                company=company_name,
                url=job_url,
                description=description[:2000],
                source=source_label,
            ))
    except Exception as e:
        print(f"[{source_label}] Lever API error: {e}")
    return jobs


# ── Greenhouse public API ─────────────────────────────────────────────────────
# URL: https://boards-api.greenhouse.io/v1/boards/SLUG/jobs?content=true

def _scrape_greenhouse(company_slug: str, company_name: str, source_label: str) -> list[Job]:
    jobs = []
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        for item in resp.json().get("jobs", []):
            title = item.get("title", "")
            if not _title_match(title):
                continue
            job_url = item.get("absolute_url", "")
            description = item.get("content", "")
            jobs.append(Job(
                id=_make_id(source_label, job_url),
                title=title,
                company=company_name,
                url=job_url,
                description=description[:2000],
                source=source_label,
            ))
    except Exception as e:
        print(f"[{source_label}] Greenhouse API error: {e}")
    return jobs


# ── Workday XML feed ──────────────────────────────────────────────────────────

def _scrape_workday_xml(feed_url: str, company_name: str, source_label: str) -> list[Job]:
    """Some companies expose a public XML/JSON feed via Workday."""
    from bs4 import BeautifulSoup
    jobs = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("jobposting, position"):
            title = item.select_one("title, jobtitle")
            link = item.select_one("link, url")
            desc = item.select_one("description, jobdescription")
            if not title:
                continue
            title_text = title.get_text(strip=True)
            if not _title_match(title_text):
                continue
            job_url = link.get_text(strip=True) if link else feed_url
            jobs.append(Job(
                id=_make_id(source_label, job_url),
                title=title_text,
                company=company_name,
                url=job_url,
                description=desc.get_text(strip=True)[:2000] if desc else "",
                source=source_label,
            ))
    except Exception as e:
        print(f"[{source_label}] Workday error: {e}")
    return jobs


# ── Individual company scrapers ───────────────────────────────────────────────

def scrape_ciklum() -> list[Job]:
    # Ciklum uses Lever
    return _scrape_lever("ciklum", "Ciklum", "Ciklum")


def scrape_intellias() -> list[Job]:
    # Intellias uses Greenhouse
    return _scrape_greenhouse("intellias", "Intellias", "Intellias")


def scrape_nix() -> list[Job]:
    # N-iX uses Greenhouse
    return _scrape_greenhouse("n-ix", "N-iX", "N-iX")


def scrape_eleks() -> list[Job]:
    # ELEKS uses Greenhouse
    return _scrape_greenhouse("eleks", "ELEKS", "ELEKS")


def scrape_epam() -> list[Job]:
    # EPAM uses their own portal — scrape search JSON endpoint
    jobs = []
    try:
        url = (
            "https://www.epam.com/api/careers/search"
            "?filterDepartments=Data+%26+Analytics&pageSize=50&pageNumber=0"
        )
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        for item in data.get("vacancies", data.get("jobs", data.get("results", []))):
            title = item.get("title", item.get("jobTitle", ""))
            if not _title_match(title):
                continue
            job_url = item.get("url", item.get("applyUrl", ""))
            if job_url and not job_url.startswith("http"):
                job_url = "https://www.epam.com" + job_url
            jobs.append(Job(
                id=_make_id("epam", job_url),
                title=title,
                company="EPAM Systems",
                url=job_url,
                description=item.get("description", "")[:2000],
                source="EPAM",
            ))
    except Exception as e:
        print(f"[EPAM] API error: {e}")
    return jobs


def scrape_globallogic() -> list[Job]:
    # GlobalLogic uses Workday — try their public search API
    jobs = []
    try:
        url = (
            "https://career.globallogic.com/careers/searchjobs/?"
            "query=data+analytics&region=Ukraine&pagesize=50"
        )
        resp = requests.get(url, headers=HEADERS, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("li.resultLink, .job-listing, article"):
            title_el = item.select_one("h2, h3, h4, a")
            link_el = item.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_match(title):
                continue
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = "https://career.globallogic.com" + href
            jobs.append(Job(
                id=_make_id("globallogic", href),
                title=title,
                company="GlobalLogic",
                url=href,
                description=item.get_text(separator=" ", strip=True)[:2000],
                source="GlobalLogic",
            ))
    except Exception as e:
        print(f"[GlobalLogic] Error: {e}")
    return jobs


def scrape_linkedin() -> list[Job]:
    """LinkedIn public job search — no auth required."""
    jobs = []
    searches = [
        "Head+of+Data+Analytics&location=Ukraine",
        "Head+of+BI+Analytics&location=Ukraine",
        "Business+Intelligence+Lead&location=Ukraine",
        "Head+of+Analytics+remote",
        "Director+of+Analytics+remote",
    ]
    seen_ids = set()
    try:
        for query in searches:
            url = f"https://www.linkedin.com/jobs/search/?keywords={query}&f_TPR=r86400"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".base-card, .job-search-card"):
                title_el = item.select_one(".base-search-card__title, h3")
                company_el = item.select_one(".base-search-card__subtitle, h4")
                link_el = item.select_one("a[href]")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_match(title):
                    continue
                href = link_el["href"].split("?")[0]
                if href in seen_ids:
                    continue
                seen_ids.add(href)
                jobs.append(Job(
                    id=_make_id("linkedin", href),
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "LinkedIn",
                    url=href,
                    description=item.get_text(separator=" ", strip=True)[:2000],
                    source="LinkedIn",
                ))
    except Exception as e:
        print(f"[LinkedIn] Error: {e}")
    return jobs
