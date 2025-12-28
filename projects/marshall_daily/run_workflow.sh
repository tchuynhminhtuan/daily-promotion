#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

echo "------------------------------------------"
echo "🚀 Starting Marshall Daily Workflow"
echo "📅 Date: $(date)"
echo "------------------------------------------"

# 1. Run Scraper
echo "🔎 Scraping Marshall prices..."
python3 scraper.py

# Check if scraper succeeded
if [ $? -ne 0 ]; then
    echo "❌ Scraper failed. Aborting."
    exit 1
fi

# 2. Generate Dashboard
echo "📊 Generating dashboard..."
python3 dashboard_generator.py

# 3. Git Push
echo "⬆️ Pushing to GitHub..."
git add content/ index.html
git commit -m "update: daily marshall data $(date +'%Y-%m-%d')"
git push

echo "------------------------------------------"
echo "✅ Marshall Daily Workflow Complete!"
echo "------------------------------------------"
