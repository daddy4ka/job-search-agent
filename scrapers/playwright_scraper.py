"""Playwright-based scraper for JS-heavy company career pages."""
import hashlib
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def _get_html(url: str, wait_selector: str = None, extra_wait_ms: int = 3000) -> str:
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
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            # Wait for JS to render content
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=15000)
                except Exception:
                    pass
            # Extra buffer for JS rendering
            page.wait_for_timeout(extra_wait_ms)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[Playwright] Error loading {url}: {e}")
        return ""


def _extract_jobs_from_links(html: str, source: str, company: str, base_url: str) -> list:
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


# ── Company scrapers with site-specific selectors ────────────────────────────

def scrape_epam() -> list:
    html = _get_html(
        "https://www.epam.com/careers/job-listings?sort=newest&department=Data+%26+Analytics",
        wait_selector=".search-result__item, .job-card, [class*='vacancy']",
    )
    # Filter only real vacancy URLs (contain /vacancy/), skip category pages (/jobs/)
    all_jobs = _extract_jobs_from_links(html, "EPAM", "EPAM Systems", "https://www.epam.com")
    return [j for j in all_jobs if "/vacancy/" in j.url]


def scrape_globallogic() -> list:
    html = _get_html(
        "https://www.globallogic.com/ua/careers/?search=data+analytics",
        wait_selector=".career-job, .job-item, [class*='career']",
    )
    return _extract_jobs_from_links(html, "GlobalLogic", "GlobalLogic", "https://www.globallogic.com")


def scrape_luxoft() -> list:
    html = _get_html(
        "https://career.luxoft.com/search-jobs/?keyword=analyst",
        wait_selector=".job-list, .job-card, [class*='job']",
    )
    return _extract_jobs_from_links(html, "Luxoft", "Luxoft", "https://career.luxoft.com")


def scrape_softserve() -> list:
    html = _get_html(
        "https://career.softserveinc.com/en-us/vacancy?category=Data+%26+Analytics",
        wait_selector=".vacancy-item, .job-card, [class*='vacancy']",
    )
    return _extract_jobs_from_links(html, "SoftServe", "SoftServe", "https://career.softserveinc.com")


def scrape_ciklum() -> list:
    html = _get_html(
        "https://www.ciklum.com/careers/open-positions",
        wait_selector=".job-card, .vacancy, [class*='position']",
    )
    return _extract_jobs_from_links(html, "Ciklum", "Ciklum", "https://www.ciklum.com")


def scrape_dataart() -> list:
    html = _get_html(
        "https://www.dataart.com/career",
        wait_selector=".vacancy, .job, [class*='career']",
    )
    return _extract_jobs_from_links(html, "DataArt", "DataArt", "https://www.dataart.com")


def scrape_sigma() -> list:
    html = _get_html(
        "https://sigma.software/about/career",
        wait_selector=".vacancy, .job, [class*='career']",
    )
    return _extract_jobs_from_links(html, "Sigma", "Sigma Software", "https://sigma.software")


def scrape_grammarly() -> list:
    html = _get_html(
        "https://www.grammarly.com/jobs",
        wait_selector="[class*='job'], [class*='position'], [class*='opening']",
        extra_wait_ms=5000,
    )
    return _extract_jobs_from_links(html, "Grammarly", "Grammarly", "https://www.grammarly.com")


def scrape_wix() -> list:
    html = _get_html(
        "https://www.wix.com/jobs/locations/all-locations/departments/data",
        wait_selector="[class*='job'], [class*='position']",
        extra_wait_ms=5000,
    )
    return _extract_jobs_from_links(html, "Wix", "Wix", "https://www.wix.com")


def scrape_playtika() -> list:
    # Handled via Greenhouse API in companies.py — this is a fallback
    return []


def scrape_weworkremotely() -> list:
    # Handled via RSS in boards.py
    from scrapers.boards import scrape_weworkremotely as _scrape
    return _scrape()


def scrape_remoteco() -> list:
    from scrapers.boards import scrape_remoteco as _scrape
    return _scrape()


def scrape_relocate() -> list:
    from scrapers.boards import scrape_relocate as _scrape
    return _scrape()
