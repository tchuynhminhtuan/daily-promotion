#!/bin/bash

echo "🚀 Starting Hybrid Scraper Workflow..."

# 1. Install Dependencies (Just in case)
echo "📦 Checking dependencies..."
pip3 install -r requirements.txt || echo "⚠️ Warning: Pip install failed. Assuming packages are present or handled by another python."
python3 -m playwright install chromium

# 2. Pull latest data from GitHub (The other 4 scrapers)
echo "⬇️ Pulling latest data from GitHub..."
git pull origin main --rebase

# 3. Run Local Scrapers (FPT & MW)
echo "🕷️ Running FPT Scraper (Local)..."
python3 code/1-Apple_FPT_playwright.py

echo "🕷️ Running Mobile World Scraper (Local)..."
python3 code/2-Apple_MW_playwright.py

# 4. Generate Final Report
echo "📊 Generating Final Report..."
python3 code/generate_report.py

echo "✅ Hybrid Workflow Complete! Check the 'reports' folder."
