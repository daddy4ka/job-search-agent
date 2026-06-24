import os
import anthropic
from config import PROFILE, ANTHROPIC_API_KEY
from scrapers.dou import Job


def _get_client() -> anthropic.Anthropic:
    api_key = ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def score_job(job: Job) -> tuple[int, str]:
    """Returns (score 0-10, short reason)."""
    client = _get_client()

    prompt = f"""You are a job relevance evaluator. Score this job posting for the candidate below.

CANDIDATE PROFILE:
{PROFILE}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Source: {job.source}
Description: {job.description[:1500]}

Score from 0 to 10 how relevant this job is for this candidate.
- 9-10: Perfect match (exact title/seniority/domain)
- 7-8: Strong match (right level, relevant domain)
- 5-6: Partial match (some alignment but missing key elements)
- 0-4: Poor match (wrong level, domain, or seniority)

Respond with ONLY this format:
SCORE: <number>
REASON: <one sentence explaining the score>"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        score_line = next((l for l in text.splitlines() if l.startswith("SCORE:")), "SCORE: 0")
        reason_line = next((l for l in text.splitlines() if l.startswith("REASON:")), "REASON: N/A")
        score = int(score_line.replace("SCORE:", "").strip())
        reason = reason_line.replace("REASON:", "").strip()
        return score, reason
    except Exception as e:
        print(f"[Matcher] Error scoring job {job.id}: {e}")
        return 0, "scoring error"


def score_jobs(jobs: list[Job]) -> list[tuple[Job, int, str]]:
    results = []
    for job in jobs:
        score, reason = score_job(job)
        print(f"  [{score}/10] {job.title} @ {job.company} — {reason}")
        results.append((job, score, reason))
    return results
