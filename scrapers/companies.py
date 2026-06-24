"""Scrapers for company career pages using Lever/Greenhouse public APIs."""
import hashlib
import requests
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


# ── Lever public API ──────────────────────────────────────────────────────────

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


# ── UA Outsourcers ────────────────────────────────────────────────────────────

def scrape_ciklum() -> list[Job]:
    return []  # no public API found

def scrape_intellias() -> list[Job]:
    return _scrape_lever("intellias", "Intellias", "Intellias")

def scrape_nix() -> list[Job]:
    return _scrape_greenhouse("nix", "N-iX", "N-iX")

def scrape_eleks() -> list[Job]:
    return _scrape_lever("eleks", "ELEKS", "ELEKS")

def scrape_softserve() -> list[Job]:
    jobs = []
    try:
        base = "https://career.softserveinc.com"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"{base}/en-us/vacancies",
            "Accept": "application/json",
        }
        page = 1
        while True:
            url = f"{base}/api/frontend/vacancies?query=%2A%3F&page={page}"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            vacancies = data.get("data", {}).get("vacancies", [])
            for v in vacancies:
                title = v.get("name", "")
                if not _title_match(title):
                    continue
                slug = v.get("urlSegment", "")
                job_url = f"{base}/en-us/vacancies/{slug}" if slug else base
                jobs.append(Job(
                    id=_make_id("softserve", job_url),
                    title=title,
                    company="SoftServe",
                    url=job_url,
                    description=f"{v.get('direction','')} | {v.get('city','')}",
                    source="SoftServe",
                ))
            meta = data.get("meta", {})
            if page >= meta.get("last_page", 1):
                break
            page += 1
    except Exception as e:
        print(f"[SoftServe] API error: {e}")
    return jobs

def scrape_dataart() -> list[Job]:
    return []  # no public API found

def scrape_playtika() -> list[Job]:
    return _scrape_greenhouse("playtikaltd", "Playtika", "Playtika")

def scrape_wix() -> list[Job]:
    return []  # no public API found

def scrape_grammarly() -> list[Job]:
    return []  # no public API found

def scrape_lohika() -> list[Job]:
    return []  # no public API found

def scrape_sigma() -> list[Job]:
    return []  # no public API found


def scrape_luxoft() -> list[Job]:
    jobs = []
    try:
        url = "https://career.luxoft.com/search-jobs/?keyword=data+analytics&remote=true"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".job-item, .vacancy, article, li.job"):
            title_el = item.select_one("h2, h3, h4, .title, a")
            link_el = item.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_match(title):
                continue
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = "https://career.luxoft.com" + href
            jobs.append(Job(
                id=_make_id("luxoft", href),
                title=title,
                company="Luxoft",
                url=href,
                description=item.get_text(separator=" ", strip=True)[:2000],
                source="Luxoft",
            ))
    except Exception as e:
        print(f"[Luxoft] Error: {e}")
    return jobs


def scrape_epam() -> list[Job]:
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
    jobs = []
    try:
        url = "https://career.globallogic.com/careers/searchjobs/?query=data+analytics&region=Ukraine&pagesize=50"
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
