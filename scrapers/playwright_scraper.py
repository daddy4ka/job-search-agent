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


# ── EPAM ──────────────────────────────────────────────────────────────────────

def scrape_epam() -> list[Job]:
    jobs = []
    url = "https://www.epam.com/careers/job-listings?sort=newest&department=Data+%26+Analytics"
    html = _get_html(url, "[class*='search-result'], [class*='job']")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='search-result__item'], [class*='job-item'], [class*='job-card']"):
        title_el = item.select_one("h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.epam.com" + href
        jobs.append(Job(
            id=_make_id("epam", href),
            title=title,
            company="EPAM Systems",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="EPAM",
        ))
    return jobs


# ── GlobalLogic ───────────────────────────────────────────────────────────────

def scrape_globallogic() -> list[Job]:
    jobs = []
    url = "https://www.globallogic.com/ua/careers/?search=data"
    html = _get_html(url, "[class*='career'], [class*='job'], article")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='career-item'], [class*='job-item'], article"):
        title_el = item.select_one("h2, h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.globallogic.com" + href
        jobs.append(Job(
            id=_make_id("globallogic", href),
            title=title,
            company="GlobalLogic",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="GlobalLogic",
        ))
    return jobs


# ── Luxoft ────────────────────────────────────────────────────────────────────

def scrape_luxoft() -> list[Job]:
    jobs = []
    url = "https://career.luxoft.com/search-jobs/?keyword=data+analytics"
    html = _get_html(url, "[class*='job'], [class*='vacancy']")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='job-item'], [class*='vacancy'], li[class*='job']"):
        title_el = item.select_one("h2, h3, h4, [class*='title'], a")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://career.luxoft.com" + href
        jobs.append(Job(
            id=_make_id("luxoft", href),
            title=title,
            company="Luxoft",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Luxoft",
        ))
    return jobs


# ── DataArt ───────────────────────────────────────────────────────────────────

def scrape_dataart() -> list[Job]:
    jobs = []
    url = "https://www.dataart.com/career?keyword=data+analytics"
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
            href = "https://www.dataart.com" + href
        jobs.append(Job(
            id=_make_id("dataart", href),
            title=title,
            company="DataArt",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="DataArt",
        ))
    return jobs


# ── Sigma Software ────────────────────────────────────────────────────────────

def scrape_sigma() -> list[Job]:
    jobs = []
    url = "https://sigma.software/about/career?category=Data"
    html = _get_html(url, "[class*='job'], [class*='vacancy'], article")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='vacancy'], [class*='job-item'], article"):
        title_el = item.select_one("h2, h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://sigma.software" + href
        jobs.append(Job(
            id=_make_id("sigma", href),
            title=title,
            company="Sigma Software",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Sigma",
        ))
    return jobs


# ── Grammarly ─────────────────────────────────────────────────────────────────

def scrape_grammarly() -> list[Job]:
    jobs = []
    url = "https://www.grammarly.com/jobs/all-departments"
    html = _get_html(url, "[class*='job'], [class*='position']")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='job-item'], [class*='position'], li"):
        title_el = item.select_one("h2, h3, h4, [class*='title'], a")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.grammarly.com" + href
        jobs.append(Job(
            id=_make_id("grammarly", href),
            title=title,
            company="Grammarly",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Grammarly",
        ))
    return jobs


# ── Wix ───────────────────────────────────────────────────────────────────────

def scrape_wix() -> list[Job]:
    jobs = []
    url = "https://www.wix.com/jobs/locations/all-locations/departments/data"
    html = _get_html(url, "[class*='job'], [class*='position'], article")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='job'], [class*='position-item'], article"):
        title_el = item.select_one("h2, h3, h4, [class*='title'], a")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.wix.com" + href
        jobs.append(Job(
            id=_make_id("wix", href),
            title=title,
            company="Wix",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Wix",
        ))
    return jobs


# ── Playtika ──────────────────────────────────────────────────────────────────

def scrape_playtika() -> list[Job]:
    jobs = []
    url = "https://www.playtika.com/careers/open-positions/?department=Data"
    html = _get_html(url, "[class*='job'], [class*='position'], article")
    if not html:
        return jobs
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("[class*='job-card'], [class*='position'], article"):
        title_el = item.select_one("h2, h3, h4, [class*='title']")
        link_el = item.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not _title_match(title):
            continue
        href = link_el["href"] if link_el else ""
        if not href.startswith("http"):
            href = "https://www.playtika.com" + href
        jobs.append(Job(
            id=_make_id("playtika", href),
            title=title,
            company="Playtika",
            url=href,
            description=item.get_text(separator=" ", strip=True)[:2000],
            source="Playtika",
        ))
    return jobs
