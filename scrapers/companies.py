"""Scrapers for company career pages using Lever/Greenhouse public APIs."""
import hashlib
import re
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

def _scrape_ashby(org_name: str, company_name: str, source_label: str) -> list[Job]:
    jobs = []
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
        slug = org_name.replace(" ", "%20")
        for j in postings:
            title = j.get("title", "")
            if not _title_match(title):
                continue
            jid = j.get("id", "")
            loc = j.get("locationName", "")
            mode = j.get("workplaceType", "")
            jobs.append(Job(
                id=_make_id(source_label, jid),
                title=title,
                company=company_name,
                url=f"https://jobs.ashbyhq.com/{slug}/{jid}",
                description=f"{loc} | {mode}".strip(" |"),
                source=source_label,
            ))
    except Exception as e:
        print(f"[{source_label}] Ashby API error: {e}")
    return jobs


# ── UA Outsourcers ────────────────────────────────────────────────────────────

def scrape_ciklum() -> list[Job]:
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
                mode = j.get("WorkplaceTypeCode", "").replace("ORA_", "").title()
                jobs.append(Job(
                    id=_make_id("ciklum", jid),
                    title=title,
                    company="Ciklum",
                    url=f"{job_base}/{jid}",
                    description=f"{country} | {mode}".strip(" |"),
                    source="Ciklum",
                ))
            offset += 25
    except Exception as e:
        print(f"[Ciklum] Error: {e}")
    return jobs

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
    return jobs

def scrape_playtika() -> list[Job]:
    return _scrape_greenhouse("playtikaltd", "Playtika", "Playtika")

def scrape_wix() -> list[Job]:
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
            loc = j.get("location", {})
            city = loc.get("city", "")
            country = loc.get("country", "")
            job_url = j.get("ref", "") or f"https://jobs.smartrecruiters.com/Wix2/{j.get('id','')}"
            jobs.append(Job(
                id=_make_id("wix", ref),
                title=title,
                company="Wix",
                url=job_url,
                description=f"{city}, {country}".strip(", "),
                source="Wix",
            ))
    except Exception as e:
        print(f"[Wix] Error: {e}")
    return jobs

def scrape_grammarly() -> list[Job]:
    return []  # no public API found


def scrape_superhuman() -> list[Job]:
    return _scrape_ashby("Superhuman Platform Inc", "Superhuman", "Superhuman")


def scrape_skelar() -> list[Job]:
    return _scrape_ashby("SKELAR", "SKELAR", "SKELAR")


def scrape_gr8tech() -> list[Job]:
    return _scrape_greenhouse("gr8tech", "GR8 Tech", "GR8 Tech")


def scrape_ajax() -> list[Job]:
    return _scrape_lever("ajax", "Ajax Systems", "Ajax")


def _scrape_workday(tenant: str, site: str, company_name: str, source_label: str, keywords: list[str]) -> list[Job]:
    jobs = []
    seen = set()
    try:
        base = f"https://{tenant}.wd1.myworkdayjobs.com"
        url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        api_headers = {**HEADERS, "Accept": "application/json", "Content-Type": "application/json"}
        for kw in keywords:
            offset = 0
            while True:
                resp = requests.post(url, headers=api_headers, json={"limit": 20, "offset": offset, "searchText": kw}, timeout=20)
                if resp.status_code != 200:
                    break
                data = resp.json()
                postings = data.get("jobPostings", [])
                total = data.get("total", 0)
                for j in postings:
                    path = j.get("externalPath", "")
                    if not path or path in seen:
                        continue
                    title = j.get("title", "")
                    if not _title_match(title):
                        continue
                    seen.add(path)
                    jobs.append(Job(
                        id=_make_id(source_label, path),
                        title=title,
                        company=company_name,
                        url=f"{base}/{site}{path}",
                        description=j.get("locationsText", ""),
                        source=source_label,
                    ))
                offset += 20
                if offset >= total or offset >= 300:
                    break
    except Exception as e:
        print(f"[{source_label}] Workday error: {e}")
    return jobs


def scrape_fractal() -> list[Job]:
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
        base = "https://career.fractal.partners"
        soup = BeautifulSoup(content, "html.parser")
        seen = set()
        for a in soup.select("a.job-card"):
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
    return jobs


def scrape_tieto() -> list[Job]:
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
    return jobs


def scrape_nixsolutions() -> list[Job]:
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
    return jobs


def scrape_zone3000() -> list[Job]:
    jobs = []
    try:
        api_headers = {**HEADERS, "Referer": "https://zone3000.net/", "Accept": "application/json"}
        resp = requests.get("https://zone3000.net/api/vacancies", headers=api_headers, timeout=15)
        resp.raise_for_status()
        for j in resp.json():
            title = j.get("title", "")
            if not _title_match(title):
                continue
            slug = j.get("url", "")
            loc = j.get("location", [])
            remote = j.get("remote", 0)
            desc = "Remote" if remote else ""
            jobs.append(Job(
                id=_make_id("zone3000", str(j.get("id", slug))),
                title=title,
                company="Zone3000",
                url=f"https://zone3000.net/vacancies/{slug}" if slug else "https://zone3000.net/vacancies",
                description=desc,
                source="Zone3000",
            ))
    except Exception as e:
        print(f"[Zone3000] Error: {e}")
    return jobs


