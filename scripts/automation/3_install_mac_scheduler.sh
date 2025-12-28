#!/bin/bash

# --- 3_install_mac_scheduler.sh ---
# Run this once to set up the daily automated run (9:00 AM) on your Mac.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.brucehuynh.dailyscrape.plist"
PLIST_PATH="$SCRIPT_DIR/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"

if [ ! -f "$PLIST_PATH" ]; then
    echo "❌ Error: $PLIST_NAME not found in $SCRIPT_DIR"
    exit 1
fi

echo "⚙️ Installing Daily Scraper Scheduler..."

# Unload existing if any
launchctl unload "$TARGET_DIR/$PLIST_NAME" 2>/dev/null

# Copy to LaunchAgents
cp "$PLIST_PATH" "$TARGET_DIR/"

# Load the new agent
launchctl load "$TARGET_DIR/$PLIST_NAME"

echo "✅ Success! The scraper will now run automatically every day at 09:00."
echo "📝 Logs will be saved to /tmp/daily_scrape.out and /tmp/daily_scrape.err"
