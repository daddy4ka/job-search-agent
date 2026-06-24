"""Main orchestrator — scrape → filter new → notify."""
from collections import defaultdict
from datetime import datetime, timezone
from config import SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.telegram import scrape as scrape_telegram
from scrapers.companies import (
    scrape_intellias, scrape_eleks, scrape_nix, scrape_lohika,
)
from scrapers.boards import scrape_otta
from scrapers.playwright_scraper import (
    scrape_weworkremotely, scrape_remoteco, scrape_relocate,
    scrape_softserve, scrape_ciklum, scrape_epam,
    scrape_globallogic, scrape_luxoft, scrape_dataart,
    scrape_sigma, scrape_grammarly, scrape_wix, scrape_playtika,
)
from tracker import filter_new, mark_seen
from notifier import send_job, send_summary


SCRAPERS = {
    # UA outsourcers
    "epam": scrape_epam,
    "globallogic": scrape_globallogic,
    "intellias": scrape_intellias,
    "eleks": scrape_eleks,
    "ciklum": scrape_ciklum,
    "nix": scrape_nix,
    "softserve": scrape_softserve,
    "luxoft": scrape_luxoft,
    "sigma": scrape_sigma,
    "dataart": scrape_dataart,
    "lohika": scrape_lohika,
    "playtika": scrape_playtika,
    "wix": scrape_wix,
    "grammarly": scrape_grammarly,
    # UA job boards
    "dou": scrape_dou,
    "djinni": scrape_djinni,
    "telegram": scrape_telegram,
    "relocate": scrape_relocate,
    # International remote boards
    "weworkremotely": scrape_weworkremotely,
    "remoteco": scrape_remoteco,
    "otta": scrape_otta,
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
            print(f"  → {len(jobs)} jobs found")
            all_jobs.extend(jobs)
            for job in jobs:
                source_counts[job.source] += 1
        except Exception as e:
            print(f"  → Error: {e}")

    print(f"\nTotal scraped: {sum(source_counts.values())}")

    new_jobs = filter_new(all_jobs)
    print(f"New (unseen): {len(new_jobs)}")

    sent = 0
    for job in new_jobs:
        mark_seen(job)
        success = send_job(job)
        if success:
            sent += 1

    send_summary(dict(source_counts), len(new_jobs), sent, started_at)
    print(f"\nDone. Sent {sent} notifications.")


if __name__ == "__main__":
    run()
