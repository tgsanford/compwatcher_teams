
# 🕵️‍♂️ CompWatcher

**CompWatcher** is a competitive intelligence tool that monitors news and blog feeds for key industry competitors. It summarizes relevant updates and posts a structured summary to Slack on Monday, Wednesday, and Friday at 10 AM CST.

---

## 📦 Features

- Automatically fetches news articles and blog posts about competitors.
- Uses GPT to summarize articles.
- Tags content based on topic (Product Launches, Partnerships, AI, etc.).
- Sends formatted messages to Slack.
- Scheduled to run via cron 3x per week.

---

## 🚀 Getting Started

### 1. Clone the Repo

```bash
git clone git@bitbucket.org:APITURE/compwatcher.git
cd compwatcher
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with the following keys:

```
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL=#compwatcher
```

You should also configure the competitor sources in `feed_config.json`.

---

## 🖥️ Running the App

### Manual Run

```bash
python mainV2.py
```

### Post to Slack

```bash
python slack_messenger.py
```

---

## 🕒 Cron Job Setup

To schedule CompWatcher on Monday, Wednesday, and Friday at 10 AM CST:

```bash
0 15 * * 1,3,5 source /home/tim.sanford/compwatcher/venv/bin/activate && /home/tim.sanford/compwatcher/venv/bin/python /home/tim.sanford/compwatcher/mainV2.py >> /home/tim.sanford/compwatcher/cron.log 2>&1
```

> Adjust path and timezone as needed.

---

## 📁 File Structure

```
compwatcher/
├── mainV2.py
├── slack_messenger.py
├── feed_config.json
├── AdminDashboard.py
├── logs/
└── requirements.txt
```

---

## 🛠️ Requirements

- Python 3.9+
- Slack API Token
- cron (for scheduling)
- Bitbucket access (for deployment)

---

## 🧾 License

Internal use only – Apiture © 2025
