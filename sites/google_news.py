import feedparser
from datetime import datetime, timedelta
import logging


def fetch_google_news(topic: str, days: int = 3):
    import feedparser
    from datetime import datetime, timedelta

    base_url = "https://news.google.com/rss/search?q="
    query = topic.replace(" ", "+")
    feed_url = f"{base_url}{query}"
    logging.info(f"🔍 Fetching Google News for: {topic}")

    entries = []
    cutoff_date = datetime.now() - timedelta(days=days)
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        try:
            published = datetime(*entry.published_parsed[:6])
        except Exception:
            published = None

        if published and published < cutoff_date:
            continue

        title = entry.title.strip()
        link = entry.link.strip()
        summary = entry.summary.strip()

        # Normalize for comparison
        lower_summary = summary.lower()
        lower_title = title.lower()

        # 🛑 Skip noisy or generic aggregator entries
        if (
            "comprehensive up-to-date news coverage" in lower_summary
            or lower_title in ("google news", "news", "headlines")
            or "news.google.com" in link and "articles" not in link
        ):
            logging.debug(f"⛔ Skipped generic Google News entry: {title}")
            continue

        entries.append({
            "title": title,
            "content": summary,
            "link": link,
            "source": f"Google News - {topic}",
            "published_at": published.isoformat() if published else None
        })

    logging.info(f"📦 Google News ({topic}): Returning {len(entries)} articles")
    return entries
