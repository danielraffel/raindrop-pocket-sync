import os
import sqlite3
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from dateutil.parser import isoparse
import argparse

# Load environment variables
load_dotenv()

RAINDROP_TOKEN = os.getenv("RAINDROP_TOKEN")
POCKET_CONSUMER_KEY = os.getenv("POCKET_CONSUMER_KEY")
POCKET_ACCESS_TOKEN = os.getenv("POCKET_ACCESS_TOKEN")
RAINDROP_COLLECTION_ID = os.getenv("RAINDROP_COLLECTION_ID", "0")

DB_PATH = "/opt/raindrop-pocket-sync/db.sqlite3"
RAINDROP_API = f"https://api.raindrop.io/rest/v1/raindrops/{RAINDROP_COLLECTION_ID or '0'}"
POCKET_ADD_API = "https://getpocket.com/v3/add"
POCKET_SEND_API = "https://getpocket.com/v3/send"

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"

DEBUG = False

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

def get_raindrop_bookmarks(since_iso, per_page=50, max_pages=50):
    headers = {
        "Authorization": f"Bearer {RAINDROP_TOKEN}"
    }

    all_items = []
    page = 1
    since_dt = isoparse(since_iso)

    while page <= max_pages:
        url = RAINDROP_API
        params = {
            "sort": "-lastUpdate",
            "perpage": per_page,
            "page": page,
        }

        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        items = res.json().get("items", [])

        if DEBUG:
            print(f"📄 Page {page}: Retrieved {len(items)} bookmarks")

        if not items:
            break

        # ✅ Add all and continue paginating — don’t break early
        all_items.extend(items)
        page += 1

    # ✅ Filter after all pages are collected
    filtered_items = [b for b in all_items if isoparse(b["lastUpdate"]) > since_dt]
    return filtered_items

def get_last_update(bookmark_id, conn):
    cur = conn.cursor()
    cur.execute("SELECT last_update FROM seen_bookmarks WHERE id = ?", (bookmark_id,))
    row = cur.fetchone()
    return row[0] if row else None

def get_latest_seen_timestamp(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(last_update) FROM seen_bookmarks")
    row = cur.fetchone()
    return row[0] if row and row[0] else DEFAULT_TIMESTAMP

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
        "consumer_key": POCKET_CONSUMER_KEY,
        "access_token": POCKET_ACCESS_TOKEN
    }
    if tags:
        data["tags"] = ",".join(tags)
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
    print(f"🔍 Checking for new or updated bookmarks at {datetime.now(timezone.utc).isoformat()}...")
    conn = sqlite3.connect(DB_PATH)

    since = get_latest_seen_timestamp(conn)
    since_dt = isoparse(since)

    if DEBUG:
        print(f"🕒 Last seen update in DB: {since} ({since_dt.isoformat()})")

    bookmarks = get_raindrop_bookmarks(since_iso=since)

    if DEBUG:
        print(f"📥 Fetched {len(bookmarks)} bookmarks from Raindrop.")
        if not bookmarks:
            print("⚠️ No bookmarks returned! Check RAINDROP_COLLECTION_ID (currently set to:", RAINDROP_COLLECTION_ID, ") and ensure your token is valid.")
        else:
            print("🔍 Sample Raindrop entries:")
            for b in bookmarks[:5]:
                print("  - ID:", b.get("_id"), "| Title:", b.get("title"), "| URL:", b.get("link"), "| Updated:", b.get("lastUpdate"))

            print("📝 New bookmarks to sync:")
            for b in bookmarks:
                print(f"  - {b.get('title')} | {b.get('link')} | Updated: {b.get('lastUpdate')}")

    new_or_updated = 0

    for item in bookmarks:
        bid = item["_id"]
        link = item.get("link")
        title = item.get("title")
        tags = item.get("tags", [])
        last_update = item.get("lastUpdate")
        important = item.get("important", False)

        stored_update = get_last_update(bid, conn)
        if DEBUG:
            print(f"🔎 Checking bookmark: {title} | lastUpdate: {last_update} | stored: {stored_update}")

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
                if hasattr(e, 'response') and e.response is not None:
                    print(f"❌ Pocket Error Response: {e.response.text}")
                print(f"❌ Failed to sync bookmark: {e}")

    conn.close()
    print(f"✅ Sync complete. {new_or_updated} bookmarks added or updated.")

def mark_all_as_seen():
    print("🔖 Marking up to 10,000 current Raindrop bookmarks as seen...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    bookmarks = get_raindrop_bookmarks(since_iso=DEFAULT_TIMESTAMP, per_page=100, max_pages=200)

    for item in bookmarks:
        bid = item["_id"]
        link = item.get("link")
        last_update = item.get("lastUpdate")
        if bid and link and last_update:
            update_db(bid, link, last_update, conn)

    conn.close()
    print(f"✅ Marked {len(bookmarks)} bookmarks as already seen.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Initialize database and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--mark-all-seen", action="store_true", help="Mark all current Raindrop bookmarks as seen.")
    args = parser.parse_args()

    DEBUG = args.debug

    if DEBUG:
        print("🔐 Loaded Raindrop token:", RAINDROP_TOKEN[:8], "...")

    if args.init:
        init_db()
    elif args.mark_all_seen:
        mark_all_as_seen()
    else:
        run_sync()