#!/bin/bash

echo "🔧 Setting up Raindrop to Pocket Sync using uv..."

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' is not installed. Please install it first from https://github.com/astral-sh/uv"
    exit 1
fi

# Create isolated environment
uv venv
source .venv/bin/activate

# Install requirements locally
uv pip install -r requirements.txt

# Create .env template if not present
if [ ! -f .env ]; then
  echo "Creating default .env file..."
  cat <<EOL > .env
RAINDROP_TOKEN=your_raindrop_token_here
RAINDROP_COLLECTION_ID=0
POCKET_CONSUMER_KEY=your_pocket_consumer_key
POCKET_ACCESS_TOKEN=your_pocket_access_token
EOL
  echo "⚠️ Edit the .env file to add your API credentials."
fi

# Use local python to init DB
echo "Initializing SQLite database..."
.venv/bin/python main.py --init

echo "✅ Setup complete. Run with: source .venv/bin/activate && .venv/bin/python main.py"
