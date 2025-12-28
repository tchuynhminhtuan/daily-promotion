#!/bin/bash

# Navigate to the root directory
cd "$(dirname "$0")/../.."

echo "------------------------------------------"
echo "🚀 Starting Marshall Daily Workflow (Core Logic)"
echo "📅 Date: $(date)"
echo "------------------------------------------"

# 1. Run Scraper Bridge
echo "🔎 Scraping Marshall prices via Core Scrapers..."
python3 projects/marshall_daily/marshall_workflow.py

# 2. Generate Dedicated Marshall Dashboard (Using core logic safely)
echo "📊 Generating dedicated Marshall dashboard..."
python3 projects/marshall_daily/generate_marshall_report.py

# Record for local project
cp docs/marshall.html projects/marshall_daily/index.html

# 3. Update Integrated Main Dashboard
echo "📊 Updating main dashboard (Integrated)..."
python3 code/generate_report.py

echo "------------------------------------------"
echo "✅ Marshall Daily Workflow Complete!"
echo "Check docs/index.html for results."
echo "------------------------------------------"
