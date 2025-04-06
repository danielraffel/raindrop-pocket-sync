import os
import sqlite3
import requests
from datetime import datetime, timezone
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
        "consumer_key": POCKET_CONSUMER_KEY,
        "access_token": POCKET_ACCESS_TOKEN
    }
    if tags:
        data["tags"] = ",".join(tags)
    res = requests.post(POCKET_ADD_API, json=data, headers={"Content-Type": "application/json", "X-Accept": "application/json"})
    res.raise_for_status()
    return res.json()

