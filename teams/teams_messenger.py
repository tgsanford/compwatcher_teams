import os
import json
import logging
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

MAX_TEXT_LENGTH = 2900

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
LAST_POST_FILE = os.path.join(LOGS_DIR, "last_post_teams.json")
os.makedirs(LOGS_DIR, exist_ok=True)


def truncate(text, limit=MAX_TEXT_LENGTH):
    if not text:
        return "No content available."
    return text if len(text) <= limit else text[:limit - 3] + "..."


def format_date_header(batch_number=None, total_batches=None):
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    header = f"📣 Weekly Competition Updates — Week of {start_of_week.strftime('%B %d, %Y')}"
    if batch_number and total_batches:
        header += f" (Part {batch_number} of {total_batches})"
    return header


def build_teams_message(articles, batch_number=None, total_batches=None):
    """
    Build a Teams Adaptive Card payload from articles.
    Returns a payload dict ready to POST to a Power Automate webhook.
    """
    header_text = format_date_header(batch_number, total_batches)

    tag_emojis = {
        "Consumer Banking": "🏦",
        "Business Banking": "💼",
        "Mobile Banking": "📱",
        "Fraud & Security": "🔐",
        "New Account Opening": "🆕",
        "Compliance & Reporting": "📋",
        "Payments & Cards": "💳",
        "AI & Data Use": "🤖"
    }

    body = [
        {
            "type": "TextBlock",
            "text": header_text,
            "size": "Large",
            "weight": "Bolder",
            "wrap": True,
            "color": "Accent"
        }
    ]

    if not articles:
        body.append({
            "type": "TextBlock",
            "text": "No relevant updates this week.",
            "wrap": True,
            "isSubtle": True
        })
    else:
        grouped = defaultdict(list)
        for article in articles:
            grouped[article.get("agency") or article.get("competitor") or "Other"].append(article)

        for agency, items in grouped.items():
            # Competitor/agency header
            body.append({
                "type": "TextBlock",
                "text": agency,
                "size": "Medium",
                "weight": "Bolder",
                "wrap": True,
                "separator": True,
                "spacing": "Medium"
            })

            for article in items:
                summary = article.get("summary", article.get("title", "Untitled Article"))
                action = article.get("action", "No action provided.")
                article_link = article.get("link", "#")

                tag_list = article.get("tags", [])
                tags_display = "  ".join([f"{tag_emojis.get(t, '')} {t}" for t in tag_list]) if tag_list else "—"

                published_at = article.get("published_at")
                try:
                    formatted_date = datetime.fromisoformat(published_at).strftime("%b %d, %Y")
                except Exception:
                    formatted_date = "Unknown date"

                # Article summary
                body.append({
                    "type": "TextBlock",
                    "text": truncate(summary, 200),
                    "wrap": True,
                    "spacing": "Small"
                })

                # Article metadata
                body.append({
                    "type": "FactSet",
                    "spacing": "Small",
                    "facts": [
                        {"title": "Published:", "value": formatted_date},
                        {"title": "Insight:", "value": truncate(action, 300)},
                        {"title": "Tags:", "value": tags_display}
                    ]
                })

                # Read more button
                body.append({
                    "type": "ActionSet",
                    "spacing": "Small",
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "Read Article",
                            "url": article_link
                        }
                    ]
                })

    adaptive_card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "msteams": {
            "width": "Full"
        },
        "body": body
    }

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": adaptive_card
            }
        ]
    }


def send_to_teams(articles, batch_number=None, total_batches=None):
    """
    Send articles to MS Teams channel via Power Automate webhook.
    """
    if not TEAMS_WEBHOOK_URL:
        logging.error("❌ TEAMS_WEBHOOK_URL not configured in .env file")
        return

    try:
        payload = build_teams_message(articles, batch_number=batch_number, total_batches=total_batches)

        logging.debug("📦 Teams Adaptive Card preview:")
        logging.debug(json.dumps(payload, indent=2))

        response = requests.post(
            TEAMS_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 202:
            logging.info("✅ Teams message sent successfully.")
        else:
            logging.error(f"❌ Teams webhook returned {response.status_code}: {response.text}")
            return

        # Track send history
        new_entry = {
            "webhook_url": TEAMS_WEBHOOK_URL[:50] + "...",
            "timestamp": datetime.now().isoformat(),
            "batch_number": batch_number,
            "total_batches": total_batches,
            "article_count": len(articles)
        }

        history = []
        if os.path.exists(LAST_POST_FILE):
            try:
                with open(LAST_POST_FILE, "r") as f:
                    history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except Exception:
                history = []

        history.insert(0, new_entry)
        history = history[:10]

        with open(LAST_POST_FILE, "w") as f:
            json.dump(history, f, indent=2)

    except Exception as e:
        logging.error(f"❌ Error sending to Teams: {e}")
        logging.exception("Full traceback:")
