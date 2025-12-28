import os
import sys
import subprocess
from datetime import datetime
import pytz

# Add root directory to sys.path to import utils.sites
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from code.utils.sites import total_links

def run_scraper(script_path, url_key):
    urls = total_links.get(url_key, [])
    if not urls:
        print(f"No URLs found for {url_key}")
        return

    print(f"--- Running {os.path.basename(script_path)} for {len(urls)} URLs ---")
    for url in urls:
        print(f"Scraping: {url}")
        # Use env variable to pass specific URL to core scrapers
        env = os.environ.copy()
        env["SPECIFIC_URL"] = url
        # Optional: Disable screenshots per implementation plan for speed
        env["TAKE_SCREENSHOT"] = "False"
        
        try:
            subprocess.run(["python3", script_path], env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error scraping {url}: {e}")

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../code"))
    
    # 1. FPT Marshall
    run_scraper(os.path.join(base_dir, "1-Apple_FPT_playwright.py"), "fpt_marshall_urls")
    
    # 2. MW Marshall
    run_scraper(os.path.join(base_dir, "2-Apple_MW_playwright.py"), "mw_marshall_urls")
    
    # 3. CPS Marshall
    run_scraper(os.path.join(base_dir, "6-Apple_CPS_playwright.py"), "cps_marshall_urls")

if __name__ == "__main__":
    main()
