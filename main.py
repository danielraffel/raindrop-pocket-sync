import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

RAINDROP_TOKEN = os.getenv("RAINDROP_TOKEN")
POCKET_CONSUMER_KEY = os.getenv("POCKET_CONSUMER_KEY")
POCKET_ACCESS_TOKEN = os.getenv("POCKET_ACCESS_TOKEN")
RAINDROP_COLLECTION_ID = os.getenv("RAINDROP_COLLECTION_ID", "0")

DB_PATH = "db.sqlite3"
RAINDROP_API = f"https://api.raindrop.io/rest/v1/raindrops/{RAINDROP_COLLECTION_ID}"
POCKET_ADD_API = "https://getpocket.com/v3/add"
POCKET_SEND_API = "https://getpocket.com/v3/send"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS seen_bookmarks (
            id INTEGER PRIMARY KEY,
            link TEXT NOT NULL UNIQUE,
            last_update TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized.")

def get_raindrop_bookmarks():
    headers = {
        "Authorization": f"Bearer {RAINDROP_TOKEN}"
    }
    res = requests.get(RAINDROP_API + "?sort=-lastUpdate", headers=headers)
    res.raise_for_status()
    return res.json().get("items", [])

def get_last_update(bookmark_id, conn):
    cur = conn.cursor()
    cur.execute("SELECT last_update FROM seen_bookmarks WHERE id = ?", (bookmark_id,))
    row = cur.fetchone()
    return row[0] if row else None

def update_db(bookmark_id, link, last_update, conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO seen_bookmarks (id, link, last_update) VALUES (?, ?, ?)",
        (bookmark_id, link, last_update)
    )
    conn.commit()

def post_to_pocket(title, url, tags):
    data = {
        "url": url,
        "title": title,
        "tags": ",".join(tags) if tags else "",
        "consumer_key": POCKET_CONSUMER_KEY,
        "access_token": POCKET_ACCESS_TOKEN
    }
    res = requests.post(POCKET_ADD_API, json=data, headers={"Content-Type": "application/json", "X-Accept": "application/json"})
    res.raise_for_status()
    return res.json()

def favorite_in_pocket(item_id):
    data = {
        "consumer_key": POCKET_CONSUMER_KEY,
        "access_token": POCKET_ACCESS_TOKEN,
        "actions": [
            {
                "action": "favorite",
                "item_id": item_id
            }
        ]
    }
    res = requests.post(POCKET_SEND_API, json=data, headers={"Content-Type": "application/json", "X-Accept": "application/json"})
    res.raise_for_status()
    return res.json()

def run_sync():
    print(f"🔍 Checking for new or updated bookmarks at {datetime.utcnow().isoformat()}...")
    conn = sqlite3.connect(DB_PATH)
    bookmarks = get_raindrop_bookmarks()
    new_or_updated = 0

    for item in bookmarks:
        bid = item["_id"]
        link = item.get("link")
        title = item.get("title")
        tags = item.get("tags", [])
        last_update = item.get("lastUpdate")
        important = item.get("important", False)

        stored_update = get_last_update(bid, conn)

        if stored_update is None or last_update > stored_update:
            print(f"📬 Syncing bookmark: {title} ({link})")
            try:
                pocket_response = post_to_pocket(title, link, tags)
                item_id = pocket_response.get("item", {}).get("item_id")

                if important and item_id:
                    print("🌟 Marking as favorite in Pocket...")
                    favorite_in_pocket(item_id)

                update_db(bid, link, last_update, conn)
                new_or_updated += 1
            except Exception as e:
                print(f"❌ Failed to sync bookmark: {e}")

    conn.close()
    print(f"✅ Sync complete. {new_or_updated} bookmarks added or updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Initialize database and exit.")
    args = parser.parse_args()

    if args.init:
        init_db()
    else:
        run_sync()