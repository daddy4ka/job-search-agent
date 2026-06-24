"""Main orchestrator — scrape → filter new → score → notify."""
from collections import defaultdict
from config import MIN_SCORE, SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.telegram import scrape as scrape_telegram
from scrapers.companies import (
    scrape_epam, scrape_globallogic, scrape_intellias,
    scrape_eleks, scrape_ciklum, scrape_nix,
    scrape_softserve, scrape_luxoft, scrape_sigma, scrape_dataart,
    scrape_lohika, scrape_playtika, scrape_wix, scrape_grammarly,
)
from scrapers.boards import scrape_otta
from scrapers.playwright_scraper import (
    scrape_weworkremotely, scrape_remoteco, scrape_relocate,
    scrape_softserve as scrape_softserve_pw,
    scrape_ciklum as scrape_ciklum_pw,
    scrape_epam as scrape_epam_pw,
    scrape_globallogic as scrape_globallogic_pw,
    scrape_luxoft as scrape_luxoft_pw,
    scrape_dataart as scrape_dataart_pw,
    scrape_sigma as scrape_sigma_pw,
    scrape_grammarly as scrape_grammarly_pw,
    scrape_wix as scrape_wix_pw,
    scrape_playtika as scrape_playtika_pw,
)
from tracker import filter_new, mark_seen
from matcher import score_jobs
from notifier import send_job, send_summary


SCRAPERS = {
    # UA outsourcers
    "epam": scrape_epam_pw,
    "globallogic": scrape_globallogic_pw,
    "intellias": scrape_intellias,
    "eleks": scrape_eleks,
    "ciklum": scrape_ciklum_pw,
    "nix": scrape_nix,
    "softserve": scrape_softserve_pw,
    "luxoft": scrape_luxoft_pw,
    "sigma": scrape_sigma_pw,
    "dataart": scrape_dataart_pw,
    "lohika": scrape_lohika,
    "playtika": scrape_playtika_pw,
    "wix": scrape_wix_pw,
    "grammarly": scrape_grammarly_pw,
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
    print("=== Job Search Agent starting ===")

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

    if not new_jobs:
        send_summary(dict(source_counts), 0, 0)
        return

    sent = 0
    for job in new_jobs:
        mark_seen(job)
        success = send_job(job)
        if success:
            sent += 1

    send_summary(dict(source_counts), len(new_jobs), sent)
    print(f"\nDone. Sent {sent} notifications.")


if __name__ == "__main__":
    run()
