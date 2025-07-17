import os
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

channel = os.getenv("SLACK_CHANNEL", "#compwatcher-product")
if ENVIRONMENT.lower() == "sandbox":
    channel = "#compwatcher-product"

MAX_TEXT_LENGTH = 2900

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
LAST_POST_FILE = os.path.join(LOGS_DIR, "last_post.json")
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


def build_slack_blocks(articles, batch_number=None, total_batches=None):
    if not articles:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No relevant updates this week."}
        }]

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

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": format_date_header(batch_number, total_batches)
            }
        },
        {"type": "divider"}
    ]

    grouped = defaultdict(list)
    for article in articles:
        grouped[article.get("agency") or article.get("competitor") or "Other"].append(article)

    for agency, items in grouped.items():
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{agency}*"}
        })

        for idx, article in enumerate(items):
            title = article.get("title", "Untitled Article")
            summary = article.get("summary", title)
            action = article.get("action", "No action provided.")
            article_link = article.get("link", "#")

            tag_list = article.get("tags", [])
            emoji_tags = " ".join([f"{tag_emojis.get(tag, '')} {tag}" for tag in tag_list])
            tags_line = f"*Tags:* {emoji_tags}" if tag_list else ""

            published_at = article.get("published_at")
            try:
                dt = datetime.fromisoformat(published_at)
                formatted_date = dt.strftime("%b %d, %Y")
            except Exception:
                formatted_date = "Unknown date"

            body = (
                f"• <{article_link}|{truncate(summary)}>\n"
                f"_Published:_ {formatted_date}\n"
                f"_Insight:_ {truncate(action)}\n"
                f"{tags_line}"
            )

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": truncate(body)
                }
            })

#            blocks.append({
#                "type": "actions",
#                "elements": [
#                    {
#                        "type": "button",
#                        "text": {"type": "plain_text", "text": "👍 Useful"},
#                        "style": "primary",
#                        "value": f"{title}:::👍 Useful",
#                        "action_id": f"useful_{idx}"
#                    },
#                   {
#                        "type": "button",
#                        "text": {"type": "plain_text", "text": "👎 Not Useful"},
#                        "style": "danger",
#                        "value": f"{title}:::👎 Not Useful",
#                        "action_id": f"not_useful_{idx}"
#                    }
#                ]
#            })

        blocks.append({"type": "divider"})

    return blocks[:50]


def send_to_slack_block_message(articles, batch_number=None, total_batches=None):
    blocks = build_slack_blocks(articles, batch_number=batch_number, total_batches=total_batches)

    try:
        logging.debug("📦 Slack blocks preview:")
        logging.debug(json.dumps(blocks, indent=2))

        response = client.chat_postMessage(
            channel=channel,
            text="Weekly Competition Updates",
            blocks=blocks
        )

        logging.info("✅ Slack message sent successfully.")
        logging.debug(f"🔁 Slack API response: {response}")

        ts = response.get("ts")
        ch = response.get("channel")
        if ts and ch:
            new_entry = {"channel": ch, "ts": ts, "timestamp": datetime.now().isoformat()}
            if os.path.exists(LAST_POST_FILE):
                try:
                    with open(LAST_POST_FILE, "r") as f:
                        history = json.load(f)
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            else:
                history = []
            history.insert(0, new_entry)
            with open(LAST_POST_FILE, "w") as f:
                json.dump(history, f, indent=2)

    except SlackApiError as e:
        logging.error(f"❌ Slack API error: {e.response['error']}")
    except Exception as e:
        logging.error(f"❌ Unexpected error sending to Slack: {e}")
