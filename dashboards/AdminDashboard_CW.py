import os
import json
import streamlit as st
from dotenv import load_dotenv, dotenv_values, set_key
import pandas as pd
import subprocess
from slack_sdk import WebClient

load_dotenv()
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

if ENVIRONMENT.lower() == "sandbox":
    st.warning("🚧 You are running in the Sandbox Environment")


# Load and display current .env config
def load_env():
    return dotenv_values(".env")


def save_env(updated_values):
    for env_key, env_value in updated_values.items():
        set_key(".env", env_key, env_value)


# Load and save competitor feed toggle config
def load_competitor_config():
    if not os.path.exists("competitor_config.json"):
        return {}
    with open("competitor_config.json") as f:
        return json.load(f)


def save_competitor_config(config):
    with open("competitor_config.json", "w") as f:
        json.dump(config, f, indent=2)


# Load and save RSS config with enable/disable flag
def load_rss_config():
    if not os.path.exists("rss_sources.json"):
        return {}
    with open("rss_sources.json") as f:
        return json.load(f)


def save_rss_config(config):
    with open("rss_sources.json", "w") as f:
        json.dump(config, f, indent=2)


page = st.sidebar.radio("Go to", [
    "Configuration", "Competitor Feeds", "RSS Feeds", "Prompt Tester",
    "Slack Preview", "Logs Viewer", "Acknowledgments",
    "Feedback Stats", "Manual Run", "Schedule", "Delete Slack Message"
])

# --- CONFIGURATION ---
if page == "Configuration":
    st.header("Environment Configuration")
    env = load_env()
    updated_env = {}

    st.subheader("Core Environment Settings")
    model = st.text_input("OpenAI Model", env.get("OPENAI_MODEL", "gpt-4"))
    temp = st.slider("OpenAI Temperature", 0.0, 1.0, float(env.get("OPENAI_TEMPERATURE", 0.3)), step=0.1)

    updated_env["OPENAI_MODEL"] = model
    updated_env["OPENAI_TEMPERATURE"] = str(temp)

    for env_key, env_value in env.items():
        if env_key not in ["OPENAI_MODEL", "OPENAI_TEMPERATURE"]:
            updated_env[env_key] = st.text_input(env_key, env_value)

    if st.button("Save Changes"):
        save_env(updated_env)
        st.success(".env updated successfully.")

# --- COMPETITOR FEEDS ---
elif page == "Competitor Feeds":
    st.header("Manage Competitor Feeds")
    st.markdown("Enable/disable feeds and test individual fetch functions.")

    current_config = load_competitor_config()
    updated_config = {}

    st.subheader("Competitor Toggle Switches")
    for comp, enabled in current_config.items():
        updated_config[comp] = st.checkbox(comp, value=enabled)

    if st.button("Save Competitor Settings"):
        save_competitor_config(updated_config)
        st.success("Feed toggles updated successfully.")

# --- RSS FEEDS ---
elif page == "RSS Feeds":
    st.header("Manage RSS Feeds")
    st.markdown("Add, edit, enable/disable, or remove additional RSS feeds for competitive monitoring.")

    rss_config = load_rss_config()
    updated_rss_config = {}
    remove_keys = []

    st.subheader("Current RSS Feeds")
    for name, data in rss_config.items():
        url = data["url"] if isinstance(data, dict) else data
        enabled = data.get("enabled", True) if isinstance(data, dict) else True

        col1, col2, col3, col4 = st.columns([3, 6, 2, 1])
        with col1:
            new_name = st.text_input(f"Name for {name}", value=name, key=f"rss_name_{name}")
        with col2:
            new_url = st.text_input(f"URL for {name}", value=url, key=f"rss_url_{name}")
        with col3:
            is_enabled = st.checkbox("Enabled", value=enabled, key=f"rss_enabled_{name}")
        with col4:
            if st.button("❌", key=f"remove_{name}"):
                remove_keys.append(name)
                continue

        updated_rss_config[new_name] = {"url": new_url, "enabled": is_enabled}

    for key in remove_keys:
        updated_rss_config.pop(key, None)

    st.markdown("---")
    st.subheader("Add New Feed")
    new_feed_name = st.text_input("Feed Name", key="new_rss_name")
    new_feed_url = st.text_input("Feed URL", key="new_rss_url")
    new_feed_enabled = st.checkbox("Enable this feed", value=True, key="new_rss_enabled")

    if st.button("Add Feed"):
        if new_feed_name and new_feed_url:
            updated_rss_config[new_feed_name] = {"url": new_feed_url, "enabled": new_feed_enabled}
            st.success(f"Added new feed: {new_feed_name}")
        else:
            st.warning("Please fill in both name and URL fields.")

    if st.button("Save RSS Feeds"):
        save_rss_config(updated_rss_config)
        st.success("RSS feeds updated successfully!")


