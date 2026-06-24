"""Playwright-based scraper for JS-heavy job sites."""
import hashlib
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def _get_html(url: str, wait_selector: str = "body", timeout: int = 20000) -> str:
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = ctx.new_page()
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            try:
                page.wait_for_selector(wait_selector, timeout=8000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[Playwright] Error loading {url}: {e}")
        return ""


# ── We Work Remotely ──────────────────────────────────────────────────────────

def scrape_weworkremotely() -> list[Job]:
    jobs = []
    pages = [
        ("https://weworkremotely.com/categories/remote-data-science-jobs", "WeWorkRemotely"),
        ("https://weworkremotely.com/categories/remote-management-jobs", "WeWorkRemotely"),
    ]
    seen = set()
    for url, source in pages:
        html = _get_html(url, "section.jobs")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("section.jobs li"):
            title_el = item.select_one("span.title")
            company_el = item.select_one("span.company")
            link_el = item.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_match(title):
                continue
            href = link_el["href"] if link_el else ""
            if not href.startswith("http"):
                href = "https://weworkremotely.com" + href
            if href in seen:
                continue
            seen.add(href)
            jobs.append(Job(
                id=_make_id("wwr", href),
                title=title,
                company=company_el.get_text(strip=True) if company_el else "WWR",
                url=href,
                description=item.get_text(separator=" ", strip=True)[:2000],
                source=source,
            ))
    return jobs


# ── Remote.co ─────────────────────────────────────────────────────────────────

def scrape_remoteco() -> list[Job]:
    jobs = []
    searches = [
        "https://remote.co/remote-jobs/search/?search_keywords=head+of+data",
        "https://remote.co/remote-jobs/search/?search_keywords=business+intelligence+lead",
        "https://remote.co/remote-jobs/search/?search_keywords=analytics+manager",
    ]
    seen = set()
    for url in searches:
        html = _get_html(url, ".job_listings")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select(".job_listings li, .listing-item"):
            title_el = item.select_one("h3, h4, .position")
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
    return jobs


# ── Relocate.me ───────────────────────────────────────────────────────────────

def scrape_relocate() -> list[Job]:
    jobs = []
    queries = ["head+of+data", "business+intelligence+lead", "analytics+manager"]
    seen = set()
    for q in queries:
        url = f"https://relocate.me/search?q={q}"
        html = _get_html(url, "[class*='job'], [class*='vacancy'], article")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select("[class*='job-card'], [class*='vacancy'], article"):
            title_el = item.select_one("h2, h3, h4, [class*='title']")
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
                company="Relocate.me",
                url=href,
                description=item.get_text(separator=" ", strip=True)[:2000],
                source="Relocate.me",
            ))
    return jobs


# ── SoftServe ─────────────────────────────────────────────────────────────────

def scrape_softserve() -> list[Job]:
    jobs = []
    url = "https://career.softserveinc.com/en-us/vacancy?category=Data+%26+Analytics"
    html = _get_html(url, "[class*='vacancy'], [class*='job']")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='vacancy-item'], [class*='job-card'], li[class*='job']"):
        title_el = item.select_one("h2, h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://career.softserveinc.com" + href
        jobs.append(Job(
            id=_make_id("softserve", href),
            title=title,
            company="SoftServe",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="SoftServe",
        ))
    return jobs


# ── Ciklum ────────────────────────────────────────────────────────────────────

def scrape_ciklum() -> list[Job]:
    jobs = []
    url = "https://www.ciklum.com/careers/open-positions?department=Data+%26+Analytics"
    html = _get_html(url, "[class*='job'], [class*='vacancy'], article")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='job-card'], [class*='vacancy'], article"):
        title_el = item.select_one("h2, h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.ciklum.com" + href
        jobs.append(Job(
            id=_make_id("ciklum", href),
            title=title,
            company="Ciklum",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Ciklum",
        ))
    return jobs
