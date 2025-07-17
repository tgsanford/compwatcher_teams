from flask import Flask, request, jsonify
import json
import logging
import csv
from datetime import datetime, timedelta
import os
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

# Set up logging
os.makedirs("../logs", exist_ok=True)
log_filename = f"logs/ack_log_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filemode='a'
)

app = Flask(__name__)


def format_date_header():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    return f":mag: Weekly Competitor Intel — Week of {start_of_week.strftime('%B %d, %Y')}"


def has_user_responded(blocks, user, block_id):
    for i, block in enumerate(blocks):
        if block.get("type") == "context" and block.get("block_id", "").startswith("feedback_"):
            if any(user in el.get("text", "") for el in block.get("elements", [])):
                prev_block_id = blocks[i - 1].get("block_id") if i > 0 else ""
                if prev_block_id == block_id:
                    return True
    return False


@app.route("/slack/interactions", methods=["POST"])
def slack_interaction():
    payload = request.form.get("payload")
    if not payload:
        return "Missing payload", 400

    try:
        data = json.loads(payload)
        user = data.get("user", {}).get("username", "unknown")
        action = data.get("actions", [{}])[0]
        timestamp = datetime.now().isoformat()

        raw_value = action.get("value", "")
        article_title, feedback = raw_value.split(":::", 1) if ":::" in raw_value else (raw_value, "Unknown")

        channel = data.get("channel", {}).get("id")
        message_ts = data.get("message", {}).get("ts")
        block_id = action.get("block_id")

        if channel and message_ts and block_id:
            original = client.conversations_history(
                channel=channel,
                latest=message_ts,
                inclusive=True,
                limit=1
            )

            messages = original.get("messages", [])
            if not messages:
                raise Exception("No message found to update.")

            blocks = messages[0].get("blocks", [])
            updated_blocks = []
            feedback_block_id = f"feedback_{timestamp}"
            feedback_line = f":ballot_box_with_ballot: *Feedback received from `{user}`:* {feedback}"
            skip_next = False

            for i, block in enumerate(blocks):
                if skip_next:
                    skip_next = False
                    continue

                updated_blocks.append(block)

                if block.get("block_id") == block_id:
                    if has_user_responded(blocks, user, block_id):
                        continue

                    # Insert feedback block
                    updated_blocks.append({
                        "type": "context",
                        "block_id": feedback_block_id,
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": feedback_line
                            }
                        ]
                    })

                    # Disable buttons
                    if i + 1 < len(blocks) and blocks[i + 1].get("type") == "actions":
                        new_actions = []
                        for btn in blocks[i + 1].get("elements", []):
                            btn_copy = json.loads(json.dumps(btn))  # deep copy
                            btn_copy["text"]["text"] += " ✓"
                            btn_copy["style"] = "danger" if "👎" in btn_copy["text"]["text"] else "primary"
                            btn_copy["confirm"] = {
                                "title": {"type": "plain_text", "text": "Feedback already received"},
                                "text": {"type": "mrkdwn", "text": "You've already submitted feedback."},
                                "confirm": {"type": "plain_text", "text": "OK"},
                                "deny": {"type": "plain_text", "text": ""}
                            }
                            new_actions.append(btn_copy)
                        updated_blocks.append({
                            "type": "actions",
                            "block_id": blocks[i + 1].get("block_id"),
                            "elements": new_actions
                        })
                        skip_next = True

            # Always update the date header
            if updated_blocks and updated_blocks[0].get("type") == "header":
                updated_blocks[0]["text"]["text"] = format_date_header()

            fallback_text = f"{article_title} — Feedback received from {user}"

            client.chat_update(
                channel=channel,
                ts=message_ts,
                blocks=updated_blocks,
                text=fallback_text
            )

            # Save feedback to CSV
            with open("../logs/acknowledgments.csv", "a", newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, user, article_title, feedback])

        return jsonify({
            "response_type": "ephemeral",
            "text": f"✅ Thanks for your CompWatcher feedback, {user}! Logged: *{feedback}*"
        })

    except Exception:
        logging.exception("❌ Error during interaction")  # Automatically logs the full traceback
        return jsonify({"text": "⚠️ Internal server error."}), 500


if __name__ == "__main__":
    app.run(port=5050, debug=True)
