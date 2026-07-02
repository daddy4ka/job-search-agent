import requests
from bs4 import BeautifulSoup
from scrapers.dou import Job, _title_match

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
MAX_PAGES = 10  # safety cap; Djinni clamps to its last page once exhausted

DJINNI_KEYWORDS = [
    "Data Science",
    "Data Analytics",
    "Business Intelligence",
    "Product Management",
    "Analytics",
    "Data Engineer",
]


def _parse_items(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("div.job-item"):
        job_id = card.get("id", "").replace("job-item-", "")
        title_el = card.select_one("h2.job-item__position")
        if not job_id or not title_el:
            continue
        company_el = card.select_one("span.small.text-gray-800")
        link_el = card.select_one("a.job_item__header-link")
        link = link_el.get("href", "") if link_el else f"/jobs/{job_id}/"
        items.append({
            "id": job_id,
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "Djinni",
            "link": "https://djinni.co" + link if link.startswith("/") else link,
        })
    return items


def scrape() -> tuple[list, int]:
    jobs = []
    seen_ids = set()
    session = requests.Session()

    for kw in DJINNI_KEYWORDS:
        try:
            prev_ids = set()
            for page in range(1, MAX_PAGES + 1):
                resp = session.get(
                    "https://djinni.co/jobs/",
                    params={"primary_keyword": kw, "page": page},
                    headers=HEADERS, timeout=20,
                )
                resp.raise_for_status()
                items = _parse_items(resp.text)
                page_ids = {it["id"] for it in items}
                if not page_ids or page_ids <= prev_ids:
                    break
                prev_ids = page_ids
                for it in items:
                    if it["id"] in seen_ids:
                        continue
                    seen_ids.add(it["id"])
                    if not _title_match(it["title"]):
                        continue
                    jobs.append(Job(
                        id=f"djinni_{it['id']}",
                        title=it["title"],
                        company=it["company"],
                        url=it["link"],
                        description="",
                        source="Djinni.co",
                    ))
        except Exception as e:
            print(f"[Djinni] Error fetching {kw}: {e}")

    print(f"  [Djinni] {len(jobs)} jobs after title filter")
    return jobs, len(seen_ids)