def scrape_dxc() -> list[Job]:
    return _scrape_workday(
        tenant="dxctechnology", site="dxcjobs", company_name="DXC Technology", source_label="DXC",
        keywords=["analyst", "analytics", "bi lead", "head of data"],
    )


def scrape_squad() -> list[Job]:
    jobs = []
    try:
        api_headers = {**HEADERS, "Referer": "https://squad.tech/careers", "Accept": "application/json"}
        resp = requests.get("https://squad.tech/api/v1/vacancies?page=0&pageLimit=200", headers=api_headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        seen = set()
        for j in data.get("vacancies", []):
            title = j.get("title", "")
            if not _title_match(title):
                continue
            slug = j.get("humanReadableId", "")
            if slug in seen:
                continue
            seen.add(slug)
            offices = j.get("offices", [])
            location = offices[0].get("name", "") if offices else j.get("country", "")
            jobs.append(Job(
                id=_make_id("squad", slug),
                title=title,
                company="Squad",
                url=f"https://squad.tech/careers/{slug}" if slug else "https://squad.tech/careers",
                description=location,
                source="Squad",
            ))
    except Exception as e:
        print(f"[Squad] Error: {e}")
    return jobs


def scrape_headway() -> list[Job]:
    jobs = []
    try:
        api_headers = {**HEADERS, "Referer": "https://careers.headway.inc/"}
        resp = requests.get("https://careers.headway.inc/jobs.json", headers=api_headers, timeout=15)
        resp.raise_for_status()
        for j in resp.json().get("items", []):
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
                description=location,
                source="Headway",
            ))
    except Exception as e:
        print(f"[Headway] Error: {e}")
    return jobs


def scrape_evoplay() -> list[Job]:
    jobs = []
    try:
        api_headers = {**HEADERS, "Referer": "https://evoplay.com.ua/"}
        resp = requests.get("https://app.catsone.com/portal?id=42364", headers=api_headers, timeout=15)
        resp.raise_for_status()
        for j in resp.json().get("jobs", []):
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
                description=city,
                source="Evoplay",
            ))
    except Exception as e:
        print(f"[Evoplay] Error: {e}")
    return jobs


def scrape_globallogic() -> list[Job]:
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
                    description=location,
                    source="GlobalLogic",
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
    return jobs


def scrape_epam() -> list[Job]:
    jobs = []
    try:
        base = "https://careers.epam.com"
        api_headers = {**HEADERS, "Referer": base, "Accept": "application/json"}
        KEYWORDS = ["analyst", "analytics", "bi lead", "head of data", "head of analytics", "data lead", "business intelligence"]
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
                    title = j.get("name", "")
                    if not _title_match(title):
                        continue
                    seen.add(uid)
                    country = j.get("country", [{}])[0].get("name", "") if j.get("country") else ""
                    city = j.get("city", [{}])[0].get("name", "") if j.get("city") else ""
                    job_url = f"{base}/en/jobs/{uid}"
                    jobs.append(Job(
                        id=_make_id("epam", uid),
                        title=title,
                        company="EPAM",
                        url=job_url,
                        description=f"{city}, {country}".strip(", "),
                        source="EPAM",
                    ))
                offset += 50
                if offset >= total or offset >= 1000:
                    break
    except Exception as e:
        print(f"[EPAM] Error: {e}")
    return jobs

def scrape_lohika() -> list[Job]:
    return []  # no public API found

def scrape_sigma() -> list[Job]:
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
    return jobs


def scrape_luxoft() -> list[Job]:
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
        for keyword in ["analyst", "analytics", "business intelligence", "data lead", "bi", "manager", "director"]:
            resp = requests.get(f"{base}/ajax/filter-jobs", headers=api_headers, params={"keyword": keyword}, timeout=15)
            if resp.status_code != 200 or not resp.text.strip():
                continue
            raw = resp.json()
            vacancies = raw if isinstance(raw, list) else raw.get("data", [])
            for v in vacancies:
                title = v.get("title", "")
                if not _title_match(title):
                    continue
                vr_key = v.get("vrPkey", "") or v.get("slug", "")
                if vr_key in seen_keys:
                    continue
                seen_keys.add(vr_key)
                slug = v.get("slug", "")
                job_url = f"{base}/job/{slug}" if slug else base
                location = f"{v.get('city', '')} | {v.get('country', '')}".strip(" |")
                jobs.append(Job(
                    id=_make_id("luxoft", vr_key),
                    title=title,
                    company="Luxoft",
                    url=job_url,
                    description=f"{v.get('specialization', '')} | {location}",
                    source="Luxoft",
                ))
    except Exception as e:
        print(f"[Luxoft] Error: {e}")
    return jobs


