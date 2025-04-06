# Raindrop.io to Pocket Sync

Backup your bookmarks by syncing new items added to [Raindrop.io](https://raindrop.io) into [Pocket](https://getpocket.com) — no 3rd-party cloud service required.

## Table of Contents
- [Features](#features)
- [Use Case](#use-case)
- [Installation](#installation)
- [Credential Setup](#credential-setup)
- [Running the Script](#running-the-script)
- [Debug Mode](#debug-mode)
- [Log Management](#log-management)
- [Supported Sync Fields](#supported-sync-fields)
- [License](#license)

## Features

- 👀 Tracks which bookmarks you've already sent
- 🔗 Syncs only new Raindrop bookmarks to Pocket
- 🏷️ Syncs tags from Raindrop to Pocket
- ⭐ Syncs favorites (important=true) to Pocket
- 💾 Uses local SQLite database for state tracking
- 💻 Works on macOS or Ubuntu
- 😶‍🌫️ No cloud server needed — just a VM or your local terminal
- 🥇 One-time setup with `.env` file and cron-compatible

---

## Use Case

You use Raindrop.io as your primary bookmark manager, and want Pocket as a backup store or secondary reading list — this script automates that.

---

## Installation

### Quick Setup with `uv`

1. First, install `uv` if you don't have it already:

   **Option A: Using standalone installers (Recommended)**
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows (using PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   
   **Option B: Using pip or pipx**
   ```bash
   # With pip
   pip install uv
   
   # Or with pipx
   pipx install uv
   ```
   
   If you installed via the standalone installer, you can update uv later with:
   ```bash
   uv self update
   ```

2. Clone and set up the repository:
   ```bash
   git clone https://github.com/danielraffel/raindrop-pocket-sync.git
   cd raindrop-pocket-sync
   chmod +x setup.sh  # Make the setup script executable
   ./setup.sh
   ```

   The `setup.sh` script will:
   - Create a Python virtual environment using `uv`
   - Install all dependencies
   - Create a `.env` template file for your credentials
   - Create necessary directory structure

### 🧩 Database Initialization (One-Time)

After running the setup script, initialize the local database (required for syncing to work):

```bash
source .venv/bin/activate  # If not already activated
python main.py --init
```

---

## Credential Setup

After installation, you'll need to add your API credentials to the `.env` file. Open the file in your text editor:

```bash
nano .env
```

### 1. Raindrop API Credentials

1. Go to [Raindrop.io → App Console](https://app.raindrop.io/settings/integrations)
2. Click "Create new app"
3. Fill in your app details (name, description)
4. Click "Create Test Token" and copy the generated token
5. Paste it in `.env` file as:
   ```
   RAINDROP_TOKEN=your_test_token_here
   ```

### 2. Pocket API Credentials

#### Step 1: Obtain a Pocket Platform Consumer Key

1. Register your application with Pocket at [Pocket Developer Apps](https://getpocket.com/developer/apps/new)
2. Fill in:
   - Application Name: (e.g., "RaindropToPocketSync")
   - Application Description: (brief description)
   - Permissions: "Add", "Modify" (minimum required)
   - Platforms: "Web"
3. After creating the app, copy the `consumer_key` 
4. Add to `.env` file:
   ```
   POCKET_CONSUMER_KEY=your_consumer_key_here
   ```

#### Step 2: Obtain a Request Token from Pocket

1. Use Postman, cURL, or any API tool to create a POST request:
   - URL: `https://getpocket.com/v3/oauth/request`
   - Headers:
     ```
     Content-Type: application/json; charset=UTF-8
     X-Accept: application/json
     ```
   - Body (JSON):
     ```json
     {
       "consumer_key": "YOUR_CONSUMER_KEY",
       "redirect_uri": "http://github.com"
     }
     ```
     (Replace `YOUR_CONSUMER_KEY` with your actual key)

2. Send the request and note the `code` value in the response (this is your request token)

#### Step 3: Authorize the App with Your Pocket Account

1. Visit this URL in your browser (replace with your actual request token):
   ```
   https://getpocket.com/auth/authorize?request_token=YOUR_REQUEST_TOKEN&redirect_uri=http://github.com
   ```

2. Log in to your Pocket account if prompted
3. Click "Authorize App"
4. You'll be redirected to GitHub (or your chosen redirect URI)

#### Step 4: Convert Request Token to Access Token

1. Create another POST request:
   - URL: `https://getpocket.com/v3/oauth/authorize`
   - Headers:
     ```
     Content-Type: application/json
     ```
   - Body (JSON):
     ```json
     {
       "consumer_key": "YOUR_CONSUMER_KEY",
       "code": "YOUR_REQUEST_TOKEN"
     }
     ```

2. Send the request and copy the `access_token` from the response
3. Add to `.env` file:
   ```
   POCKET_ACCESS_TOKEN=your_access_token_here
   ```

Your completed `.env` file should look like:
```
RAINDROP_TOKEN=your_test_token_here
RAINDROP_COLLECTION_ID=0
POCKET_CONSUMER_KEY=your_consumer_key_here
POCKET_ACCESS_TOKEN=your_access_token_here
```

Note: The `RAINDROP_COLLECTION_ID=0` setting is required and syncs your default Raindrop collection. If you want to sync a different collection, replace `0` with your specific collection ID.

---

## Running the Script

### First-Time Setup

If you've already imported all your Pocket bookmarks into Raindrop, run this command once to prevent duplicates:

```bash
source .venv/bin/activate  # If not already activated
python main.py --mark-all-seen
```

This marks all existing Raindrop bookmarks as "already synced" to Pocket.

### 📌 Bulk Sync Limits and Verification

- The `--mark-all-seen` command supports marking up to **10,000** bookmarks as "already seen" in one run.
- If your Raindrop collection exceeds that, run the script again or adjust the `max_total` parameter in the script source.
- To verify how many bookmarks were marked, you can inspect the local SQLite database with:

```bash
sqlite3 /opt/raindrop-pocket-sync/db.sqlite3 "SELECT COUNT(*) FROM seen_bookmarks;"
```

This will return the number of Raindrop bookmarks currently tracked as “seen.”

### Regular Usage

To manually run the sync:

```bash
source .venv/bin/activate  # If not already activated
python main.py
```

### Automation with Cron

To check for new URLs every 10 minutes:

1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add this line (update paths to match your installation):
   ```
   */10 * * * * cd /opt/raindrop-pocket-sync && /opt/raindrop-pocket-sync/.venv/bin/python main.py >> cron.log 2>&1
   ```

### Additional Commands

Initialize the database (safe to re-run, no data will be lost):
```bash
python main.py --init
```

---

## Debug Mode

Use the `--debug` flag for troubleshooting or development. It increases verbosity and gives insight into internal operations.

### 🔍 What `--debug` Enables

- Prints raw Raindrop API responses  
- Logs internal decisions (e.g. new vs. updated bookmarks)  
- Displays database comparisons (`lastUpdate` vs stored)  
- Notes skipped or already-synced bookmarks  

### 🛠️ Usage

**Run with debug logging:**

```bash
python main.py --debug
```

**Run in quiet mode (default):**

```bash
python main.py
```

---

## 🧹 Log Management

This project writes sync output to a persistent log file:

```
/opt/raindrop-pocket-sync/cron.log
```

To prevent the log from growing indefinitely, it's recommended to enable automatic log rotation.

### ✅ Setting Up Log Rotation (via `logrotate`)

You can configure `logrotate` to manage the log file by creating a config at:

```
/etc/logrotate.d/raindrop-pocket-sync
```

With the following contents:

```nginx
/opt/raindrop-pocket-sync/cron.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
```

### 🔍 What This Does

- Rotates the log **daily**
- Keeps the **last 7 days** of logs (`.gz` compressed)
- Automatically handles rotation **without stopping the cron job**
- Skips empty logs and avoids errors if the file doesn't exist

This ensures the cron log stays manageable while still preserving recent sync history for debugging or auditing.

---

## Supported Sync Fields

| Raindrop       | Pocket        | Notes |
|----------------|----------------|-------|
| `url`          | `url`          | ✅ Synced always |
| `title`        | `title`        | ✅ Synced if available |
| `tags`         | `tags`         | ✅ Tags are transferred directly |
| `important`    | `favorite`     | ✅ `important: true` in Raindrop → `favorite: 1` in Pocket |

---

## License

MIT (for personal use)
