import os
import subprocess
import re
from datetime import datetime

# Script mapping configuration (Script Name -> Default Sites.py List Name)
RETAILERS = {
    "scrape_fpt_links.py": "fpt",
    "scrape_cps_links.py": "cps",
    "scrape_hoangha_links.py": "hh",
    "scrape_mw_links.py": "mw",
    "scrape_viettel_links.py": "vt",
    "scrape_ddv_links.py": "ddv"
}

def run_scraper(script_name):
    """Runs a playwright python scraper and captures the stdout lines."""
    print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] Running {script_name}...")
    try:
        # Assuming we are running this inside src/crawlers/utils/
        result = subprocess.run(
            ["python", script_name],
            capture_output=True,
            text=True,
            timeout=1800 # 30 mins max per script
        )
        return result.stdout
    except Exception as e:
        print(f"Execution Error for {script_name}: {e}")
        return ""

def extract_urls(stdout_text):
    """Extracts strings formatted inside list definitions from stdout."""
    # We look for lines containing a URL in quotes
    # e.g., 'https://fptshop.com.vn/...',
    urls = []
    lines = stdout_text.split('\\n')
    for line in lines:
        match = re.search(r"['\"](http[s]?://.*?)['\"]", line)
        if match:
            urls.append(match.group(1))
    return sorted(list(set(urls)))

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sites_path = os.path.join(base_dir, "sites.py")
    
    # Store aggregated links
    compiled_links = {}

    for script, prefix in RETAILERS.items():
        script_path = os.path.join(base_dir, script)
        if not os.path.exists(script_path):
            print(f"Skipping {script} - File not found.")
            continue
            
        stdout = run_scraper(script_path)
        all_urls = extract_urls(stdout)
        
        apple_key = f"{prefix}_urls"
        marshall_key = f"{prefix}_marshall_urls"
        
        compiled_links[apple_key] = []
        compiled_links[marshall_key] = []
        
        for url in all_urls:
            # Routing logic: if URL contains 'marshall', put it in marshall list
            if "marshall" in url.lower():
                compiled_links[marshall_key].append(url)
            else:
                compiled_links[apple_key].append(url)
                
        print(f" -> Found {len(compiled_links[apple_key])} Apple URLs and {len(compiled_links[marshall_key])} Marshall URLs.")

    # Generate Python code for sites.py
    print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] Writing to sites.py...")
    
    with open(sites_path, "w", encoding="utf-8") as f:
        f.write("total_links = {\\n")
        
        for key, url_list in compiled_links.items():
            if not url_list:
                # Don't write empty lists to avoid breaking expectations, or write them empty
                pass
            f.write(f"    '{key}': [\\n")
            for u in url_list:
                f.write(f"        '{u}',\\n")
            f.write("    ],\\n\\n")
            
        f.write("}\\n")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully updated {sites_path}!")

if __name__ == "__main__":
    main()
