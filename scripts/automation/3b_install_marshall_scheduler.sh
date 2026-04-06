#!/bin/bash

# --- 3b_install_marshall_scheduler.sh ---
# Run this once to set up the daily automated run (7:15 AM) on your Mac.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.brucehuynh.marshall_daily.plist"
PLIST_PATH="$SCRIPT_DIR/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"

if [ ! -f "$PLIST_PATH" ]; then
    echo "❌ Error: $PLIST_NAME not found in $SCRIPT_DIR"
    exit 1
fi

echo "⚙️ Installing Marshall Daily Scheduler..."

# Unload existing if any
launchctl unload "$TARGET_DIR/$PLIST_NAME" 2>/dev/null

# Copy to LaunchAgents
cp "$PLIST_PATH" "$TARGET_DIR/"

# Load the new agent
launchctl load "$TARGET_DIR/$PLIST_NAME"

echo "✅ Success! The Marshall tracker will now run automatically every day at 07:15."
echo "📝 Logs will be saved to /tmp/marshall_daily.out and /tmp/marshall_daily.err"
