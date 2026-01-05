#!/bin/bash

# --- 1b_marshall_workflow.sh ---
# Specialized automation for Marshall Tracker.
# Handles scraping, dashboard updates, and Git.

echo "🚀 Starting Marshall Daily Workflow..."

# ENSURE WE ARE IN THE PROJECT ROOT
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$PROJECT_ROOT" || exit

echo "📍 Working Directory: $PROJECT_ROOT"

# --- INTERNET CHECK ---
check_internet() {
    echo "📡 Checking internet connection..."
    while ! ping -c 1 -W 2000 google.com > /dev/null 2>&1; do
        echo "❌ No internet connection."
        echo "⏳ Waiting 30 minutes. Press [ENTER] to retry immediately..."
        read -t 1800
        echo "🔄 Retrying internet check..."
    done
    echo "✅ Internet connected. Proceeding..."
}

check_internet


# 0. PRE-FLIGHT SYNC (Sandboxing) 🥪
# Capture output to check if stash was actually created
STASH_OUT=$(git stash push -m "Auto-Stash: Marshall Pre-Run")
echo "Stash Status: $STASH_OUT"

git pull origin main --rebase

# Only pop if we actually stashed something (avoid popping old stashes)
if [[ "$STASH_OUT" != *"No local changes"* ]]; then
    echo "♻️ Restoring local changes..."
    git stash pop || echo "⚠️ Conflict during stash pop. Please resolve manually."
else
    echo "✅ No local changes to restore (Clean state)."
fi

# 1. Notify User
osascript -e 'display notification "Scrapers Running: Marshall" with title "Daily Promotion (Marshall)"'

# 2. Run Scraper Bridge
echo "🔎 Scraping Marshall prices via Core Scrapers..."
python3 projects/marshall_daily/marshall_workflow.py

# 3. Generate Dedicated Marshall Dashboard
echo "📊 Generating dedicated Marshall dashboard..."
python3 projects/marshall_daily/generate_marshall_report.py

if [ $? -eq 0 ]; then
    # 3. Handle Git Push
    echo "📤 Pushing Marshall updates to GitHub..."
    
    # Store current date
    DATE=$(date +%Y-%m-%d)
    
    # Add project data
    git add "projects/marshall_daily/content/$DATE/*.csv" || echo "⚠️ No new Marshall CSV data found for $DATE"
    
    # Add Marshall Dashboards
    git add "docs/marshall.html"
    
    git commit -m "Auto (Local): Marshall Daily Update - $(date)" || echo "⚠️ No changes to commit"
    
    # Sync with origin
    git pull origin main --rebase
    git push origin main
    
    osascript -e 'display notification "Workflow Completed: Marshall Dashboard Updated" with title "Daily Promotion (Marshall)"'
    echo "🎉 Done! Marshall tracker updated and synced."
else
    osascript -e 'display notification "Workflow FAILED: Check logs" with title "Daily Promotion (Marshall)"'
    echo "❌ ERROR: Workflow execution failed."
    exit 1
fi
