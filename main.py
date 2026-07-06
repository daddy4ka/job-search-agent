"""Main orchestrator — scrape all sources, filter new, notify."""
from collections import defaultdict
from datetime import datetime, timezone
from config import SOURCES
from scrapers.dou import scrape as scrape_dou
from scrapers.djinni import scrape as scrape_djinni
from scrapers.companies import (
    scrape_intellias, scrape_eleks, scrape_nix, scrape_epam, scrape_globallogic,
    scrape_playtika, scrape_softserve, scrape_luxoft, scrape_sigma, scrape_dataart, scrape_wix,
    scrape_ciklum, scrape_superhuman, scrape_skelar, scrape_squad, scrape_gr8tech,
    scrape_ajax, scrape_dxc, scrape_zone3000, scrape_nixsolutions, scrape_tieto, scrape_fractal, scrape_novadigital,
    scrape_temabit,
    scrape_evoplay, scrape_headway, scrape_griddynamics, scrape_avenga, scrape_betterme,
    scrape_obrio, scrape_allstarsit, scrape_autodoc, scrape_whitebit, scrape_ideals,
    scrape_genesis, scrape_uklon, scrape_macpaw, scrape_readdle, scrape_upstars, scrape_dripify,
)
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
    "superhuman":     scrape_superhuman,
    "skelar":         scrape_skelar,
    "squad":          scrape_squad,
    "gr8tech":        scrape_gr8tech,
    "ajax":           scrape_ajax,
    "dxc":            scrape_dxc,
    "zone3000":       scrape_zone3000,
    "nixsolutions":   scrape_nixsolutions,
    "tieto":          scrape_tieto,
    "fractal":        scrape_fractal,
    "novadigital":    scrape_novadigital,
    "temabit":        scrape_temabit,
    "evoplay":        scrape_evoplay,
    "headway":        scrape_headway,
    "griddynamics":   scrape_griddynamics,
    "avenga":         scrape_avenga,
    "betterme":       scrape_betterme,
    "obrio":          scrape_obrio,
    "allstarsit":     scrape_allstarsit,
    "autodoc":        scrape_autodoc,
    "whitebit":       scrape_whitebit,
    "ideals":         scrape_ideals,
    "genesis":        scrape_genesis,
    "uklon":          scrape_uklon,
    "macpaw":         scrape_macpaw,
    "readdle":        scrape_readdle,
    "upstars":        scrape_upstars,
    "dripify":        scrape_dripify,
    # UA job boards
    "dou":            scrape_dou,
    "djinni":         scrape_djinni,
}


def run():
    started_at = datetime.now(timezone.utc)
    print(f"=== Job Search Agent starting at {started_at.strftime('%Y-%m-%d %H:%M UTC')} ===")

    all_jobs = []
    source_raw_counts = defaultdict(int)
    source_counts = defaultdict(int)
    job_source_to_key = {}

    for source in SOURCES:
        scraper = SCRAPERS.get(source)
        if not scraper:
            continue
        print(f"[Scraper] {source}...")
        try:
            jobs, raw_total = scraper()
            print(f"  -> {raw_total} total, {len(jobs)} matched")
            all_jobs.extend(jobs)
            source_raw_counts[source] = raw_total
            source_counts[source] = len(jobs)
            for job in jobs:
                job_source_to_key[job.source] = source
        except Exception as e:
            print(f"  -> Error: {e}")

    print(f"\nTotal scraped: {sum(source_counts.values())}")

    new_jobs = filter_new(all_jobs)
    print(f"New (unseen): {len(new_jobs)}")

    new_counts = defaultdict(int)
    for job in new_jobs:
        mark_seen(job)
        new_counts[job_source_to_key.get(job.source, job.source)] += 1
        send_job(job)

    send_summary(dict(source_raw_counts), dict(source_counts), dict(new_counts), started_at, SOURCES)
    print(f"\nDone. Sent {len(new_jobs)} notifications.")


if __name__ == "__main__":
    run()
