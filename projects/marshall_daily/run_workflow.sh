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

# 2. Generate Dedicated Marshall Dashboard (Using core logic without code changes)
echo "📊 Generating dedicated Marshall dashboard..."
# Temporarily swap content directory to use Marshall data
mv content content_backup
ln -s projects/marshall_daily/content content
# Run core report (outputs to docs/index.html)
python3 code/generate_report.py
# 1. Store in projects folder for record
cp docs/index.html projects/marshall_daily/index.html
# 2. Make it LIVE on GitHub Pages
mv docs/index.html docs/marshall.html
# Restore original content
rm content
mv content_backup content

# Clean up temporary analysis data
rm -rf projects/marshall_daily/content/analysis_result

# 3. Update Integrated Main Dashboard
echo "📊 Updating main dashboard (Integrated)..."
python3 code/generate_report.py

echo "------------------------------------------"
echo "✅ Marshall Daily Workflow Complete!"
echo "Check docs/index.html for results."
echo "------------------------------------------"
