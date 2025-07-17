import feedparser
from datetime import datetime, timedelta
import logging


def fetch_rss_feed(source_name, feed_url, days=7):
    logging.info(f"🔍 Fetching RSS feed: {source_name}")
    entries = []
    one_week_ago = datetime.now() - timedelta(days=days)

    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            try:
                published = datetime(*entry.published_parsed[:6])
            except Exception:
                continue

            if published < one_week_ago:
                continue

            entries.append({
                "title": entry.title,
                "content": entry.get("summary", ""),
                "link": entry.link,
                "source": source_name,
                "tags": [source_name]
            })
    except Exception as e:
        logging.error(f"❌ Failed to fetch RSS from {source_name}: {e}")

    return entries
