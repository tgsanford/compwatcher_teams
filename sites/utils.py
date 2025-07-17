from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
import os
import logging
load_dotenv()


def is_online_banking_related(title, summary):
    if os.getenv("DISABLE_KEYWORD_FILTER", "false").lower() == "true":
        return True

    keywords = [
        "online banking", "mobile banking", "digital banking",
        "mobile app", "internet banking", "electronic banking",
        "digital wallet", "banking security", "mobile fraud",
        "authentication", "biometric", "accessibility", "login",
        "user interface", "UX", "cybersecurity", "account takeover",
        "identity theft", "mobile deposit", "remote deposit",
        "account access", "bill pay", "card controls",
        "financial technology", "FinTech", "Zelle", "peer-to-peer payments,account opening, online privacy"
    ]
    content = f"{title.lower()} {summary.lower()}"
    return any(keyword in content for keyword in keywords)


def is_recent(entry, days=7):
    try:
        published = parsedate_to_datetime(entry.published).astimezone(timezone.utc)
        return published >= (datetime.now(timezone.utc) - timedelta(days=days))
    except Exception as e:
        logging.warning(f"Could not parse date for entry: {getattr(entry, 'title', 'unknown')} — {e}")
        return False
