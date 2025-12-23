#!/bin/bash

echo "🚀 Starting Hybrid Scraper Workflow..."

# 1. Install Dependencies (Just in case)
echo "📦 Checking dependencies..."
pip3 install -r requirements.txt || echo "⚠️ Warning: Pip install failed. Assuming packages are present or handled by another python."
python3 -m playwright install chromium

# 2. Pull latest data from GitHub (The other 4 scrapers)
echo "⬇️ Pulling latest data from GitHub..."

# SAFETY: Auto-backup local Cloud files (3,4,5,6) to prevent Merge Conflicts if accidentally run locally
DATE=$(date +%Y-%m-%d)
for i in 3-viettel 4-hoangha 5-ddv 6-cps; do
    FILE="content/$DATE/$i-$DATE.csv"
    if [ -f "$FILE" ] && git status --porcelain | grep -q "$FILE"; then
        mv "$FILE" "$FILE.local_backup"
        echo "⚠️  Backed up $FILE to $FILE.local_backup (Preventing Conflict)"
    fi
done

git stash
git pull origin main --rebase
git stash pop || echo "⚠️ Auto-merge conflict or nothing to pop. Continuing..."

# 3. Run Local Scrapers (FPT & MW Only)
# echo "🕷️ Running FPT Scraper..."
# python3 code/1-Apple_FPT_playwright.py

# echo "🕷️ Running Mobile World Scraper..."
# python3 code/2-Apple_MW_playwright.py

# echo "🕷️ Running Viettel Store Scraper..."
# python3 code/3-Apple_Viettel_playwright.py

# echo "🕷️ Running Hoang Ha Mobile Scraper..."
# python3 code/4-Apple_HoangHa_playwright.py

# echo "🕷️ Running Di Dong Viet Scraper..."
# python3 code/5-Apple_DDV_playwright.py

# echo "🕷️ Running CellphoneS Scraper..."
# python3 code/6-Apple_CPS_playwright.py

# 4. Generate Final Report
echo "📊 Generating Final Report..."
python3 code/generate_report.py

echo "✅ Hybrid Workflow Complete!"

# 5. Push Results to GitHub
echo "🚀 Pushing results to GitHub..."
git add content/
git add docs/index.html
git commit -m "Auto: Update Daily Promotion Data & Report (Hybrid Run)" || echo "⚠️ No changes to commit"
git stash
git pull origin main --rebase
git stash pop || echo "⚠️ Auto-merge conflict or nothing to pop. Continuing..."
git push

echo "🎉 Done! Data synced to GitHub."
