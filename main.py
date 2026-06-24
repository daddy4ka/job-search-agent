"""Main orchestrator — scrape all sources, filter new, notify."""
from collections import defaultdict
from datetime import datetime, timezone
from config import SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.telegram import scrape as scrape_telegram
from scrapers.companies import (
    scrape_intellias, scrape_eleks, scrape_nix, scrape_epam, scrape_globallogic,
    scrape_playtika, scrape_softserve, scrape_luxoft, scrape_sigma, scrape_dataart, scrape_wix,
    scrape_ciklum, scrape_grammarly, scrape_superhuman, scrape_skelar, scrape_squad, scrape_gr8tech,
    scrape_evoplay, scrape_headway,
)
from scrapers.boards import scrape_weworkremotely, scrape_remoteco, scrape_relocate, scrape_otta
from tracker import filter_new, mark_seen
from notifier import send_job, send_summary


SCRAPERS = {
    # UA outsourcers — API-based
    "intellias":      scrape_intellias,
    "eleks":          scrape_eleks,
    "nix":            scrape_nix,
    "epam":           scrape_epam,
    "globallogic":    scrape_globallogic,
    "playtika":       scrape_playtika,
    "softserve":      scrape_softserve,
    "luxoft":         scrape_luxoft,
    "sigma":          scrape_sigma,
    "dataart":        scrape_dataart,
    "wix":            scrape_wix,
    # UA outsourcers — Playwright
    "ciklum":         scrape_ciklum,
    "grammarly":      scrape_grammarly,
    "superhuman":     scrape_superhuman,
    "skelar":         scrape_skelar,
    "squad":          scrape_squad,
    "gr8tech":        scrape_gr8tech,
    "evoplay":        scrape_evoplay,
    "headway":        scrape_headway,
    # UA job boards
    "dou":            scrape_dou,
    "djinni":         scrape_djinni,
    "telegram":       scrape_telegram,
    # International
    "weworkremotely": scrape_weworkremotely,
    "remoteco":       scrape_remoteco,
    "relocate":       scrape_relocate,
    "otta":           scrape_otta,
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
