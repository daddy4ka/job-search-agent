"""BrightData residential proxy session."""
import os
import requests

PROXY_HOST = "brd.superproxy.io"
PROXY_PORT = 33335


def get_session() -> requests.Session:
    user = os.environ.get("BRIGHTDATA_USER", "")
    password = os.environ.get("BRIGHTDATA_PASSWORD", "")
    if not user or not password:
        return requests.Session()

    proxy_url = f"http://{user}:{password}@{PROXY_HOST}:{PROXY_PORT}"
    session = requests.Session()
    session.proxies = {"http": proxy_url, "https": proxy_url}
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    })
    return session
