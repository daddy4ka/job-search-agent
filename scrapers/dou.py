import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass

@dataclass
class Job:
    id: str
    title: str
    company: str
    url: str
    description: str
    source: str
    location: str = ""


TITLE_MUST_HAVE = [
    # Generic
    "analyst", "analytics", "operations",
    # Head-level
    "head of data", "head of analytics", "head of bi", "head of business intelligence",
    "head of r&d", "head of research", "head of insight", "head of insights",
    "head of growth", "head of strategy", "head of performance",
    "head of product analytics", "head of data science",
    # Lead-level
    "bi lead", "data lead", "analytics lead",
    "business intelligence lead", "business intelligence manager",
    "analytics chapter lead", "growth lead", "strategy lead", "insights lead",
    "insight lead",
    # Manager/Director/VP
    "data analytics manager", "analytics manager",
    "director of data", "director of analytics",
    "chief data", "cdo", "vp of data", "vp of analytics",
    "growth manager", "insights manager", "insight manager",
    "performance manager", "revenue operations manager",
    "product analytics manager", "data science manager",
    "marketing strategy manager", "marketing manager", "strategy manager",
    # Governance & strategy
    "data governance lead", "data office",
    "strategic analytics", "decision science", "decision analytics",
    "revenue analytics",
    # Analyst roles
    "lead data analyst", "senior data analyst", "principal data",
    "data analyst", "bi analyst", "business intelligence analyst",
    "analytics analyst", "marketing analyst", "product analyst",
    "growth analyst", "insights analyst", "insight analyst",
    "аналітик", "дата аналітик", "бі аналітик",
    # R&D
    "r&d team lead", "r&d lead", "research and development lead",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
BASE = "https://jobs.dou.ua/vacancies/"
MAX_BATCHES = 20  # safety cap on "load more" pages per search

# HTML search + pagination captures far more than the RSS feeds (each RSS feed
# is hard-capped at the latest 25 items regardless of how many actually match).
DOU_SEARCHES = [
    {"search": "analyst"},
    {"search": "analytics"},
    {"search": "head of data"},
    {"search": "head of analytics"},
    {"search": "bi analyst"},
    {"search": "data lead"},
    {"search": "bi lead"},
    {"search": "data manager"},
    {"search": "head of bi"},
    {"search": "analytics manager"},
    {"search": "operations"},
    {"search": "аналітик"},
    {"search": "аналітика"},
    {"category": "Analytics / BI"},
    {"category": "Data Science"},
    {"category": "Management"},
]


def _title_match(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TITLE_MUST_HAVE)


def _parse_items(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("li.l-vacancy"):
        title_el = li.select_one("a.vt")
        if not title_el:
            continue
        link = title_el.get("href", "").split("?")[0]
        job_id_m = re.search(r'/vacancies/(\d+)/', link)
        if not job_id_m:
            continue
        company_el = li.select_one("a.company")
        loc_el = li.select_one("span.cities")
        desc_el = li.select_one("div.sh-info")
        items.append({
            "id": job_id_m.group(1),
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "DOU",
            "location": loc_el.get_text(strip=True) if loc_el else "",
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "link": link,
        })
    return items


def _scrape_search(params: dict, session: requests.Session) -> list[dict]:
    resp = session.get(BASE, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    csrf = session.cookies.get("csrftoken", "")

    all_items = _parse_items(resp.text)
    seen_ids = {it["id"] for it in all_items}

    xhr_headers = {
        **HEADERS,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": resp.url,
        "X-CSRFToken": csrf,
    }

    for _ in range(MAX_BATCHES):
        r = session.post(
            f"{BASE}xhr-load/",
            params=params,
            data={"count": len(all_items)},
            headers=xhr_headers,
            timeout=20,
        )
        if r.status_code != 200:
            break
        try:
            fragment = r.json().get("html", "")
        except ValueError:
            break
        batch = _parse_items(fragment)
        new_batch = [it for it in batch if it["id"] not in seen_ids]
        if not new_batch:
            break
        for it in new_batch:
            seen_ids.add(it["id"])
            all_items.append(it)

    return all_items


def scrape() -> tuple[list, int]:
    jobs = []
    seen_ids = set()
    session = requests.Session()

    for params in DOU_SEARCHES:
        try:
            items = _scrape_search(params, session)
        except Exception as e:
            print(f"[DOU] Error fetching {params}: {e}")
            continue
        for it in items:
            if it["id"] in seen_ids:
                continue
            seen_ids.add(it["id"])
            if not _title_match(it["title"]):
                continue
            jobs.append(Job(
                id=f"dou_{it['id']}",
                title=it["title"],
                company=it["company"],
                url=it["link"],
                description=it["description"],
                source="DOU.ua",
                location=it["location"],
            ))

    print(f"  [DOU] {len(jobs)} jobs after title filter")
    return jobs, len(seen_ids)
