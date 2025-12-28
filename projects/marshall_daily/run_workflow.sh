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

# 2. Generate Dashboard using Core Report Generator
echo "📊 Generating dashboard via Core Report Generator..."
python3 code/generate_report.py

echo "------------------------------------------"
echo "✅ Marshall Daily Workflow Complete!"
echo "Check docs/index.html for results."
echo "------------------------------------------"
