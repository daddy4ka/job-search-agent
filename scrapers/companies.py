"""Scrapers for company career pages: EPAM, GlobalLogic, Intellias, Eleks, Ciklum, N-iX"""
import hashlib
import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Keywords to pre-filter job titles before sending to Claude
TITLE_KEYWORDS = [
    "data", "analytics", "bi ", "business intelligence", "insight",
    "head of", "lead", "manager", "director", "chief", "r&d",
]


def _title_relevant(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TITLE_KEYWORDS)


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def scrape_epam() -> list[Job]:
    jobs = []
    try:
        url = "https://www.epam.com/careers/job-listings?sort=newest&department=Data+%26+Analytics"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".search-result__item, .job-item, [class*='job-card']"):
            title_el = item.select_one("[class*='title'], h3, h4")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://www.epam.com" + href
            jobs.append(Job(
                id=_make_id("epam", href),
                title=title,
                company="EPAM Systems",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="EPAM",
            ))
    except Exception as e:
        print(f"[EPAM] Error: {e}")
    return jobs


def scrape_globallogic() -> list[Job]:
    jobs = []
    try:
        url = "https://www.globallogic.com/ua/careers/?search=data+analytics"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".job-listing__item, .career-item, article"):
            title_el = item.select_one("h2, h3, h4, .title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://www.globallogic.com" + href
            jobs.append(Job(
                id=_make_id("globallogic", href),
                title=title,
                company="GlobalLogic",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="GlobalLogic",
            ))
    except Exception as e:
        print(f"[GlobalLogic] Error: {e}")
    return jobs


def scrape_intellias() -> list[Job]:
    jobs = []
    try:
        url = "https://intellias.com/open-positions/?department=data"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".job-card, .vacancy-item, .position-item, article"):
            title_el = item.select_one("h2, h3, h4, .job-title, .title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://intellias.com" + href
            jobs.append(Job(
                id=_make_id("intellias", href),
                title=title,
                company="Intellias",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="Intellias",
            ))
    except Exception as e:
        print(f"[Intellias] Error: {e}")
    return jobs


def scrape_eleks() -> list[Job]:
    jobs = []
    try:
        url = "https://eleks.com/career/?expertise=Data+Science+%26+Analytics"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".vacancy, .job-item, .career-item, article"):
            title_el = item.select_one("h2, h3, h4, .title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://eleks.com" + href
            jobs.append(Job(
                id=_make_id("eleks", href),
                title=title,
                company="ELEKS",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="ELEKS",
            ))
    except Exception as e:
        print(f"[ELEKS] Error: {e}")
    return jobs


def scrape_ciklum() -> list[Job]:
    jobs = []
    try:
        url = "https://www.ciklum.com/careers/open-positions?department=Data+%26+Analytics"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".job-card, .vacancy, .position, article"):
            title_el = item.select_one("h2, h3, h4, .title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://www.ciklum.com" + href
            jobs.append(Job(
                id=_make_id("ciklum", href),
                title=title,
                company="Ciklum",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="Ciklum",
            ))
    except Exception as e:
        print(f"[Ciklum] Error: {e}")
    return jobs


def scrape_nix() -> list[Job]:
    jobs = []
    try:
        url = "https://n-ix.com/careers/?department=data"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".vacancy, .job-card, .career-item, article"):
            title_el = item.select_one("h2, h3, h4, .title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_relevant(title):
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://n-ix.com" + href
            jobs.append(Job(
                id=_make_id("nix", href),
                title=title,
                company="N-iX",
                url=href,
                description=item.get_text(separator=" ", strip=True),
                source="N-iX",
            ))
    except Exception as e:
        print(f"[N-iX] Error: {e}")
    return jobs


def scrape_linkedin() -> list[Job]:
    """LinkedIn public job search — no auth required."""
    jobs = []
    searches = [
        "Head+of+Data+Analytics&location=Ukraine",
        "BI+Lead+Analytics&location=Ukraine",
        "Head+of+BI&location=Ukraine",
        "Head+of+Analytics+remote",
    ]
    try:
        for query in searches:
            url = f"https://www.linkedin.com/jobs/search/?keywords={query}&f_TPR=r3600"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".base-card, .job-search-card"):
                title_el = item.select_one(".base-search-card__title, h3")
                company_el = item.select_one(".base-search-card__subtitle, h4")
                link_el = item.select_one("a[href]")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_relevant(title):
                    continue
                href = link_el["href"].split("?")[0]
                jobs.append(Job(
                    id=_make_id("linkedin", href),
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "LinkedIn",
                    url=href,
                    description=item.get_text(separator=" ", strip=True),
                    source="LinkedIn",
                ))
    except Exception as e:
        print(f"[LinkedIn] Error: {e}")
    return jobs