# --- PROMPT TESTER ---
# elif page == "Prompt Tester":
    # st.header("Test GPT Prompts")
    # st.markdown("Use this section to paste article content and test the relevance and summary prompts.")

    # title = st.text_input("Article Title")
    # content = st.text_area("Article Content", height=200)

    # if st.button("Run Prompt Tests"):
        # test_article = {"title": title, "content": content}

        # with st.spinner("Analyzing with GPT..."):
        # relevant = is_article_relevant(test_article)
        # summary = summarize_article(test_article)

        # st.subheader("🔍 Relevance Result")
        # st.markdown(f"**Relevant:** {'✅ YES' if relevant else '❌ NO'}")

        # st.subheader("📝 Summary + Action")
        # st.markdown(f"```\n{summary}\n```)  # formatted output")

# --- SLACK PREVIEW (Placeholder) ---
elif page == "Slack Preview":
    st.header("Simulate Slack Message")
    st.markdown("This will render a Slack Block Kit preview using fake or real data.")
    st.info("Slack rendering logic to be added.")


# --- LOGS VIEWER ---
elif page == "Logs Viewer":
    st.header("Logs Viewer")
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))

    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith(".log")], reverse=True)
    if log_files:
        selected_log = st.selectbox("Choose a log file", log_files)

        if selected_log:
            with open(os.path.join(logs_dir, selected_log), "r") as f:
                log_content = f.read()
            st.text_area("Log Output", log_content, height=400)
    else:
        st.info("📭 No log files available yet. Run the script to generate logs.")


# --- ACKNOWLEDGMENTS ---
elif page == "Acknowledgments":
    st.header("Acknowledgment Log")

    try:
        df = pd.read_csv("../logs/acknowledgments.csv", names=["Timestamp", "User", "Article", "Feedback"])

        # Render with HTML and CSS to enable wrapping
        st.markdown("""
        <style>
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            vertical-align: top;
            border: 1px solid #444;
            padding: 8px;
            word-wrap: break-word;
            white-space: normal;
        }
        th {
            background-color: #222;
            color: #fff;
        }
        </style>
        """, unsafe_allow_html=True)

        table_html = "<table><tr><th>Timestamp</th><th>User</th><th>Article</th><th>Feedback</th></tr>"
        for _, row in df.iterrows():
            table_html += f"<tr><td>{row['Timestamp']}</td><td>{row['User']}</td><td>{row['Article']}</td><td>{row['Feedback']}</td></tr>"
        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Failed to load acknowledgment log: {e}")


# --- FEEDBACK STATS ---
elif page == "Feedback Stats":
    st.header("📊 Feedback Summary")
    try:
        df = pd.read_csv("../logs/acknowledgments.csv", names=["Timestamp", "User", "Article", "Feedback"])

        st.subheader("Total Feedback by Type")
        st.bar_chart(df["Feedback"].value_counts())

        st.subheader("User Sentiment Breakdown")
        user_feedback = df.groupby(["User", "Feedback"]).size().unstack(fill_value=0)
        st.dataframe(user_feedback)

    except Exception as e:
        st.error(f"Error loading or visualizing feedback: {e}")

