"""Tracks seen job IDs in an Excel file to avoid duplicate notifications."""
import os
from pathlib import Path
import openpyxl
from scrapers.dou import Job

TRACKER_PATH = Path(__file__).parent / "seen_jobs.xlsx"
SHEET_NAME = "seen"


def _load_workbook():
    if TRACKER_PATH.exists():
        return openpyxl.load_workbook(TRACKER_PATH)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(["job_id", "title", "company", "url", "source", "score", "seen_at"])
    wb.save(TRACKER_PATH)
    return wb


def is_seen(job_id: str) -> bool:
    if not TRACKER_PATH.exists():
        return False
    wb = openpyxl.load_workbook(TRACKER_PATH)
    ws = wb[SHEET_NAME]
    seen_ids = {str(row[0].value) for row in ws.iter_rows(min_row=2) if row[0].value}
    return job_id in seen_ids


def mark_seen(job: Job, score: int) -> None:
    from datetime import datetime
    wb = _load_workbook()
    ws = wb[SHEET_NAME]
    ws.append([job.id, job.title, job.company, job.url, job.source, score,
               datetime.utcnow().strftime("%Y-%m-%d %H:%M")])
    wb.save(TRACKER_PATH)


def filter_new(jobs: list[Job]) -> list[Job]:
    if not TRACKER_PATH.exists():
        return jobs
    wb = openpyxl.load_workbook(TRACKER_PATH)
    ws = wb[SHEET_NAME]
    seen_ids = {str(row[0].value) for row in ws.iter_rows(min_row=2) if row[0].value}
    return [j for j in jobs if j.id not in seen_ids]
