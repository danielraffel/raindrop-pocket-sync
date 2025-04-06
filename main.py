
import os
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import sys

load_dotenv()

RAINDROP_TOKEN = os.getenv("RAINDROP_TOKEN")
RAINDROP_COLLECTION_ID = os.getenv("RAINDROP_COLLECTION_ID", "0")
POCKET_CONSUMER_KEY = os.getenv("POCKET_CONSUMER_KEY")
POCKET_ACCESS_TOKEN = os.getenv("POCKET_ACCESS_TOKEN")

RAINDROP_API = f"https://api.raindrop.io/rest/v1/raindrops/{RAINDROP_COLLECTION_ID}"
DB_PATH = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS seen_bookmarks (
            id INTEGER PRIMARY KEY,
            link TEXT NOT NULL UNIQUE,
            last_update TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized.")

def get_seen_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM seen_bookmarks")
    ids = {row[0] for row in c.fetchall()}
    conn.close()
    return ids

def get_raindrop_bookmarks():
    headers = {"Authorization": f"Bearer {RAINDROP_TOKEN}"}
    res = requests.get(RAINDROP_API + "?sort=-lastUpdate", headers=headers)
    if res.status_code == 401:
        print("❌ Unauthorized: Please check your RAINDROP_TOKEN")
        print("Response:", res.text)
        sys.exit(1)
    res.raise_for_status()
    return res.json().get("items", [])

def post_to_pocket(url, title=None, tags=None, favorite=False):
    data = {
        "url": url,
        "favorite": 1 if favorite else 0,
        "consumer_key": POCKET_CONSUMER_KEY,
        "access_token": POCKET_ACCESS_TOKEN
    }
    if title:
        data["title"] = title
    if tags:
        data["tags"] = ",".join(tags)
    res = requests.post("https://getpocket.com/v3/add", json=data, headers={
        "Content-Type": "application/json; charset=UTF-8",
        "X-Accept": "application/json"
    })
    res.raise_for_status()

def mark_bookmarks_as_seen(bookmarks):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for item in bookmarks:
        c.execute("INSERT OR IGNORE INTO seen_bookmarks (id, link, last_update) VALUES (?, ?, ?)",
                  (item["_id"], item["link"], item["lastUpdate"]))
    conn.commit()
    conn.close()

def run_sync(mark_all_seen=False):
    print(f"🔍 Checking Raindrop for new bookmarks at {datetime.now(timezone.utc).isoformat()}...")
    bookmarks = get_raindrop_bookmarks()
    seen_ids = get_seen_ids()

    if mark_all_seen:
        mark_bookmarks_as_seen(bookmarks)
        print("✅ Marked all current bookmarks as seen (no items sent to Pocket).")
        return

    new_items = [item for item in bookmarks if item["_id"] not in seen_ids]
    print(f"📌 Found {len(new_items)} new bookmark(s)")

    for item in new_items:
        print(f"→ Sending to Pocket: {item['link']}")
        post_to_pocket(item["link"], item.get("title"), item.get("tags", []), item.get("important", False))
        mark_bookmarks_as_seen([item])

if __name__ == "__main__":
    if "--init" in sys.argv:
        init_db()
    elif "--mark-all-seen" in sys.argv:
        run_sync(mark_all_seen=True)
    else:
        run_sync()
