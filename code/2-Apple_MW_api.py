import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import pytz

# Configuration
BASE_URL = "https://www.thegioididong.com"
API_URL = "https://www.thegioididong.com/Category/FilterProductBox"

# Category IDs (Found via inspection: Apple=80, Mobile=42)
CATEGORY_ID = 42
MANUFACTURER_ID = 80 # Apple

def get_vietnam_time():
    """Returns current date in VN format YYYY-MM-DD."""
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d")

def fetch_products_via_api():
    """Fetches all products via pagination loop."""
    all_products = []
    page_index = 0
    total_found = 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.thegioididong.com/dtdd-apple-iphone",
        "Origin": "https://www.thegioididong.com"
    }

    print(f"🚀 Starting API Scraper for TGDĐ (Apple)...")

    while True:
        payload = {
            "c": CATEGORY_ID,
            "m": MANUFACTURER_ID, 
            "o": 13, # Highlights sorting
            "pi": page_index,
            "IsParentCate": "False",
            "IsShowCompare": "True",
            "prevent": "true"
        }

        try:
            print(f"    Requesting Page {page_index}...", end=" ", flush=True)
            response = requests.post(API_URL, data=payload, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Failed (Status {response.status_code})")
                break

            data = response.json()
            html_content = data.get("listproducts", "")
            
            if not html_content:
                print("⚠️ No content returned. Stopping.")
                break

            soup = BeautifulSoup(html_content, 'html.parser')
            products = soup.select('li.item')
            
            if not products:
                print("⚠️ No valid product items found in HTML. Stopping.")
                break

            batch_count = 0
            for p in products:
                # 1. Product Name & Link
                main_link = p.select_one('a.main-contain')
                if not main_link: continue # Skip banners

                name_el = main_link.select_one('h3')
                name = name_el.text.strip() if name_el else main_link.get('data-name', "Unknown Name")
                
                # Filter non-Apple if API leeks others (sanity check)
                # if "iPhone" not in name: continue 

                link_suffix = main_link.get('href', '')
                full_link = BASE_URL + link_suffix if link_suffix.startswith('/') else link_suffix

                # 2. Price
                price_el = p.select_one('.price')
                # Sometimes price is just a number text, sometimes it has ₫
                raw_price = price_el.text.strip() if price_el else "0"
                
                # Cleanup Price: "18.990.000₫" -> 18990000
                clean_price = ''.join(filter(str.isdigit, raw_price))
                promo_price = int(clean_price) if clean_price else 0

                # Old Price (Listed Price)
                old_price_el = p.select_one('.price-old')
                raw_old_price = old_price_el.text.strip() if old_price_el else "0"
                clean_old_price = ''.join(filter(str.isdigit, raw_old_price))
                listed_price = int(clean_old_price) if clean_old_price else 0

                if promo_price == 0 and listed_price > 0:
                    promo_price = listed_price # Fallback
                
                if listed_price == 0 and promo_price > 0:
                    listed_price = promo_price # Fallback

                # 3. Stock Status
                # "Mua ngay" often implies stock.
                # In list view, logic is simpler: if price > 0 usually stock yes.
                stock_status = "Yes" if promo_price > 0 else "No"
                
                # 4. Promotions (Text)
                # In list view, promo text is usually in .promotions or .gift-txt
                promo_text = ""
                promo_el = p.select_one('.text-gift') # Example selector for list view promo
                if promo_el:
                    promo_text = promo_el.text.strip()
                
                # Standardize Record
                record = {
                    "Product_Name": name,
                    "Color": "Unknown", # List view rarely has specific color unless title says so
                    "Ton_Kho": stock_status,
                    "Gia_Niem_Yet": listed_price,
                    "Gia_Khuyen_Mai": promo_price,
                    "Date": get_vietnam_time(),
                    "Khuyen_Mai": promo_text,
                    "Thanh_Toan": "", # List view doesn't usually show detailed payment promo
                    "Link": full_link,
                    "screenshot_name": "API_Scrape"
                }
                all_products.append(record)
                batch_count += 1

            print(f"✅ Got {batch_count} items.")
            total_found += batch_count
            
            # Pagination Check
            # If batch returned fewer than expected (usually 20-30), end might be reached.
            # OR we can trust the 'total' field if reliable.
            # Safest is loop until empty.
            
            page_index += 1
            # Safety break to avoid infinite loop
            if page_index > 20: 
                print("⚠️ Safety Limit Reached (20 pages).")
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")
            break
            
    return all_products

def save_to_csv(data):
    if not data:
        print("⚠️ No data to save.")
        return

    # Create directory if needed
    date_str = get_vietnam_time()
    save_dir = f"content/{date_str}"
    os.makedirs(save_dir, exist_ok=True)
    
    filename = f"{save_dir}/2-mw-{date_str}-api.csv"
    
    df = pd.DataFrame(data)
    
    # Reorder columns to match existing format
    cols = ["Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", 
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"]
            
    # Add missing cols with defaults if needed
    for c in cols:
        if c not in df.columns: df[c] = ""
        
    df = df[cols]
    
    df.to_csv(filename, index=False)
    print(f"💾 Saved {len(df)} records to: {filename}")

if __name__ == "__main__":
    data = fetch_products_via_api()
    save_to_csv(data)
