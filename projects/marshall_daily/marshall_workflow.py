import os
import sys
import asyncio
import shutil
from datetime import datetime
import pytz
import importlib.util

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
CODE_DIR = os.path.join(ROOT_DIR, "code")
PROJECT_CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

# Add CODE_DIR to sys.path so we can import utils.sites
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

# Set the output path for core scrapers to the local project content directory
os.environ["BASE_OUTPUT_PATH"] = PROJECT_CONTENT_DIR

from utils.sites import total_links

def get_date_str():
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(local_tz).strftime('%Y-%m-%d')

async def run_core_scraper(script_name, marshall_key, core_key):
    print(f"\n🚀 Running {script_name} for {marshall_key}...")
    
    # 1. Monkeypatch total_links to point Marshall URLs to the expected core key
    original_urls = total_links.get(core_key)
    marshall_urls = total_links.get(marshall_key, [])
    
    if not marshall_urls:
        print(f"⚠️ No URLs found for {marshall_key}")
        return

    # Temporarily override
    total_links[core_key] = marshall_urls
    
    # 2. Dynamic Import
    script_path = os.path.join(CODE_DIR, script_name)
    spec = importlib.util.spec_from_file_location("scraper_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 3. Run main()
    if hasattr(module, 'main'):
        try:
            # Check if it's async
            if asyncio.iscoroutinefunction(module.main):
                await module.main()
            else:
                module.main()
        except Exception as e:
            print(f"❌ Error running {script_name}: {e}")
    else:
        print(f"❌ No main() found in {script_name}")

    # 4. Restore
    total_links[core_key] = original_urls

async def workflow():
    await run_core_scraper("1-Apple_FPT_playwright.py", "fpt_marshall_urls", "fpt_urls")
    await run_core_scraper("2-Apple_MW_playwright.py", "mw_marshall_urls", "mw_urls")
    await run_core_scraper("6-Apple_CPS_playwright.py", "cps_marshall_urls", "cps_urls")

if __name__ == "__main__":
    asyncio.run(workflow())
