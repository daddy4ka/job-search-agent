"""Main orchestrator — scrape → filter new → score → notify."""
from collections import defaultdict
from config import MIN_SCORE, SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.companies import (
    scrape_epam, scrape_globallogic, scrape_intellias,
    scrape_eleks, scrape_ciklum, scrape_nix, scrape_linkedin,
)
from tracker import filter_new, mark_seen
from matcher import score_jobs
from notifier import send_job, send_summary


SCRAPERS = {
    "dou": scrape_dou,
    "djinni": scrape_djinni,
    "epam": scrape_epam,
    "globallogic": scrape_globallogic,
    "intellias": scrape_intellias,
    "eleks": scrape_eleks,
    "ciklum": scrape_ciklum,
    "nix": scrape_nix,
    "linkedin": scrape_linkedin,
}


def run():
    print("=== Job Search Agent starting ===")

    # 1. Scrape all sources
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

    # 2. Filter already-seen jobs
    new_jobs = filter_new(all_jobs)
    print(f"New (unseen): {len(new_jobs)}")

    if not new_jobs:
        send_summary(dict(source_counts), 0, 0)
        return

    # 3. Score with Claude
    print("\nScoring jobs with Claude...")
    scored = score_jobs(new_jobs)

    # 4. Send relevant ones to Telegram and mark all as seen
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
