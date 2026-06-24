"""Main orchestrator — scrape → filter new → score → notify."""
from collections import defaultdict
from config import MIN_SCORE, SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.companies import (
    scrape_epam, scrape_globallogic, scrape_intellias,
    scrape_eleks, scrape_ciklum, scrape_nix,
    scrape_softserve, scrape_luxoft, scrape_sigma, scrape_dataart,
    scrape_lohika, scrape_playtika, scrape_wix, scrape_grammarly,
)
from scrapers.boards import (
    scrape_weworkremotely, scrape_remoteco, scrape_otta, scrape_relocate,
)
from tracker import filter_new, mark_seen
from matcher import score_jobs
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
    "relocate": scrape_relocate,
    # International remote boards
    "weworkremotely": scrape_weworkremotely,
    "remoteco": scrape_remoteco,
    "otta": scrape_otta,
}


def run():
    print("=== Job Search Agent starting ===")

    all_jobs = []
    source_counts: dict[str, int] = defaultdict(int)

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

    print("\nScoring jobs with Claude...")
    scored = score_jobs(new_jobs)

    sent = 0
    for job, score, reason in scored:
        mark_seen(job, score)
        if score >= MIN_SCORE:
            success = send_job(job, score, reason)
            if success:
                sent += 1

    send_summary(dict(source_counts), len(new_jobs), sent)
    print(f"\nDone. Sent {sent} notifications.")


if __name__ == "__main__":
    run()
