"""BrightData residential proxy session."""
import os
import requests

PROXY_HOST = "brd.superproxy.io"
PROXY_PORT = 33335
PROXY_USER = "brd-customer-hl_8b3a9889-zone-job_search"


def get_session() -> requests.Session:
    password = os.environ.get("BRIGHTDATA_PASSWORD", "")
    if not password:
        return requests.Session()

    proxy_url = f"http://{PROXY_USER}:{password}@{PROXY_HOST}:{PROXY_PORT}"
    session = requests.Session()
    session.proxies = {"http": proxy_url, "https": proxy_url}
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    })
    return session
