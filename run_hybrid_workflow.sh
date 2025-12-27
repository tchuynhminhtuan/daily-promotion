#!/bin/bash

echo "🚀 Starting Hybrid Scraper Workflow..."

# Ensure we are in the script's directory
cd "$(dirname "$0")" || exit


# 1. Install Dependencies (Just in case)
echo "📦 Checking dependencies..."
pip3 install -r requirements.txt || echo "⚠️ Warning: Pip install failed. Assuming packages are present or handled by another python."
python3 -m playwright install chromium

echo "3. Run Local Scrapers (FPT & MW Only - Parallel)..."
osascript -e 'display notification "Scrapers Running: FPT & MW" with title "Daily Promotion"'
echo "🕷️ Running FPT & MW Scrapers..."
python3 code/1-Apple_FPT_playwright.py
python3 code/2-Apple_MW_playwright.py
osascript -e 'display notification "Scrapers Completed: FPT & MW" with title "Daily Promotion"'
echo "✅ FPT & MW Scrapers Completed."

echo "✅ Hybrid Workflow Complete!"

# 5. Push Results (Data + Code Updates) to GitHub
echo "🚀 Pushing results to GitHub..."

# 5.1 Add Code & Config (Ensure GitHub Action has latest logic)
git add code/
git add .github/


# 5.2 Add Daily Data (Specific files only)
DATE=$(date +%Y-%m-%d)
git add "content/$DATE/1-fpt-$DATE.csv" || echo "⚠️ FPT CSV not found?"
git add "content/$DATE/2-mw-$DATE.csv" || echo "⚠️ MW CSV not found?"

git commit -m "Auto: Update Daily Promotion Data (FPT/MW Local Run) - $(date)" || echo "⚠️ No changes to commit"
git stash
git pull origin main --rebase
git stash pop || echo "⚠️ Auto-merge conflict or nothing to pop. Continuing..."
git push

echo "🎉 Done! Data synced to GitHub."