# --- MANUAL RUN ---
elif page == "Manual Run":
    st.header("Trigger Manual Run")
    st.markdown("This will run the CompWatcher script manually and show output.")

    if st.button("Run Now"):
        with st.spinner("Running fetch and summarization script..."):
            result = subprocess.run(["python", "main_intel.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.success("✅ Script executed.")
            else:
                st.error(f"❌ Script failed with exit code {result.returncode}")
                st.text_area("Stdout", result.stdout, height=150)
                st.text_area("Stderr", result.stderr, height=150)

        # Ensure logs directory exists
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)

        try:
            log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith(".log")])
            if log_files:
                latest_log = log_files[-1]
                with open(os.path.join(logs_dir, latest_log), "r") as log_file:
                    st.text_area("Latest Log Output", log_file.read(), height=400)
            else:
                st.info("📭 No log files found yet.")
        except Exception as e:
            st.error(f"⚠️ Failed to load log file: {e}")


# --- SCHEDULE MANAGEMENT ---
elif page == "Schedule":
    st.header("🕒 Cron Schedule Management")

    st.markdown("Below is the current cron job entry used to schedule CompWatcher.")
    current_cron = subprocess.getoutput("crontab -l")
    intelwatcher_cron = "\n".join([
     line for line in current_cron.splitlines()
     if "compwatcher_prod" in line
    ])

    st.text_area("Current CompWatcher Cron Entry", value=intelwatcher_cron, height=100)

    st.markdown("---")
    st.subheader("✏️ Update Cron Schedule")
    new_schedule = st.text_input("Enter new cron timing + command", value=intelwatcher_cron)

    if st.button("Update Cron Job"):
        new_crontab = []
        replaced = False
        for line in current_cron.splitlines():
            if "compwatcher_prod" in line or "run.sh" in line:
                new_crontab.append(new_schedule)
                replaced = True
            else:
                new_crontab.append(line)

        if not replaced:
            new_crontab.append(new_schedule)

        temp_path = "/tmp/new_crontab.txt"
        with open(temp_path, "w") as f:
            f.write("\n".join(new_crontab) + "\n")
        os.system(f"crontab {temp_path}")
        os.remove(temp_path)
        st.success("✅ Cron job updated successfully!")

# --- DELETE SLACK MESSAGE ---
elif page == "Delete Slack Message":
    st.header("🗑️ Delete Slack Message")
    st.markdown("Use this tool to delete a specific Slack message by channel and timestamp.")
    st.info("Only messages posted by this bot using the same token can be deleted.")

    channel = st.text_input("Channel ID", value=os.getenv("DEFAULT_CHANNEL_ID", ""))
    ts = st.text_input("Message Timestamp (e.g., 1712874225.158169)")

    if st.button("Delete Message"):
        if channel and ts:
            try:
                response = client.chat_delete(channel=channel, ts=ts)
                if response["ok"]:
                    st.success("✅ Message deleted successfully!")
                else:
                    st.error(f"❌ Failed to delete message: {response['error']}")
            except Exception as e:
                st.error(f"❌ Exception occurred: {e}")
        else:
            st.warning("Please enter both channel ID and timestamp.")

    st.markdown("---")
    st.subheader("🗑️ Delete Last Posted Message")

    # Use absolute path to logs
    LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    LAST_POST_FILE = os.path.join(LOGS_DIR, "last_post.json")

    if st.button("Delete Last Bot Message"):
        try:
            with open(LAST_POST_FILE, "r") as f:
                history = json.load(f)

            last_post = history[0] if isinstance(history, list) and history else None
            if not last_post:
                st.warning("No post data found in last_post.json.")
            else:
                del_response = client.chat_delete(
                    channel=last_post["channel"],
                    ts=last_post["ts"]
                )
                if del_response["ok"]:
                    st.success("✅ Last posted message deleted!")
                else:
                    st.error(f"❌ Failed to delete last message: {del_response['error']}")
        except FileNotFoundError:
            st.warning("⚠️ No last_post.json file found. Message info missing.")
        except Exception:
            st.exception("❌ Error deleting last message.")
