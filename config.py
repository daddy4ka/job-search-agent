PROFILE = """
Name: Vitalii Skakovets
Target roles: Head of Data, Head of Analytics, BI Lead, Business Intelligence Lead,
              Head of R&D (analytics), Data Analytics Lead, Analytics Manager,
              Head of Data Management, Chief Data Officer, Director of Analytics

Experience: 14+ years in BI, data analytics, data engineering
Current: Head of Data @ Vogue UA

Key skills: BI architecture, data warehouse design, ETL pipelines, KPI frameworks,
            executive dashboards, team leadership, data governance, revenue modeling,
            predictive analytics, AI agents integration

Tech stack: Python, SQL, BigQuery, Power BI, Tableau, Looker Studio, Metabase,
            dbt, Airflow, GCP, AWS, MongoDB, GA4, ML/NLP, LLM Integration

Industries: media & publishing, FinTech, digital subscriptions, advertising, digital products

Seniority: Senior / Lead / Head level only. Not interested in analyst/junior/mid roles.

Location preference: Ukraine (remote or Kyiv), EU remote, global remote
"""

# Minimum relevance score (0-10) to send notification
MIN_SCORE = 6

TELEGRAM_BOT_TOKEN = "8734395128:AAFxeNXXTaEb9FACNm3928XRvyh9-9B_RUU"
TELEGRAM_CHAT_ID = "235956039"

ANTHROPIC_API_KEY = ""  # Set via GitHub Actions secret ANTHROPIC_API_KEY

SOURCES = [
    # UA outsourcers
    "intellias",
    "eleks",
    "nix",
    "epam",
    "globallogic",
    "softserve",
    "luxoft",
    "sigma",
    "dataart",
    "playtika",
    "wix",
    "grammarly",
    # UA job boards
    "dou",
    "djinni",
    "telegram",
    "relocate",
    # International remote boards
    "weworkremotely",
    "remoteco",
    "otta",
]
