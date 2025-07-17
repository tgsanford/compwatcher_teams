import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL")
SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")
PAGE_ID = os.getenv("CONFLUENCE_PAGE_ID")
EMAIL = os.getenv("CONFLUENCE_EMAIL")
API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

auth = (EMAIL, API_TOKEN)
headers = {"Content-Type": "application/json"}


def get_page_content():
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{PAGE_ID}?expand=body.storage,version"
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json()


def update_page_content(new_html_block):
    page = get_page_content()
    current_body = page['body']['storage']['value']
    version_number = page['version']['number'] + 1

    # Generate new section title
    today = datetime.now().strftime("%B %d, %Y")
    section_title = f"<h2>Weekly CompWatch Update – {today}</h2>"

    # New content block to prepend
    new_body = section_title + new_html_block + current_body

    update_payload = {
        "id": PAGE_ID,
        "type": "page",
        "title": page['title'],
        "space": {"key": SPACE_KEY},
        "body": {
            "storage": {
                "value": new_body,
                "representation": "storage"
            }
        },
        "version": {"number": version_number}
    }

    update_url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{PAGE_ID}"
    response = requests.put(update_url, json=update_payload, auth=auth, headers=headers)

    if response.status_code == 200:
        print("✅ Confluence page updated successfully.")
    else:
        print(f"❌ Failed to update page: {response.status_code}", response.text)


def format_articles_as_html(articles):
    html = ""
    grouped = {}
    for article in articles:
        group = article.get("competitor") or article.get("source") or "Other"
        grouped.setdefault(group, []).append(article)

    for group, items in grouped.items():
        html += f"<h3>{group}</h3><ul>"
        for article in items:
            summary = article.get("summary", article.get("title"))
            action = article.get("action", "No insight provided.")
            tags = ", ".join(article.get("tags", []))
            pub_date = article.get("published_at", "")[:10]
            html += f"<li><p><strong><a href='{article['link']}'>{summary}</a></strong><br/>"
            html += f"<em>Published:</em> {pub_date}<br/>"
            html += f"<em>Insight:</em> {action}<br/><em>Tags:</em> {tags}</p></li>"
        html += "</ul>"
    return html
