import requests
import pandas as pd
import os
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import time

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
TARGET_BRAND = "Apple"  # Change this to switch brands (e.g. "Samsung", "Xiaomi")

# Brand Configuration (Verified IDs)
BRAND_CONFIGS = {
    "Apple": {
        "iPhone": {"c": 42, "m": 80},
        "MacBook": {"c": 44, "m": 203},
        "iPad": {"c": 522, "m": 1028},
        "Watch": {"c": 7077, "m": 17188},
    },
    "Samsung": {
        "Phone": {"c": 42, "m": 2},
        "Tablet": {"c": 522, "m": 1101},
        "Watch": {"c": 7077, "m": 17189},
    },
    # ... (Keep other brands if needed, but focusing on Apple for now)
}

API_URL = "https://www.thegioididong.com/Category/FilterProductBox"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.thegioididong.com",
    "Referer": "https://www.thegioididong.com"
}

def get_vietnam_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d')

def crawl_product_colors(product_url):
    """
    Fetches the product detail page and extracts all color options.
    Returns a list of dicts: [{'Color': '...', 'SKU': '...', 'Active': True/False}]
    """
    try:
        # Respectful delay
        time.sleep(0.5) 
        
        print(f"      🕷️ Crawling: {product_url}")
        resp = requests.get(product_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"      ⚠️ Failed to load page: {resp.status_code}")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find color elements
        # Selector based on debug: .box03.color .item
        colors = []
        
        # Strategy 1: .box03.color
        color_box = soup.select_one('.box03.color')
        if color_box:
            items = color_box.select('.item')
            for item in items:
                color_name = item.get_text(strip=True)
                sku = item.get('data-code', '') # SKU specific to color
                is_active = 'act' in item.get('class', [])
                
                # Construct specific link if href exists
                href = item.get('href', '')
                specific_link = f"https://www.thegioididong.com{href}" if href.startswith('/') else href
                
                colors.append({
                    "Color": color_name,
                    "SKU": sku,
                    "Link_Color": specific_link,
                    "Is_Active_Color": is_active
                })
        
        # EXTRACT DETAIL PAGE PRICE
        # Selector: .bs_price strong (Promo) or .box-price-present
        crawled_price = 0
        price_el = soup.select_one('.bs_price strong') or soup.select_one('.box-price-present')
        if price_el:
            txt = price_el.get_text(strip=True)
            digits = ''.join(filter(str.isdigit, txt))
            if digits: crawled_price = int(digits)
            
        return colors, crawled_price

    except Exception as e:
        print(f"      ❌ Error crawling details: {e}")
        return [], 0

