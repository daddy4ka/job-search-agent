"""Playwright-based scraper for JS-heavy job sites."""
import hashlib
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def _get_html(url: str, wait_selector: str = "body", timeout: int = 25000) -> str:
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = ctx.new_page()
            page.goto(url, timeout=timeout, wait_until="networkidle")
            try:
                page.wait_for_selector(wait_selector, timeout=10000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[Playwright] Error loading {url}: {e}")
        return ""


def _extract_jobs_from_links(html: str, source: str, company: str, base_url: str) -> list[Job]:
    """Generic extractor — finds all <a> tags whose text matches title keywords."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if len(title) < 5 or len(title) > 150:
            continue
        if not _title_match(title):
            continue
        href = a["href"]
        if not href.startswith("http"):
            href = base_url.rstrip("/") + "/" + href.lstrip("/")
        if href in seen:
            continue
        seen.add(href)
        # grab surrounding context as description
        parent = a.find_parent(["li", "article", "div", "tr"])
        desc = parent.get_text(separator=" ", strip=True)[:2000] if parent else title
        jobs.append(Job(
            id=_make_id(source.lower(), href),
            title=title,
            company=company,
            url=href,
            description=desc,
            source=source,
        ))
    return jobs


COMPANY_PAGES = [
    ("weworkremotely", "WeWorkRemotely", "https://weworkremotely.com", [
        "https://weworkremotely.com/categories/remote-data-science-jobs",
        "https://weworkremotely.com/categories/remote-management-jobs",
    ]),
    ("remoteco", "Remote.co", "https://remote.co", [
        "https://remote.co/remote-jobs/search/?search_keywords=head+of+data",
        "https://remote.co/remote-jobs/search/?search_keywords=analytics+manager",
    ]),
    ("relocate", "Relocate.me", "https://relocate.me", [
        "https://relocate.me/search?q=head+of+data",
        "https://relocate.me/search?q=analytics+lead",
    ]),
    ("softserve", "SoftServe", "https://career.softserveinc.com", [
        "https://career.softserveinc.com/en-us/vacancy?category=Data+%26+Analytics",
    ]),
    ("ciklum", "Ciklum", "https://www.ciklum.com", [
        "https://www.ciklum.com/careers/open-positions",
    ]),
    ("epam", "EPAM Systems", "https://www.epam.com", [
        "https://www.epam.com/careers/job-listings?sort=newest&department=Data+%26+Analytics",
    ]),
    ("globallogic", "GlobalLogic", "https://www.globallogic.com", [
        "https://www.globallogic.com/ua/careers/?search=data+analytics",
    ]),
    ("luxoft", "Luxoft", "https://career.luxoft.com", [
        "https://career.luxoft.com/search-jobs/?keyword=data+analytics",
    ]),
    ("dataart", "DataArt", "https://www.dataart.com", [
        "https://www.dataart.com/career",
    ]),
    ("sigma", "Sigma Software", "https://sigma.software", [
        "https://sigma.software/about/career",
    ]),
    ("grammarly", "Grammarly", "https://www.grammarly.com", [
        "https://www.grammarly.com/jobs",
    ]),
    ("wix", "Wix", "https://www.wix.com", [
        "https://www.wix.com/jobs/locations/all-locations/departments/data",
    ]),
    ("playtika", "Playtika", "https://www.playtika.com", [
        "https://www.playtika.com/careers/open-positions/",
    ]),
]


def _scrape_company(key: str, company: str, base_url: str, urls: list[str]) -> list[Job]:
    jobs = []
    seen = set()
    for url in urls:
        html = _get_html(url)
        new_jobs = _extract_jobs_from_links(html, key.capitalize(), company, base_url)
        for j in new_jobs:
            if j.url not in seen:
                seen.add(j.url)
                jobs.append(j)
    return jobs


def scrape_weworkremotely() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[0])

def scrape_remoteco() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[1])

def scrape_relocate() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[2])

def scrape_softserve() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[3])

def scrape_ciklum() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[4])

def scrape_epam() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[5])

def scrape_globallogic() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[6])

def scrape_luxoft() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[7])

def scrape_dataart() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[8])

def scrape_sigma() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[9])

def scrape_grammarly() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[10])

def scrape_wix() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[11])

def scrape_playtika() -> list[Job]:
    return _scrape_company(*COMPANY_PAGES[12])
