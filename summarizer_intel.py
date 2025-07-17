import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Load model and temperature from environment
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")
TEMPERATURE_RAW = os.getenv("OPENAI_TEMPERATURE", "0.3")

try:
    TEMPERATURE = float(TEMPERATURE_RAW)
except ValueError:
    logging.warning(f"Invalid temperature value: {TEMPERATURE_RAW}, defaulting to 1.")
    TEMPERATURE = 1

# Enforce temperature=1 for models that require it
if MODEL.lower() in ["gpt-4", "o3"]:
    if TEMPERATURE != 1:
        logging.warning(f"⚠️ Model '{MODEL}' only supports temperature=1. Forcing override.")
        TEMPERATURE = 1

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Default prompt for summarization
default_summary_prompt = """
You are a competitive intelligence analyst supporting a product and strategy team at a fintech company. 
Your goal is to surface useful insights about competitor activity across product, marketing, partnerships, and technology.  Avoid summarizing duplicate stories that repeat the same news across sources. If multiple entries are very similar, summarize only once.

Please analyze the following news article, announcement, or social media update and respond with:
1. A one-sentence summary of what happened.
2. A recommended insight or takeaway for product or strategy teams.
3. Tags that categorize the article’s themes (choose from: Product Launch, Pricing Change, Marketing Campaign, Hiring, Technology Shift, Regulatory Mention, Partnership, Competitive Threat, Other).

Title: {title}
Content: {content}

Respond using the format below:
- Summary: <your summary>
- Insight: <your strategic takeaway or implication>
- Tags: <comma-separated list of tags>
"""

# Default prompt for filtering

default_relevance_prompt = """
You are a competitive intelligence assistant helping product managers at an online banking company stay informed on competitors actions and announcements.  These articles should provide meaningful information to the Product Manager.  The product managers cover a variety of product in online banking.  They include, Consumer Banking, Business Banking, Data & AI, Account Origination and Mobile Banking.Avoid summarizing duplicate stories that repeat the same news across sources. If multiple entries are very similar, summarize only once.
  

Decide whether the following article is relevant to competitive monitoring. 
It is relevant if it includes:
- New product features or launches
- Partnerships or integrations
- Strategy shifts or leadership changes
- Marketing or brand positioning
- Pricing updates
- Technical or platform changes
- Regulatory impacts or public attention

Title: {title}

Content or Summary: {content}

If the article includes any of the above, respond with YES. Otherwise, respond with NO.  Do your best to filter out duplicate articles that may come from different sources.

Answer ONLY with one word: YES or NO.
"""


# Fallback to code-defined templates if env doesn't override
summary_template = os.getenv("GPT_SUMMARY_PROMPT_TEMPLATE", default_summary_prompt)
relevance_template = os.getenv("GPT_RELEVANCE_PROMPT_TEMPLATE", default_relevance_prompt)


def summarize_article(article):
    prompt = summary_template.format(
        title=article["title"],
        content=article["content"]
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE
    )

    result = response.choices[0].message.content.strip()

    parsed_summary = ""
    parsed_insight = ""
    parsed_tags = []

    for line in result.splitlines():
        line = line.strip()
        if line.lower().startswith("- summary:"):
            parsed_summary = line.split(":", 1)[1].strip()
        elif line.lower().startswith("- insight:"):  # 🔄 was 'action'
            parsed_insight = line.split(":", 1)[1].strip()
        elif line.lower().startswith("- tags:"):
            tag_line = line.split(":", 1)[1].strip()
            parsed_tags = [tag.strip() for tag in tag_line.split(",") if tag.strip()]

    return {
     "summary": parsed_summary or article["title"],
     "action": parsed_insight or "No insight provided.",
     "tags": parsed_tags
     }


def is_article_relevant(article):
    logging.info(f"🧠 Filtering: {article['title']}")
    prompt = relevance_template.format(
        title=article["title"],
        content=article.get("content", "")
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE
    )

    result = response.choices[0].message.content.strip().lower()
    logging.info(f"GPT answer: {result}")
    return result == "yes"