def fetch_products_deep_crawl(brand_name):
    timestamp = get_vietnam_time()
    all_products = []
    
    config = BRAND_CONFIGS.get(brand_name)
    if not config:
        print(f"❌ Brand '{brand_name}' not found in configuration.")
        return []

    print(f"🚀 Starting DEEP CRAWL Scraper for Brand: {brand_name}...")
    
    for category, params in config.items():
        print(f"\n📂 Processing Category: {category} (ID: {params['c']}, Manu: {params['m']})")
        
        page_idx = 0
        while True:
            payload = {
                "c": params['c'],
                "m": params['m'],
                "o": 13, # Sort by selling (banchay)
                "pi": page_idx,
                "IsParentCate": "False",
                "IsShowCompare": "True",
                "prevent": "true"
            }
            
            print(f"    Requesting List Page {page_idx}...")
            resp = requests.post(API_URL, data=payload, headers=HEADERS)
            
            try:
                data = resp.json()
                html = data.get('listproducts', '')
            except:
                print("    ⚠️ Failed to parse API JSON.")
                break
                
            if not html:
                print("    ⚠️ No content returned. Moving to next category.")
                break
                
            soup = BeautifulSoup(html, 'html.parser')
            products = soup.select('li.item')
            
            if not products:
                print("    ⚠️ No products found in HTML.")
                break
                
            print(f"    ✅ Found {len(products)} products in list. Beginning Deep Crawl...")
            
            for p in products:
                # ---------------------------------------------------------
                # 1. EXTRACT BASE DATA (Fast)
                # ---------------------------------------------------------
                # Basic parsing same as api.py
                main_link = p.select_one('a.main-contain')
                if not main_link: continue

                product_id = p.get('data-id')
                name = main_link.get('data-name')
                brand = main_link.get('data-brand')
                
                link_suffix = main_link.get('href', '')
                # Ensure complete URL
                base_url = "https://www.thegioididong.com" 
                full_link = base_url + link_suffix if link_suffix.startswith('/') else link_suffix

                # Pricing (Base)
                price_el = p.select_one('.price')
                raw_price = price_el.text.strip() if price_el else "0"
                clean_price = ''.join(filter(str.isdigit, raw_price))
                promo_price = int(clean_price) if clean_price else 0
                
                old_price_el = p.select_one('.price-old')
                if old_price_el:
                    clean_old = ''.join(filter(str.isdigit, old_price_el.text.strip()))
                    listed_price = int(clean_old) if clean_old else 0
                else:
                    listed_price = 0
                    
                if promo_price == 0 and listed_price > 0: promo_price = listed_price
                if listed_price == 0 and promo_price > 0: listed_price = promo_price
                
                # Internal Data
                label_online = p.select_one('.item-txt-online')
                label_online_txt = label_online.text.strip() if label_online else ""
                
                # Full Field Extraction (Sync with api.py)
                color_default = main_link.get('data-color', "Unknown")
                sku_default = p.get('data-productcode', "")
                
                utility = p.select_one('.utility')
                specs = utility.text.strip().replace('\n', ', ') if utility else ""
                
                # Variants String (for reference)
                variants_els = p.select('.merge__item')
                variants_str = ", ".join([v.text.strip() for v in variants_els]) if variants_els else ""
                
                # Image
                img_el = p.select_one('.item-img img')
                image_url = img_el.get('data-src') or img_el.get('src') if img_el else ""
                
                # Ratings
                rating_el = p.select_one('.vote-txt')
                rating = ""
                vote_count = ""
                if rating_el:
                    rating_txt = rating_el.text.strip() # e.g. "4.5 (10)" or just empty
                    if rating_el.find('b'):
                         rating = rating_el.find('b').text.strip()
                    # Vote count often inside 'Rating' logic or separate, keeping simple extraction
                    vote_count = rating_txt # Placeholder as api.py logic was similar
                
                # Installment
                pay_el = p.select_one('.lb-tragop')
                installment = pay_el.text.strip() if pay_el else ""
                
                # Discount
                disc_el = p.select_one('.box-p')
                discount_percent = ""
                if disc_el:
                    d_txt = disc_el.text.strip()
                    if '%' in d_txt: discount_percent = d_txt

                # Internal IDs
                internal_pro_id = main_link.get('data-pro', "")
                internal_s_code = main_link.get('data-s', "")
                internal_maingroup = p.get('data-maingroup', "")
                internal_subgroup = p.get('data-subgroup', "")
                internal_type = p.get('data-type', "")
                internal_vehicle = p.get('data-vehicle', "")
                internal_ordertype = p.get('data-ordertypeid', "")

                # Helper to process a single "Capacity Variant"
                def process_capacity_variant(v_element, is_main_capacity):
                    # Determine Capacity Name
                    if is_main_capacity:
                         final_name = name
                    else:
                        v_text = v_element.text.strip()
                        base_name_clean = name
                        for cln in variants_els:
                            cln_txt = cln.text.strip()
                            if cln_txt in base_name_clean:
                                base_name_clean = base_name_clean.replace(cln_txt, "").strip()
                        base_name_clean = " ".join(base_name_clean.split())
                        final_name = f"{base_name_clean} {v_text}"
                    
                    if is_main_capacity:
                        cap_link = full_link
                        cap_id = product_id
                        cap_price = promo_price 
                        stock = "Yes"
                    else:
                        cap_suffix = v_element.get('data-url', '')
                        if len(cap_suffix) > 2:
                            cap_link = base_url + cap_suffix if cap_suffix.startswith('/') else cap_suffix
                        else:
                            cap_link = full_link 
                            
                        cap_id = v_element.get('data-id')
                        cap_price = 0 
                        stock = "Check Link"
                    
                    # DEEP CRAWL
                    color_options, detail_price = crawl_product_colors(cap_link)
                    
                    if not color_options:
                        color_options = [{
                            "Color": color_default, 
                            "SKU": sku_default,
                            "Link_Color": cap_link,
                            "Is_Active_Color": True
                        }]
                    
                    for color_opt in color_options:
                        # Logic (STRICT MODE)
                        if color_opt['Is_Active_Color']:
                            final_price = detail_price if detail_price > 0 else cap_price
                            final_stock = stock
                            final_listed = listed_price
                        else:
                            final_price = 0
                            final_stock = "Check Link"
                            final_listed = 0 
                             
                        record = {
                            "Product_ID": cap_id, 
                            "SKU": color_options[0]['SKU'] if color_opt['Is_Active_Color'] else color_opt['SKU'], 
                            "Product_Name": final_name,
                            "Brand": brand,
                            "Category": category,
                            "Color": color_opt['Color'], 
                            "Specs": specs,
                            "Variants": variants_str,
                            
                            "Ton_Kho": final_stock,
                            "Gia_Niem_Yet": final_listed,
                            "Gia_Khuyen_Mai": final_price, 
                            "Discount_Percent": discount_percent,
                            "Installment": installment,
                            "Rating": rating,
                            "Vote_Count": vote_count,
                            
                            "Date": timestamp,
                            "Khuyen_Mai": "", # Todo: Promo text
                            "Thanh_Toan": "",
                            "Link": color_opt['Link_Color'] or cap_link,
                            "Image_URL": image_url,
                            
                            "Label_Online": label_online_txt,
                            "Internal_Pro_ID": internal_pro_id,
                            "Internal_S_Code": internal_s_code,
                            "Internal_Maingroup": internal_maingroup,
                            "Internal_Subgroup": internal_subgroup,
                            "Internal_Type": internal_type,
                            "Internal_Vehicle": internal_vehicle,
                            "Internal_OrderType": internal_ordertype,
                            
                            "screenshot_name": "Deep_Crawl"
                        }
                        
                        # Add extra logic for SKU (if crawled)
                        if color_opt['SKU']: record['SKU'] = color_opt['SKU']
                        
                        all_products.append(record)

                # Loop through Capacities
                if not variants_els:
                    process_capacity_variant(p, True)
                else:
                    for v in variants_els:
                         v_id = v.get('data-id')
                         is_main = (v_id == product_id)
                         process_capacity_variant(v, is_main)
            
            page_idx += 1
            if len(products) < 5: break 
            
    return all_products

def save_to_csv(data, filename):
    if not data:
        print("⚠️ No data to save.")
        return

    df = pd.DataFrame(data)
    
    # Exact same column list requested by user
    cols = ["Product_ID", "SKU", "Product_Name", "Brand", "Category", 
            "Color", "Specs", "Variants",
            "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", 
            "Discount_Percent", "Installment", "Rating", "Vote_Count",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Image_URL", 
            "Label_Online", "Internal_Pro_ID", "Internal_S_Code", 
            "Internal_Maingroup", "Internal_Subgroup", 
            "Internal_Type", "Internal_Vehicle", "Internal_OrderType",
            "screenshot_name"]
            
    # Reorder if columns exist
    final_cols = [c for c in cols if c in df.columns]
    remaining = [c for c in df.columns if c not in cols]
    
    df = df[final_cols + remaining]
    
    # Ensure dir exists
    output_path = f"content/{get_vietnam_time()}/{filename}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"💾 Saved {len(df)} records to: {output_path}")

if __name__ == "__main__":
    data = fetch_products_deep_crawl(TARGET_BRAND)
    filename = f"3-deep-{TARGET_BRAND.lower()}-{get_vietnam_time()}.csv"
    save_to_csv(data, filename)
