"""Main orchestrator — scrape all sources, filter new, notify."""
from collections import defaultdict
from datetime import datetime, timezone
from config import SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.telegram import scrape as scrape_telegram
from scrapers.companies import (
    scrape_intellias, scrape_eleks, scrape_nix, scrape_lohika,
    scrape_playtika, scrape_softserve, scrape_luxoft, scrape_sigma,
)
from scrapers.boards import scrape_weworkremotely, scrape_remoteco, scrape_relocate, scrape_otta
from scrapers.playwright_scraper import (
    scrape_ciklum, scrape_dataart,
    scrape_grammarly, scrape_wix,
)
from tracker import filter_new, mark_seen
from notifier import send_job, send_summary


SCRAPERS = {
    # UA outsourcers — API-based (reliable)
    "intellias":    scrape_intellias,    # Lever API
    "eleks":        scrape_eleks,        # Lever API
    "nix":          scrape_nix,          # Greenhouse API
    "playtika":     scrape_playtika,     # Greenhouse API
    # UA outsourcers — Playwright (JS-rendered)
    "epam":         scrape_epam,
    "globallogic":  scrape_globallogic,
    "luxoft":       scrape_luxoft,
    "softserve":    scrape_softserve,
    "ciklum":       scrape_ciklum,
    "dataart":      scrape_dataart,
    "sigma":        scrape_sigma,
    "grammarly":    scrape_grammarly,
    "wix":          scrape_wix,
    "lohika":       scrape_lohika,       # returns [] — no public API
    # UA job boards
    "dou":          scrape_dou,          # RSS search feeds
    "djinni":       scrape_djinni,       # RSS category feeds
    "telegram":     scrape_telegram,     # 4 Telegram channels
    # International
    "weworkremotely": scrape_weworkremotely,  # RSS
    "remoteco":     scrape_remoteco,     # HTML via proxy
    "relocate":     scrape_relocate,     # HTML via proxy
    "otta":         scrape_otta,         # returns [] — API broken
}


def run():
    started_at = datetime.now(timezone.utc)
    print(f"=== Job Search Agent starting at {started_at.strftime('%Y-%m-%d %H:%M UTC')} ===")

    all_jobs = []
    source_counts = defaultdict(int)

    for source in SOURCES:
        scraper = SCRAPERS.get(source)
        if not scraper:
            continue
        print(f"[Scraper] {source}...")
        try:
            jobs = scraper()
            print(f"  -> {len(jobs)} jobs found")
            all_jobs.extend(jobs)
            for job in jobs:
                source_counts[job.source] += 1
        except Exception as e:
            print(f"  -> Error: {e}")

    print(f"\nTotal scraped: {sum(source_counts.values())}")

    new_jobs = filter_new(all_jobs)
    print(f"New (unseen): {len(new_jobs)}")

    new_counts = defaultdict(int)
    sent = 0
    for job in new_jobs:
        mark_seen(job)
        new_counts[job.source] += 1
        success = send_job(job)
        if success:
            sent += 1

    send_summary(dict(source_counts), dict(new_counts), len(new_jobs), sent, started_at)
    print(f"\nDone. Sent {sent} notifications.")


if __name__ == "__main__":
    run()
