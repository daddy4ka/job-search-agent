"""Scrapers for company career pages using Lever/Greenhouse public APIs."""
import hashlib
import json
import re
import time
import requests
from scrapers.dou import Job, _title_match, TITLE_MUST_HAVE

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}


def _make_id(source: str, url: str) -> str:
    return f"{source}_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def _get_json_with_retry(url: str, headers: dict, retries: int = 2, delay: float = 1.5, timeout: int = 15):
    """GET + parse JSON, retrying on any failure (HTTP error, timeout, bad body)."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise


def _post_json_with_retry(url: str, headers: dict, json_body: dict, retries: int = 2, delay: float = 1.5, timeout: int = 20):
    """POST + parse JSON. Non-200 is a legitimate stop signal (not retried);
    only a bad/empty body on a 200 response is retried."""
    for attempt in range(retries + 1):
        resp = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except ValueError:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise


_COUNTRY = {
    "ua": "Ukraine", "pl": "Poland", "de": "Germany", "pt": "Portugal",
    "md": "Moldova", "ro": "Romania", "cz": "Czech Republic", "sk": "Slovakia",
    "hu": "Hungary", "bg": "Bulgaria", "hr": "Croatia", "rs": "Serbia",
    "gb": "UK", "nl": "Netherlands", "fr": "France", "es": "Spain",
    "it": "Italy", "at": "Austria", "ch": "Switzerland", "se": "Sweden",
    "no": "Norway", "dk": "Denmark", "fi": "Finland", "ee": "Estonia",
    "lv": "Latvia", "lt": "Lithuania", "il": "Israel", "ae": "UAE",
    "us": "USA", "ca": "Canada", "au": "Australia", "tr": "Turkey",
    "ge": "Georgia", "am": "Armenia", "kz": "Kazakhstan",
}

def _sr_location(loc: dict) -> str:
    city = loc.get("city", "")
    country = _COUNTRY.get(loc.get("country", "").lower(), loc.get("country", ""))
    place = ", ".join(filter(None, [city, country]))
    work_type = "Remote" if loc.get("remote") else ("Hybrid" if loc.get("hybrid") else "On-site")
    return " · ".join(filter(None, [work_type, place]))


# ── Lever public API ──────────────────────────────────────────────────────────

def _scrape_lever(company_slug: str, company_name: str, source_label: str) -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        total_raw = len(items)
        for item in items:
            title = item.get("text", "")
            if not _title_match(title):
                continue
            job_url = item.get("hostedUrl", "")
            description = item.get("descriptionPlain", "") or item.get("description", "")
            cats = item.get("categories", {})
            location = cats.get("location", "") or cats.get("allLocations", [""])[0] if isinstance(cats.get("allLocations"), list) else ""
            jobs.append(Job(
                id=_make_id(source_label, job_url),
                title=title,
                company=company_name,
                url=job_url,
                description=description[:2000],
                source=source_label,
                location=location,
            ))
    except Exception as e:
        print(f"[{source_label}] Lever API error: {e}")
    return jobs, total_raw


# ── Greenhouse public API ─────────────────────────────────────────────────────

def _scrape_greenhouse(company_slug: str, company_name: str, source_label: str) -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("jobs", [])
        total_raw = len(items)
        for item in items:
            title = item.get("title", "")
            if not _title_match(title):
                continue
            job_url = item.get("absolute_url", "")
            description = item.get("content", "")
            location = item.get("location", {}).get("name", "")
            jobs.append(Job(
                id=_make_id(source_label, job_url),
                title=title,
                company=company_name,
                url=job_url,
                description=description[:2000],
                source=source_label,
                location=location,
            ))
    except Exception as e:
        print(f"[{source_label}] Greenhouse API error: {e}")
    return jobs, total_raw


# ── Ashby public GraphQL API ──────────────────────────────────────────────────

_ASHBY_QUERY = """query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
    jobPostings {
      id
      title
      locationName
      workplaceType
    }
  }
}"""

def _scrape_ashby(org_name: str, company_name: str, source_label: str) -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        api_headers = {**HEADERS, "Content-Type": "application/json", "Referer": "https://jobs.ashbyhq.com/"}
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": org_name},
            "query": _ASHBY_QUERY,
        }
        resp = requests.post(
            "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams",
            headers=api_headers, json=payload, timeout=20,
        )
        resp.raise_for_status()
        postings = resp.json().get("data", {}).get("jobBoard", {}).get("jobPostings", [])
        total_raw = len(postings)
        slug = org_name.replace(" ", "%20")
        for j in postings:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            jid = j.get("id", "")
            loc = j.get("locationName", "")
            mode = j.get("workplaceType", "").replace("Remote", "Remote").replace("OnSite", "On-site").replace("Hybrid", "Hybrid")
            location = " · ".join(filter(None, [mode, loc]))
            jobs.append(Job(
                id=_make_id(source_label, jid),
                title=title,
                company=company_name,
                url=f"https://jobs.ashbyhq.com/{slug}/{jid}",
                description="",
                source=source_label,
                location=location,
            ))
    except Exception as e:
        print(f"[{source_label}] Ashby API error: {e}")
    return jobs, total_raw


# ── Breezy HR public API ──────────────────────────────────────────────────────

def _scrape_breezy(slug: str, company: str, source: str) -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        resp = requests.get(f"https://{slug}.breezy.hr/json", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        total_raw = len(items)
        for item in items:
            title = item.get("name", "")
            if not _title_match(title):
                continue
            loc = item.get("location", {})
            city = loc.get("city", "")
            country = loc.get("country", {}).get("name", "")
            remote_val = loc.get("remote_details", {}).get("value", "")
            is_remote = loc.get("is_remote", False)
            if remote_val == "remote" or (is_remote and not remote_val):
                work_type = "Remote"
            elif remote_val == "hybrid":
                work_type = "Hybrid"
            else:
                work_type = "On-site"
            place = ", ".join(filter(None, [city, country]))
            location = " · ".join(filter(None, [work_type, place]))
            jobs.append(Job(
                id=_make_id(slug, item.get("id", "")),
                title=title,
                company=company,
                url=item.get("url", ""),
                description="",
                source=source,
                location=location,
            ))
    except Exception as e:
        print(f"[{source}] Error: {e}")
    return jobs, total_raw


# ── UA Outsourcers ────────────────────────────────────────────────────────────

def scrape_ciklum() -> tuple[list[Job], int]:
    jobs = []
    seen = set()
    try:
        api = "https://ialmme.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        job_base = "https://explore-jobs.ciklum.com/en/sites/ciklum-career/job"
        api_headers = {**HEADERS, "Referer": "https://explore-jobs.ciklum.com/", "Accept": "application/json"}
        offset = 0
        total = 9999
        while offset < total:
            params = {
                "onlyData": "true",
                "expand": "requisitionList.workLocation",
                "finder": f"findReqs;siteNumber=CX_1001,facetsList=LOCATIONS;TITLES;CATEGORIES,limit=25,sortBy=POSTING_DATES_DESC,offset={offset}",
            }
            resp = requests.get(api, headers=api_headers, params=params, timeout=20)
            if resp.status_code != 200 or not resp.text.strip():
                break
            item = resp.json()["items"][0]
            reqs = item.get("requisitionList", [])
            total = item.get("TotalJobsCount", 0)
            if not reqs:
                break
            for j in reqs:
                jid = str(j.get("Id", ""))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                title = j.get("Title", "")
                if not _title_match(title):
                    continue
                country = j.get("PrimaryLocationCountry", "")
                mode = j.get("WorkplaceTypeCode", "").replace("ORA_REMOTE", "Remote").replace("ORA_", "").title()
                location = " · ".join(filter(None, [mode, country]))
                jobs.append(Job(
                    id=_make_id("ciklum", jid),
                    title=title,
                    company="Ciklum",
                    url=f"{job_base}/{jid}",
                    description="",
                    source="Ciklum",
                    location=location,
                ))
            offset += 25
    except Exception as e:
        print(f"[Ciklum] Error: {e}")
    return jobs, len(seen)

def scrape_intellias() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        base = "https://career.intellias.com"
        api_headers = {**HEADERS, "Accept": "application/json"}
        page = 1
        total_pages = 1
        while page <= total_pages:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/vacancy",
                headers=api_headers,
                params={"per_page": 100, "page": page, "_fields": "link,title,class_list"},
                timeout=15,
            )
            resp.raise_for_status()
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            items = resp.json()
            total_raw += len(items)
            for item in items:
                title = item.get("title", {}).get("rendered", "")
                if not _title_match(title):
                    continue
                job_url = item.get("link", "")
                locs = [c[len("location-"):] for c in item.get("class_list", []) if c.startswith("location-")]
                location = ", ".join(l.replace("-", " ").title() for l in locs)
                jobs.append(Job(
                    id=_make_id("intellias", job_url),
                    title=title,
                    company="Intellias",
                    url=job_url,
                    description="",
                    source="Intellias",
                    location=location,
                ))
            page += 1
    except Exception as e:
        print(f"[Intellias] Error: {e}")
    return jobs, total_raw

def scrape_nix() -> tuple[list[Job], int]:
    return _scrape_greenhouse("nix", "N-iX", "N-iX")

def scrape_eleks() -> tuple[list[Job], int]:
    return _scrape_lever("eleks", "ELEKS", "ELEKS")

def scrape_softserve() -> tuple[list[Job], int]:
    jobs = []
    seen = set()
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
                slug = v.get("urlSegment", "")
                if slug in seen:
                    continue
                seen.add(slug)
                title = v.get("name", "")
                if not _title_match(title):
                    continue
                job_url = f"{base}/en-us/vacancies/{slug}" if slug else base
                jobs.append(Job(
                    id=_make_id("softserve", job_url),
                    title=title,
                    company="SoftServe",
                    url=job_url,
                    description="",
                    source="SoftServe",
                    location=v.get("city", ""),
                ))
            meta = data.get("meta", {})
            if page >= meta.get("last_page", 1):
                break
            page += 1
    except Exception as e:
        print(f"[SoftServe] API error: {e}")
    return jobs, len(seen)

def scrape_dataart() -> tuple[list[Job], int]:
    jobs = []
    try:
        base = "https://www.dataart.team"
        api_headers = {**HEADERS, "Referer": f"{base}/vacancies", "Accept": "application/json"}
        # Data & Analytics (4667), Business Analysis (4665), Management (964)
        CATEGORY_IDS = [4667, 4665, 964]
        seen = set()
        for cat_id in CATEGORY_IDS:
            for pg in range(1, 20):
                url = f"{base}/dataart-team/api/vacancies/filter-fields-page?page={pg}&pageSize=0&categories={cat_id}"
                resp = requests.get(url, headers=api_headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                vacs = data.get("vacancies", {})
                items = vacs.get("items", []) if isinstance(vacs, dict) else []
                pages_total = vacs.get("pagesTotal", 1)
                for v in items:
                    vid = v.get("id")
                    if vid in seen:
                        continue
                    seen.add(vid)
                    title = v.get("title", "")
                    if not _title_match(title):
                        continue
                    job_url = v.get("fullUrl", base)
                    jobs.append(Job(
                        id=_make_id("dataart", str(vid)),
                        title=title,
                        company="DataArt",
                        url=job_url,
                        description=v.get("text", "")[:500],
                        source="DataArt",
                    ))
                if pg >= pages_total or not items:
                    break
    except Exception as e:
        print(f"[DataArt] Error: {e}")
    return jobs, len(seen)

def scrape_playtika() -> tuple[list[Job], int]:
    return _scrape_greenhouse("playtikaltd", "Playtika", "Playtika")

def scrape_wix() -> tuple[list[Job], int]:
    jobs = []
    try:
        url = "https://api.smartrecruiters.com/v1/companies/Wix2/postings?limit=200"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        seen = set()
        for j in resp.json().get("content", []):
            ref = j.get("refNumber") or j.get("id", "")
            if ref in seen:
                continue
            seen.add(ref)
            title = j.get("name", "")
            if not _title_match(title):
                continue
            job_url = f"https://jobs.smartrecruiters.com/Wix2/{j.get('id', '')}"
            jobs.append(Job(
                id=_make_id("wix", ref),
                title=title,
                company="Wix",
                url=job_url,
                description="",
                source="Wix",
                location=_sr_location(j.get("location", {})),
            ))
    except Exception as e:
        print(f"[Wix] Error: {e}")
    return jobs, len(seen)


def scrape_superhuman() -> tuple[list[Job], int]:
    return _scrape_ashby("Superhuman Platform Inc", "Superhuman", "Superhuman")


def scrape_skelar() -> tuple[list[Job], int]:
    return _scrape_ashby("SKELAR", "SKELAR", "SKELAR")


def scrape_gr8tech() -> tuple[list[Job], int]:
    return _scrape_greenhouse("gr8tech", "GR8 Tech", "GR8 Tech")


def scrape_ajax() -> tuple[list[Job], int]:
    return _scrape_lever("ajax", "Ajax Systems", "Ajax")


def scrape_capitalcom() -> tuple[list[Job], int]:
    return _scrape_lever("capital", "Capital.com", "Capital.com")


def _scrape_workday(tenant: str, site: str, company_name: str, source_label: str, keywords: list[str]) -> tuple[list[Job], int]:
    jobs = []
    seen = set()
    try:
        base = f"https://{tenant}.wd1.myworkdayjobs.com"
        url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        api_headers = {**HEADERS, "Accept": "application/json", "Content-Type": "application/json"}
        for kw in keywords:
            offset = 0
            while True:
                data = _post_json_with_retry(url, api_headers, {"limit": 20, "offset": offset, "searchText": kw})
                if data is None:
                    break
                postings = data.get("jobPostings", [])
                total = data.get("total", 0)
                for j in postings:
                    path = j.get("externalPath", "")
                    if not path or path in seen:
                        continue
                    seen.add(path)
                    title = j.get("title", "")
                    if not _title_match(title):
                        continue
                    jobs.append(Job(
                        id=_make_id(source_label, path),
                        title=title,
                        company=company_name,
                        url=f"{base}/{site}{path}",
                        description="",
                        source=source_label,
                        location=j.get("locationsText", ""),
                    ))
                offset += 20
                if offset >= total or offset >= 300:
                    break
    except Exception as e:
        print(f"[{source_label}] Workday error: {e}")
    return jobs, len(seen)


def scrape_temabit() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        from bs4 import BeautifulSoup
        resp = requests.get("https://careers.temabit.com/job-sitemap.xml", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        urls = [loc.text for loc in soup.find_all("loc") if "/job/" in loc.text]
        total_raw = len(urls)
        for url in urls:
            slug = url.rstrip("/").split("/")[-1]
            title = slug.replace("-", " ").title()
            if not _title_match(title):
                continue
            jobs.append(Job(
                id=_make_id("temabit", slug),
                title=title,
                company="Temabit / Fozzy Group",
                url=url,
                description="Ukraine",
                source="Temabit",
            ))
    except Exception as e:
        print(f"[Temabit] Error: {e}")
    return jobs, total_raw


def scrape_novadigital() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        api_headers = {**HEADERS, "Accept": "application/json", "Referer": "https://novadigital.com/"}
        resp = requests.get(
            "https://jobs.dou.ua/companies/nova-digital/vacancies/export/?lang=en",
            headers=api_headers, timeout=15,
        )
        resp.raise_for_status()
        items = resp.json()
        total_raw = len(items)
        for j in items:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            jobs.append(Job(
                id=_make_id("novadigital", j.get("link", title)),
                title=title,
                company="Nova Digital",
                url=j.get("link", "https://novadigital.com/careers"),
                description=j.get("location", ""),
                source="Nova Digital",
            ))
    except Exception as e:
        print(f"[Nova Digital] Error: {e}")
    return jobs, total_raw


def scrape_fractal() -> tuple[list[Job], int]:
    jobs = []
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()
            page.goto("https://career.fractal.partners/ua/vacancy/", timeout=90000, wait_until="domcontentloaded")
            try:
                page.wait_for_selector("a.job-card", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(4000)
            content = page.content()
            browser.close()

        lowered = content.lower()
        blockers = [m for m in ["just a moment", "attention required", "cf-browser-verification",
                                 "checking your browser", "captcha", "cloudflare", "access denied"]
                    if m in lowered]
        print(f"[Fractal Partners] DEBUG html_len={len(content)} block_markers={blockers}")

        base = "https://career.fractal.partners"
        soup = BeautifulSoup(content, "html.parser")
        cards = soup.select("a.job-card")
        print(f"[Fractal Partners] DEBUG job-card elements: {len(cards)}")
        seen = set()
        for a in cards:
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            h3 = a.select_one("h3.job-title-text")
            if not h3:
                continue
            title = re.sub(r"[\U0001F300-\U0001FFFF]", "", h3.get_text(strip=True)).strip()
            if not title or not _title_match(title):
                continue
            jobs.append(Job(
                id=_make_id("fractal", href),
                title=title,
                company="Fractal Partners",
                url=base + href if not href.startswith("http") else href,
                description="Ukraine",
                source="Fractal Partners",
            ))
    except Exception as e:
        print(f"[Fractal Partners] Error: {e}")
    return jobs, len(seen)


def scrape_tieto() -> tuple[list[Job], int]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        page_headers = {**HEADERS, "Accept": "text/html"}
        base = "https://careers.tieto.com"
        seen = set()
        for page_num in range(1, 60):
            resp = requests.get(f"{base}/jobs?q=&options=&page={page_num}", headers=page_headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = {
                a.get("href"): a.get_text(strip=True)
                for a in soup.select("a[href^='/job/']")
                if a.get_text(strip=True) and "Apply" not in a.get_text(strip=True)
            }
            new_hrefs = [h for h in links if h not in seen]
            if not new_hrefs:
                break
            for href in new_hrefs:
                seen.add(href)
                title = links[href]
                if not _title_match(title):
                    continue
                jobs.append(Job(
                    id=_make_id("tieto", href),
                    title=title,
                    company="TietoEVRY",
                    url=base + href,
                    description="",
                    source="TietoEVRY",
                ))
    except Exception as e:
        print(f"[TietoEVRY] Error: {e}")
    return jobs, len(seen)


def scrape_nixsolutions() -> tuple[list[Job], int]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        page_headers = {**HEADERS, "Accept": "text/html", "Accept-Language": "en,uk;q=0.9"}
        resp = requests.get("https://www.nixsolutions.com/ua/cooperation/vacancies/", headers=page_headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        base = "https://www.nixsolutions.com"
        seen = set()
        for a in soup.select("a[href*='/vacancies/']"):
            href = a.get("href", "")
            if not href.startswith("http"):
                href = base + href
            slug = href.rstrip("/").split("/")[-1]
            if not slug or slug == "vacancies":
                continue
            title = a.get_text(strip=True)
            if not title or href in seen:
                continue
            seen.add(href)
            if not _title_match(title):
                continue
            jobs.append(Job(
                id=_make_id("nixsolutions", slug),
                title=title,
                company="NIX Solutions",
                url=href,
                description="Ukraine",
                source="NIX Solutions",
            ))
    except Exception as e:
        print(f"[NIX Solutions] Error: {e}")
    return jobs, len(seen)


def scrape_zone3000() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        api_headers = {**HEADERS, "Referer": "https://zone3000.net/", "Accept": "application/json"}
        resp = requests.get("https://zone3000.net/api/vacancies", headers=api_headers, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        total_raw = len(items)
        for j in items:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            slug = j.get("url", "")
            loc = j.get("location", [])
            remote = j.get("remote", 0)
            jobs.append(Job(
                id=_make_id("zone3000", str(j.get("id", slug))),
                title=title,
                company="Zone3000",
                url=f"https://zone3000.net/vacancies/{slug}" if slug else "https://zone3000.net/vacancies",
                description="",
                source="Zone3000",
                location="Remote" if remote else "Ukraine",
            ))
    except Exception as e:
        print(f"[Zone3000] Error: {e}")
    return jobs, total_raw


def scrape_dxc() -> tuple[list[Job], int]:
    return _scrape_workday(
        tenant="dxctechnology", site="dxcjobs", company_name="DXC Technology", source_label="DXC",
        keywords=["analyst", "analytics", "bi lead", "head of data"],
    )


def scrape_squad() -> tuple[list[Job], int]:
    jobs = []
    seen = set()
    try:
        api_headers = {**HEADERS, "Referer": "https://squad.tech/careers", "Accept": "application/json"}
        resp = requests.get("https://squad.tech/api/v1/vacancies?page=0&pageLimit=200", headers=api_headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get("vacancies", []):
            slug = j.get("humanReadableId", "")
            if slug in seen:
                continue
            seen.add(slug)
            title = j.get("title", "")
            if not _title_match(title):
                continue
            offices = j.get("offices", [])
            location = offices[0].get("name", "") if offices else j.get("country", "")
            jobs.append(Job(
                id=_make_id("squad", slug),
                title=title,
                company="Squad",
                url=f"https://squad.tech/careers/{slug}" if slug else "https://squad.tech/careers",
                description="",
                source="Squad",
                location=location,
            ))
    except Exception as e:
        print(f"[Squad] Error: {e}")
    return jobs, len(seen)


def scrape_headway() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        api_headers = {**HEADERS, "Referer": "https://careers.headway.inc/"}
        resp = requests.get("https://careers.headway.inc/jobs.json", headers=api_headers, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        total_raw = len(items)
        for j in items:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            jp = j.get("_jobposting", {})
            loc = jp.get("jobLocation", {})
            if isinstance(loc, dict):
                addr = loc.get("address", {})
                location = ", ".join(filter(None, [addr.get("addressLocality", ""), addr.get("addressCountry", "")]))
            else:
                location = ""
            jobs.append(Job(
                id=_make_id("headway", j.get("id", "")),
                title=title,
                company="Headway",
                url=j.get("url", "https://careers.headway.inc/jobs"),
                description="",
                source="Headway",
                location=location,
            ))
    except Exception as e:
        print(f"[Headway] Error: {e}")
    return jobs, total_raw


def scrape_evoplay() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        api_headers = {**HEADERS, "Referer": "https://evoplay.com.ua/"}
        data = _get_json_with_retry("https://app.catsone.com/portal?id=42364", api_headers)
        items = data.get("jobs", [])
        total_raw = len(items)
        for j in items:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            loc = j.get("location", {})
            city = loc.get("city", "") or loc.get("state", "")
            jobs.append(Job(
                id=_make_id("evoplay", str(j.get("id", ""))),
                title=title,
                company="Evoplay",
                url=j.get("url", "https://evoplay.com.ua/uk/career/"),
                description="",
                source="Evoplay",
                location=city,
            ))
    except Exception as e:
        print(f"[Evoplay] Error: {e}")
    return jobs, total_raw


def scrape_globallogic() -> tuple[list[Job], int]:
    import re as _re
    import time as _time
    from bs4 import BeautifulSoup

    jobs = []
    seen = set()

    try:
        base = "https://www.globallogic.com"
        page_headers = {**HEADERS, "Accept": "text/html"}
        page = 1
        while True:
            url = (
                f"{base}/career-search-page/?experience=none&location=none"
                if page == 1
                else f"{base}/career-search-page/page/{page}/?experience=none&location=none"
            )
            resp = requests.get(url, headers=page_headers, timeout=20)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            job_boxes = soup.select("a.job_box")
            if not job_boxes:
                break
            for jb in job_boxes:
                href = jb.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                h4 = jb.select_one("h4")
                if not h4:
                    continue
                title = _re.sub(r"\s*IRC\d+(-\d+)?\s*$", "", h4.get_text(strip=True)).strip()
                if not _title_match(title):
                    continue
                location_parts = [s.get_text(strip=True) for s in jb.select(".job_location, .job_tag")]
                location = " | ".join(p for p in location_parts if p)
                jobs.append(Job(
                    id=_make_id("globallogic", href),
                    title=title,
                    company="GlobalLogic",
                    url=href,
                    description="",
                    source="GlobalLogic",
                    location=location,
                ))
            next_link = soup.select_one("a.next, a[rel='next']")
            if not next_link:
                max_pg = page
                for pl in soup.select("a.page-numbers:not(.next):not(.prev)"):
                    try:
                        n = int(pl.get_text(strip=True))
                        if n > max_pg:
                            max_pg = n
                    except ValueError:
                        pass
                if page >= max_pg:
                    break
            page += 1
            _time.sleep(0.3)
    except Exception as e:
        print(f"[GlobalLogic] Error: {e}")
    return jobs, len(seen)


def scrape_epam() -> tuple[list[Job], int]:
    jobs = []
    try:
        base = "https://careers.epam.com"
        api_headers = {**HEADERS, "Referer": base, "Accept": "application/json"}
        KEYWORDS = TITLE_MUST_HAVE
        seen = set()
        for kw in KEYWORDS:
            offset = 0
            while True:
                resp = requests.get(
                    f"{base}/api/jobs/v2/search/careers-i18n",
                    headers=api_headers,
                    params={"from": offset, "lang": "en", "q": kw, "size": 50},
                    timeout=15,
                )
                if resp.status_code != 200 or not resp.text.strip():
                    break
                data = resp.json().get("data", {})
                items = data.get("jobs", [])
                total = data.get("total", 0)
                for j in items:
                    uid = j.get("uid") or j.get("_key", "")
                    if not uid or uid in seen:
                        continue
                    seen.add(uid)
                    title = j.get("name", "")
                    if not _title_match(title):
                        continue
                    country = j.get("country", [{}])[0].get("name", "") if j.get("country") else ""
                    city = j.get("city", [{}])[0].get("name", "") if j.get("city") else ""
                    seo_url = j.get("seo", {}).get("url", "")
                    job_url = f"{base}{seo_url}" if seo_url else f"{base}/en/jobs/{uid}"
                    jobs.append(Job(
                        id=_make_id("epam", uid),
                        title=title,
                        company="EPAM",
                        url=job_url,
                        description="",
                        source="EPAM",
                        location=", ".join(filter(None, [city, country])),
                    ))
                offset += 50
                if offset >= total or offset >= 1000:
                    break
    except Exception as e:
        print(f"[EPAM] Error: {e}")
    return jobs, len(seen)

def scrape_lohika() -> tuple[list[Job], int]:
    return [], 0  # no public API found

def scrape_sigma() -> tuple[list[Job], int]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        base = "https://career.sigma.software"
        ajax_url = f"{base}/wp-admin/admin-ajax.php"
        headers = {
            **HEADERS,
            "Referer": f"{base}/what-we-offer/vacancies/",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        seen = set()

        def _parse_page(html: str):
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", class_="vacancy-card-new"):
                href = a.get("href", "")
                if href in seen:
                    continue
                seen.add(href)
                title_el = a.select_one("h3")
                title = title_el.get_text(strip=True)[:120] if title_el else ""
                if not _title_match(title):
                    continue
                jobs.append(Job(
                    id=_make_id("sigma", href),
                    title=title,
                    company="Sigma Software",
                    url=href,
                    description=a.get_text(separator=" ", strip=True)[:500],
                    source="Sigma",
                ))

        r0 = requests.post(ajax_url, headers=headers, timeout=15,
            data="action=filter_vacancies_v2&keyword=&direction=%5B%5D&direction_type=children&locations=%5B%5D&seniority=%5B%5D&workplace_type=%5B%5D")
        _parse_page(r0.json().get("data", {}).get("html", ""))

        for page in range(1, 20):
            r = requests.post(ajax_url, headers=headers, timeout=15,
                data=f"action=filter_vacancies_v2_loadmore&page={page}&direction=%5B%5D&direction_type=children&locations=%5B%5D&seniority=%5B%5D&workplace_type=%5B%5D&keyword=")
            html = r.json().get("data", {}).get("html", "") if r.json() else ""
            if not html:
                break
            _parse_page(html)
    except Exception as e:
        print(f"[Sigma] Error: {e}")
    return jobs, len(seen)


def scrape_luxoft() -> tuple[list[Job], int]:
    jobs = []
    try:
        base = "https://career.luxoft.com"
        api_headers = {
            **HEADERS,
            "Referer": f"{base}/jobs",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        seen_keys = set()
        for keyword in TITLE_MUST_HAVE:
            resp = requests.get(f"{base}/ajax/filter-jobs", headers=api_headers, params={"keyword": keyword}, timeout=15)
            if resp.status_code != 200 or not resp.text.strip():
                continue
            raw = resp.json()
            vacancies = raw if isinstance(raw, list) else raw.get("data", [])
            for v in vacancies:
                vr_key = v.get("vrPkey", "") or v.get("slug", "")
                if vr_key in seen_keys:
                    continue
                seen_keys.add(vr_key)
                title = v.get("title", "")
                if not _title_match(title):
                    continue
                slug = v.get("slug", "")
                job_url = f"{base}/jobs/{slug}" if slug else base
                location = ", ".join(filter(None, [v.get("city", ""), v.get("country", "")]))
                jobs.append(Job(
                    id=_make_id("luxoft", vr_key),
                    title=title,
                    company="Luxoft",
                    url=job_url,
                    description="",
                    source="Luxoft",
                    location=location,
                ))
    except Exception as e:
        print(f"[Luxoft] Error: {e}")
    return jobs, len(seen_keys)


def scrape_autodoc() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        offset = 0
        while True:
            resp = requests.get(
                "https://api.smartrecruiters.com/v1/companies/Autodoc3/postings",
                headers=HEADERS, params={"limit": 100, "offset": offset}, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("content", [])
            if not items:
                break
            total_raw += len(items)
            for j in items:
                title = j.get("name", "")
                if not _title_match(title):
                    continue
                job_id = j.get("id", "")
                slug = j.get("ref", job_id)
                url = f"https://jobs.smartrecruiters.com/Autodoc3/{job_id}"
                jobs.append(Job(
                    id=_make_id("autodoc", url),
                    title=title,
                    company="Autodoc",
                    url=url,
                    description="",
                    source="Autodoc",
                    location=_sr_location(j.get("location", {})),
                ))
            offset += len(items)
            if offset >= data.get("totalFound", 0):
                break
    except Exception as e:
        print(f"[Autodoc] Error: {e}")
    return jobs, total_raw


def scrape_allstarsit() -> tuple[list[Job], int]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        base = "https://www.allstarsit.com"
        seen = set()
        for page in range(1, 20):
            resp = requests.get(f"{base}/careers/jobs?page={page}", headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                if "/job-posts/" not in a["href"]:
                    continue
                title_el = a.select_one(".text-block-90") or a.select_one("[class*='text-block']")
                title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                links.append((title, a["href"]))
            new = [(t, h) for t, h in links if h not in seen]
            if not new:
                break
            for title, path in new:
                seen.add(path)
                if not _title_match(title):
                    continue
                url = f"{base}{path}" if path.startswith("/") else path
                jobs.append(Job(
                    id=_make_id("allstarsit", url),
                    title=title,
                    company="AllStarsIT",
                    url=url,
                    description="",
                    source="AllStarsIT",
                ))
    except Exception as e:
        print(f"[AllStarsIT] Error: {e}")
    return jobs, len(seen)


def scrape_jooble() -> list[Job]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        base = "https://careers.jooble.com"
        headers = {**HEADERS, "Accept": "text/html"}
        seen = set()
        for page in range(1, 20):
            resp = requests.get(f"{base}/jobs?page={page}", headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = [(a.get_text(strip=True), a["href"]) for a in soup.find_all("a", href=True)
                     if "/jobs/" in a["href"] and a["href"] != f"{base}/jobs" and "applications" not in a["href"]]
            new = [(t, h) for t, h in links if h not in seen]
            if not new:
                break
            for title, url in new:
                seen.add(url)
                if not _title_match(title):
                    continue
                jobs.append(Job(
                    id=_make_id("jooble", url),
                    title=title,
                    company="Jooble",
                    url=url,
                    description="",
                    source="Jooble",
                ))
    except Exception as e:
        print(f"[Jooble] Error: {e}")
    return jobs


def scrape_obrio() -> tuple[list[Job], int]:
    return _scrape_ashby("OBRIO", "OBRIO", "OBRIO")

def scrape_ideals() -> tuple[list[Job], int]:
    return _scrape_ashby("ideals", "iDeals", "iDeals")


def scrape_betterme() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        resp = requests.get("https://betterme.breezy.hr/json", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        total_raw = len(items)
        for j in items:
            title = j.get("name", "")
            if not _title_match(title):
                continue
            url = j.get("url", "")
            loc = j.get("location", {})
            location = ", ".join(filter(None, [loc.get("city", ""), loc.get("country", {}).get("name", "")]))
            jobs.append(Job(
                id=_make_id("betterme", url),
                title=title,
                company="BetterMe",
                url=url,
                description="",
                source="BetterMe",
                location=location,
            ))
    except Exception as e:
        print(f"[BetterMe] Error: {e}")
    return jobs, total_raw


def scrape_avenga() -> tuple[list[Job], int]:
    jobs = []
    try:
        from bs4 import BeautifulSoup
        base = "https://career.avenga.com"
        headers = {**HEADERS, "Accept": "text/html"}
        seen = set()
        for page in range(1, 30):
            resp = requests.get(f"{base}/jobs?page={page}", headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = [(a.get_text(strip=True), a["href"]) for a in soup.find_all("a", href=True)
                     if "/jobs/" in a["href"] and a["href"] != f"{base}/jobs"]
            new = [(t, h) for t, h in links if h not in seen]
            if not new:
                break
            for title, url in new:
                seen.add(url)
                if not _title_match(title):
                    continue
                jobs.append(Job(
                    id=_make_id("avenga", url),
                    title=title,
                    company="Avenga",
                    url=url,
                    description="",
                    source="Avenga",
                ))
    except Exception as e:
        print(f"[Avenga] Error: {e}")
    return jobs, len(seen)


def _scrape_hurma(slug: str, company_name: str, source_label: str) -> tuple[list[Job], int]:
    """Hurma-hosted career sites (hurma.work) expose vacancies via a paginated JSON API."""
    jobs = []
    total_raw = 0
    try:
        base = f"https://{slug}.hurma.work"
        headers = {**HEADERS, "Accept": "application/json"}
        page = 1
        while True:
            resp = requests.get(f"{base}/api/vacancies?page={page}", headers=headers, timeout=15)
            resp.raise_for_status()
            result = resp.json().get("result", {})
            items = result.get("data", [])
            total_raw += len(items)
            for v in items:
                title = v.get("name", "")
                if not _title_match(title):
                    continue
                vid = str(v.get("id", ""))
                job_url = f"{base}/public-vacancies/{vid}"
                jobs.append(Job(
                    id=_make_id(source_label, vid),
                    title=title,
                    company=company_name,
                    url=job_url,
                    description="",
                    source=source_label,
                    location=v.get("residence", ""),
                ))
            if page >= result.get("last_page", 1):
                break
            page += 1
    except Exception as e:
        print(f"[{source_label}] Error: {e}")
    return jobs, total_raw


def scrape_whitebit() -> tuple[list[Job], int]:
    return _scrape_hurma("whitebit", "WhiteBit", "WhiteBit")


def scrape_dataforest() -> tuple[list[Job], int]:
    return _scrape_hurma("dataforest", "Dataforest", "Dataforest")


def scrape_griddynamics() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        from bs4 import BeautifulSoup
        base = "https://www.griddynamics.com"
        resp = requests.get(f"{base}/careers/discover-openings", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("a.job-row[href*='/careers/vacancy/']")
        total_raw = len(cards)
        for a in cards:
            title_el = a.select_one(".job-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not _title_match(title):
                continue
            location_el = a.select_one(".job-location")
            location = location_el.get_text(strip=True) if location_el else ""
            url = f"{base}{a['href']}"
            jobs.append(Job(
                id=_make_id("griddynamics", url),
                title=title,
                company="Grid Dynamics",
                url=url,
                description="",
                source="Grid Dynamics",
                location=location,
            ))
    except Exception as e:
        print(f"[GridDynamics] Error: {e}")
    return jobs, total_raw


def scrape_genesis() -> tuple[list[Job], int]:
    return _scrape_breezy("gen-tech", "Genesis", "Genesis")


def scrape_uklon() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        base = "https://careers.uklon.net"
        resp = requests.get(f"{base}/vacancies-ua", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        pattern = (
            r'📍([^<]+)</span></span></p>'
            r'<p[^>]+w-heading[^>]+><span[^>]+><span[^>]+>([^<]+)</span>'
            r'.*?href="(/ua-[^"]+)"'
        )
        for m in re.finditer(pattern, resp.text, re.DOTALL):
            total_raw += 1
            title = m.group(2).strip()
            if not _title_match(title):
                continue
            loc_raw = m.group(1).replace('&nbsp;', ' ')
            loc_part = re.split(r'[‍]?💎', loc_raw)[0].replace('📍', '').strip()
            url_path = m.group(3)
            jobs.append(Job(
                id=_make_id("uklon", url_path),
                title=title,
                company="Uklon",
                url=base + url_path,
                description="",
                source="Uklon",
                location=loc_part,
            ))
    except Exception as e:
        print(f"[Uklon] Error: {e}")
    return jobs, total_raw


def scrape_macpaw() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        base = "https://macpaw.com"
        resp = requests.get(f"{base}/careers-all", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        positions = []
        for m in re.finditer(r'self\.__next_f\.push\(\[1,(".*?")\]\)', resp.text):
            try:
                s = json.loads(m.group(1))
            except Exception:
                continue
            if isinstance(s, str) and '"positions":[' in s:
                start = s.index('"positions":[') + len('"positions":')
                depth = 0
                end = start
                for i in range(start, len(s)):
                    if s[i] == '[':
                        depth += 1
                    elif s[i] == ']':
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                positions = json.loads(s[start:end + 1])
                break
        total_raw = len(positions)
        for p in positions:
            title = p.get("title", "")
            if not _title_match(title):
                continue
            slug = p.get("slug", "")
            jobs.append(Job(
                id=_make_id("macpaw", slug),
                title=title,
                company="MacPaw",
                url=f"{base}/careers/{slug}",
                description="",
                source="MacPaw",
                location=p.get("location", ""),
            ))
    except Exception as e:
        print(f"[MacPaw] Error: {e}")
    return jobs, total_raw


def scrape_readdle() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        from bs4 import BeautifulSoup
        base = "https://readdle.com"
        resp = requests.get(f"{base}/careers", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.vacancy-card")
        total_raw = len(cards)
        for c in cards:
            pos_el = c.select_one("span.position")
            a_el = c.select_one("a[href]")
            if not pos_el or not a_el:
                continue
            title = pos_el.get_text(strip=True)
            if not _title_match(title):
                continue
            href = a_el.get("href", "")
            job_url = base + href if href.startswith("/") else href
            jobs.append(Job(
                id=_make_id("readdle", href),
                title=title,
                company="Readdle",
                url=job_url,
                description="",
                source="Readdle",
                location=c.get("data-location", ""),
            ))
    except Exception as e:
        print(f"[Readdle] Error: {e}")
    return jobs, total_raw


def _scrape_teamtailor(base_url: str, company_name: str, source_label: str) -> tuple[list[Job], int]:
    """Teamtailor career sites expose all vacancies as a JSON Feed at /jobs.json."""
    jobs = []
    total_raw = 0
    try:
        resp = requests.get(f"{base_url}/jobs.json", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        total_raw = len(items)
        for j in items:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            jp = j.get("_jobposting", {})
            loc_raw = jp.get("jobLocation", []) if isinstance(jp, dict) else []
            if isinstance(loc_raw, list) and loc_raw:
                addr = loc_raw[0].get("address", {})
            elif isinstance(loc_raw, dict):
                addr = loc_raw.get("address", {})
            else:
                addr = {}
            location = ", ".join(filter(None, [addr.get("addressLocality", ""), addr.get("addressCountry", "")]))
            jobs.append(Job(
                id=_make_id(source_label, j.get("id", "")),
                title=title,
                company=company_name,
                url=j.get("url", f"{base_url}/jobs"),
                description="",
                source=source_label,
                location=location,
            ))
    except Exception as e:
        print(f"[{source_label}] Error: {e}")
    return jobs, total_raw


def scrape_upstars() -> tuple[list[Job], int]:
    return _scrape_teamtailor("https://career.upstars.com", "Upstars", "Upstars")


def scrape_dripify() -> tuple[list[Job], int]:
    return _scrape_teamtailor("https://career.dripify.com", "Dripify", "Dripify")


def scrape_pmgroup() -> tuple[list[Job], int]:
    return _scrape_teamtailor("https://talent.pm.group", "PM Group", "PM Group")


def scrape_galaktica() -> tuple[list[Job], int]:
    jobs = []
    total_raw = 0
    try:
        from bs4 import BeautifulSoup
        base = "https://www.galaktica.io"
        seen = set()
        for page in range(1, 15):
            url = f"{base}/careers" if page == 1 else f"{base}/careers?05cb77c9_page={page}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("a.card-career")
            new_cards = [c for c in cards if c.get("href", "") not in seen]
            if not new_cards:
                break
            for a in new_cards:
                href = a.get("href", "")
                seen.add(href)
                title_el = a.select_one("h3")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _title_match(title):
                    continue
                job_url = base + href if href.startswith("/") else href
                jobs.append(Job(
                    id=_make_id("galaktica", href),
                    title=title,
                    company="Galaktica",
                    url=job_url,
                    description="",
                    source="Galaktica",
                    location="",
                ))
        total_raw = len(seen)
    except Exception as e:
        print(f"[Galaktica] Error: {e}")
    return jobs, total_raw
