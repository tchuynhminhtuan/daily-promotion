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

# 1. Notify User
osascript -e 'display notification "Scrapers Running: Marshall" with title "Daily Promotion (Marshall)"'

# 2. Run Scraper Bridge
echo "🔎 Scraping Marshall prices via Core Scrapers..."
python3 projects/marshall_daily/marshall_workflow.py

# 3. Generate Dedicated Marshall Dashboard
echo "📊 Generating dedicated Marshall dashboard..."
python3 projects/marshall_daily/generate_marshall_report.py

# 4. Update Integrated Main Dashboard
echo "📊 Updating main dashboard (Integrated)..."
python3 code/generate_report.py

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
