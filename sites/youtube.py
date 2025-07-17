import os
import requests
import logging
from datetime import datetime, timedelta

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Add this to your .env


def fetch_youtube_videos(query: str, days: int = 7, max_results: int = 10):
    if not YOUTUBE_API_KEY:
        logging.warning("❌ YouTube API key is missing.")
        return []

    published_after = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": max_results,
        "order": "date",
        "publishedAfter": published_after
    }

    logging.info(f"🔍 Searching YouTube for: {query}")
    try:
        response = requests.get(YOUTUBE_SEARCH_URL, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception as e:
        logging.error(f"❌ Failed to fetch YouTube results: {e}")
        return []

    results = []
    for item in items:
        snippet = item.get("snippet", {})
        video_id = item["id"].get("videoId")
        if not video_id:
            continue

        results.append({
            "title": snippet.get("title"),
            "content": snippet.get("description", ""),
            "link": f"https://www.youtube.com/watch?v={video_id}",
            "source": "YouTube",
            "published_at": snippet.get("publishedAt")
        })

    logging.info(f"📦 YouTube ({query}): Returning {len(results)} videos")
    return results
