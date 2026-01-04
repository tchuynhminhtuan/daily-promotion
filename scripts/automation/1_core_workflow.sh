#!/bin/bash

# --- 1_core_workflow.sh ---
# The heart of the automation. Handles scraping, DB updates, and Git pushing.

echo "🚀 Starting Hybrid Scraper Workflow..."

# ENSURE WE ARE IN THE PROJECT ROOT
# This logic works regardless of where the script is called from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"
cd "$PROJECT_ROOT" || exit

echo "📍 Working Directory: $PROJECT_ROOT"

# --- INTERNET CHECK ---
check_internet() {
    echo "📡 Checking internet connection..."
    while ! ping -c 1 -W 2000 google.com > /dev/null 2>&1; do
        echo "❌ No internet connection. Waiting 30 minutes to retry..."
        sleep 1800 # 30 minutes
        echo "🔄 Retrying internet check..."
    done
    echo "✅ Internet connected. Proceeding..."
}

check_internet


# 0. PRE-FLIGHT SYNC (Sandboxing) 🥪
# Isolates local changes to prevent conflicts during run
echo "🛡️ Executing Safety Sync (Stash -> Pull -> Pop)..."

# Capture output to check if stash was actually created
STASH_OUT=$(git stash push -m "Auto-Stash: Pre-Run Safety")
echo "Stash Status: $STASH_OUT"

git pull origin main --rebase                  # Sync with remote

# Only pop if we actually stashed something (avoid popping old stashes)
if [[ "$STASH_OUT" != *"No local changes"* ]]; then
    echo "♻️ Restoring local changes..."
    git stash pop || echo "⚠️ Conflict during stash pop. Please resolve manually."
else
    echo "✅ No local changes to restore (Clean state)."
fi

# 1. Install/Update Dependencies
echo "📦 Checking dependencies..."
pip3 install -r requirements.txt --quiet || echo "⚠️ Warning: Pip install failed. Continuing..."
python3 -m playwright install chromium --quiet

# 2. Run Local Scrapers (FPT & MW Only - Sequential/Parallel)
osascript -e 'display notification "Scrapers Running: FPT & MW" with title "Daily Promotion"'
echo "🕷️ Running FPT & MW Scrapers..."

# Use absolute paths or root-relative paths
python3 "$PROJECT_ROOT/code/1-Apple_FPT_playwright.py"
python3 "$PROJECT_ROOT/code/2-Apple_MW_playwright.py"

osascript -e 'display notification "Scrapers Completed: FPT & MW" with title "Daily Promotion"'
echo "✅ FPT & MW Scrapers Completed."

# 3. Handle Normalization & Data Versioning
# (Add any additional normalization logic here if needed)

# 4. Push Results to GitHub (STRICT SCOPE)
echo "🚀 Pushing results to GitHub..."

DATE=$(date +%Y-%m-%d)

# Only commit DATA and REPORT (Ignore Code/Config changes)
git add "content/$DATE/*.csv" || echo "⚠️ No new CSV data found for $DATE"
git add "docs/index.html" || echo "⚠️ No report update found"

git commit -m "Auto: Daily Scrape Update - $(date)" || echo "⚠️ No changes to commit"

# Post-Flight Sync (Just in case remote moved during run)
git pull origin main --rebase
git push

echo "🎉 Done! Data synced to GitHub."
