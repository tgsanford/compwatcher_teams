import os
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from openai import OpenAI
from summarizer_intel import summarize_article, is_article_relevant
from teams.teams_messenger import send_to_teams
from confluence.confluence_uploader import update_page_content, format_articles_as_html
from sites import google_news, rss_reader
# from sites import youtube
# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Logging setup
os.makedirs("logs", exist_ok=True)
log_file = f"logs/intelwatcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(filename=log_file, filemode='a', level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')


def load_enabled_competitors():
    try:
        with open("competitor_config.json") as f:
            config = json.load(f)
            return [name for name, enabled in config.items() if enabled]
    except Exception as e:
        logging.error(f"❌ Failed to load competitor_config.json: {e}")
        return []


def normalize(text):
    return " ".join(text.lower().strip().split())


def run():
    start_time = time.time()
    logging.info("🚀 Starting Competitive Intel fetch via Google News, RSS, and YouTube...")

    competitors = load_enabled_competitors()
    all_articles = []

    for topic in competitors:
        try:
            articles = google_news.fetch_google_news(topic, days=7)
            for article in articles:
                article["competitor"] = topic
                article["tags"] = [topic]
            all_articles.extend(articles)
        except Exception as e:
            logging.error(f"❌ Error fetching Google News for {topic}: {e}")

    try:
        with open("rss_sources.json") as f:
            rss_sources = json.load(f)

        for comp in competitors:
            for name, meta in rss_sources.items():
                feed_url = meta["url"] if isinstance(meta, dict) else meta
                enabled = meta.get("enabled", True) if isinstance(meta, dict) else True
                if not enabled:
                    continue

                rss_articles = rss_reader.fetch_rss_feed(name, feed_url)
                for article in rss_articles:
                    if comp.lower() in article["title"].lower() or comp.lower() in article["content"].lower():
                        article["competitor"] = comp
                        article["tags"] = [comp]
                        all_articles.append(article)
    except Exception as e:
        logging.error(f"❌ Failed to load RSS sources: {e}")

    # for topic in competitors:
    """
        #try:
            #yt_articles = youtube.fetch_youtube_videos(topic, days=3)
            #for article in yt_articles:
               # article["competitor"] = topic
               # article["tags"] = [topic]
           # all_articles.extend(yt_articles)
        #except Exception as e:
           # logging.error(f"❌ Error fetching YouTube videos for {topic}: {e}")

    #logging.info(f"📥 Fetched {len(all_articles)} raw articles from Google News, RSS, and YouTube")
    """
    # Basic deduplication (hash + fuzzy)
    deduped = []
    seen_hashes = set()
    fuzzy_keys = []
    threshold = int(os.getenv("FUZZY_MATCH_THRESHOLD", 80))

    for article in all_articles:
        title = normalize(article.get("title", ""))
        content = normalize(article.get("content", ""))
        published = article.get("published_at", "")[:10]
        source = normalize(article.get("source", ""))

        key_hash = f"{title}|{source}|{published}"
        fuzzy_key = f"{title} {content}"

        if key_hash in seen_hashes:
            logging.debug(f"🔁 Skipped (hash match): {title}")
            continue
        if any(fuzz.token_set_ratio(fuzzy_key, existing) >= threshold for existing in fuzzy_keys):
            logging.debug(f"🔁 Skipped (fuzzy match): {title}")
            continue

        deduped.append(article)
        seen_hashes.add(key_hash)
        fuzzy_keys.append(fuzzy_key)

    logging.info(f"🧹 Deduplication reduced {len(all_articles)} to {len(deduped)} articles")

    # 🔍 GPT-based semantic deduplication
    gpt_prompt = """
    You are an AI assistant helping a competitive intelligence analyst filter redundant articles. Given a list of article titles and summaries, identify pairs that describe the same news event.

    Compare the meanings, not just the words. Return a list of index pairs like [(0,1), (2,5)] where the second is a duplicate of the first.

    Data:
    {data}

    Respond with only a Python list of tuples.
    """

    try:
        gpt_items = [f"{i}. Title: {a['title']} | Insight: {a.get('action', '')}" for i, a in enumerate(deduped)]
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": gpt_prompt.format(data="\n".join(gpt_items))}],
            temperature=0.3
        )
        gpt_output = response.choices[0].message.content.strip()
        logging.debug(f"🤖 GPT dedupe suggestion: {gpt_output}")

        to_remove = set()
        exec(f"pairs = {gpt_output}", {}, locals())
        for p in locals().get("pairs", []):
            if isinstance(p, (list, tuple)) and len(p) == 2:
                to_remove.add(p[1])

        deduped = [a for i, a in enumerate(deduped) if i not in to_remove]
        logging.info(f"🤖 GPT reduced final article count to {len(deduped)}")
    except Exception as e:
        logging.warning(f"⚠️ GPT deduplication skipped due to error: {e}")

    filtered_articles = [a for a in deduped if is_article_relevant(a)]
    logging.info(f"✅ {len(filtered_articles)} articles passed relevance filtering")

    for article in filtered_articles:
        try:
            result = summarize_article(article)
            article["summary"] = result.get("summary", article["title"])
            article["action"] = result.get("action", "No action provided.")
            ai_tags = result.get("tags", [])
            article["tags"] = list(set([article.get("competitor", article.get("source", "Unknown"))] + ai_tags))
            article["title"] = f"[{article['title']}]({article['link']})"
        except Exception as e:
            logging.error(f"❌ Failed to summarize article: {article['title']} — {e}")

    chunk_size = 12
    total_batches = (len(filtered_articles) + chunk_size - 1) // chunk_size

    for i in range(0, len(filtered_articles), chunk_size):
        chunk = filtered_articles[i:i + chunk_size]
        batch_number = i // chunk_size + 1
        logging.info(f"📤 Sending batch {batch_number} of {total_batches} to Teams ({len(chunk)} articles)")
        send_to_teams(chunk, batch_number=batch_number, total_batches=total_batches)

    try:
        html_block = format_articles_as_html(filtered_articles)
        update_page_content(html_block)
        logging.info("✅ Articles uploaded to Confluence.")
    except Exception as e:
        logging.error(f"❌ Failed to post to Confluence: {e}")

    elapsed = round(time.time() - start_time, 2)
    logging.info(f"✅ Script completed in {elapsed} seconds.")


if __name__ == "__main__":
    run()
