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

# 4. Push Results to GitHub
echo "🚀 Pushing results to GitHub..."

git add code/
git add .github/

DATE=$(date +%Y-%m-%d)
git add "content/$DATE/*.csv" || echo "⚠️ No new CSV data found for $DATE"

git commit -m "Auto: Daily Scrape Update - $(date)" || echo "⚠️ No changes to commit"
git stash
git pull origin main --rebase
git stash pop || echo "⚠️ No stash to pop."
git push

echo "🎉 Done! Data synced to GitHub."
