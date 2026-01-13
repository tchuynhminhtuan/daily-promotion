import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import pytz

# Configuration
BASE_URL = "https://www.thegioididong.com"
API_URL = "https://www.thegioididong.com/Category/FilterProductBox"

# Brand Configuration (Verified IDs)
# dictionary format: "BrandName": { "CategoryName": {"c": CategoryID, "m": ManufacturerID}, ... }
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
    "OPPO": {
        "Phone": {"c": 42, "m": 1971},
        "Tablet": {"c": 522, "m": 35263},
    },
    "Xiaomi": {
        "Phone": {"c": 42, "m": 2235},
        "Tablet": {"c": 522, "m": 29147},
        "Watch": {"c": 7077, "m": 17197},
    },
    "Vivo": {
        "Phone": {"c": 42, "m": 2236},
    },
    "Realme": {
        "Phone": {"c": 42, "m": 17201},
    },
    "Asus": {
        "Laptop": {"c": 44, "m": 128},
    },
    "HP": {
        "Laptop": {"c": 44, "m": 122},
    },
    "Dell": {
        "Laptop": {"c": 44, "m": 118},
    },
    "Acer": {
        "Laptop": {"c": 44, "m": 119},
    },
    "Lenovo": {
        "Laptop": {"c": 44, "m": 120},
        "Tablet": {"c": 522, "m": 1226},
    },
    "MSI": {
        "Laptop": {"c": 44, "m": 133},
    },
    "Garmin": {
        "Watch": {"c": 7077, "m": 17190},
    },
    "Amazfit": {
        "Watch": {"c": 7077, "m": 19817},
    }
}

# ---------------------------------------------------------
# ⚙️ CONFIGURATION: Set the brand you want to scrape here
# ---------------------------------------------------------
TARGET_BRAND = "Apple" 
# ---------------------------------------------------------

CATEGORIES = BRAND_CONFIGS.get(TARGET_BRAND, {})

def get_vietnam_time():
    """Returns current date in VN format YYYY-MM-DD."""
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d")

def fetch_products_via_api():
    """Fetches all products via pagination loop for the SELECTED BRAND."""
    all_products = []
    
    if not CATEGORIES:
        print(f"❌ No configuration found for brand: {TARGET_BRAND}")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.thegioididong.com"
    }

    print(f"🚀 Starting API Scraper for Brand: {TARGET_BRAND}...")
    
    total_found = 0

    for cat_name, config in CATEGORIES.items():
        print(f"\n📂 Processing Category: {cat_name} (ID: {config['c']}, Manu: {config['m']})")
        page_index = 0
        
        while True:
            payload = {
                "c": config['c'],
                "m": config['m'], 
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
                    print("⚠️ No content returned. Moving to next category.")
                    break

                soup = BeautifulSoup(html_content, 'html.parser')
                products = soup.select('li.item')
                
                if not products:
                    print("⚠️ No valid items found. Next.")
                    break

                batch_count = 0
                for p in products:
                    # 1. Main Attributes
                    main_link = p.select_one('a.main-contain')
                    if not main_link: continue # Skip banners

                    product_id = main_link.get('data-id', "")
                    brand = main_link.get('data-brand', "")
                    category = main_link.get('data-cate', "")
                    
                    name_el = main_link.select_one('h3')
                    name = name_el.text.strip() if name_el else main_link.get('data-name', "Unknown Name")
                    
                    link_suffix = main_link.get('href', '')
                    full_link = BASE_URL + link_suffix if link_suffix.startswith('/') else link_suffix

                    # New Fields Extraction
                    color = main_link.get('data-color', "Unknown")
                    sku = p.get('data-productcode', "")
                    
                    # Specs
                    utility = p.select_one('.utility')
                    specs = utility.text.strip().replace('\n', ', ') if utility else ""
                    
                    # Variants (Storage/Versions)
                    variants_els = p.select('.merge__item')
                    variants = ", ".join([v.text.strip() for v in variants_els]) if variants_els else ""
                    
                    # Image
                    img_el = p.select_one('.item-img img')
                    image_url = img_el.get('data-src') or img_el.get('src') if img_el else ""

                    # Internal System Data (User Requested "Don't miss anything")
                    label_online = p.select_one('.item-txt-online')
                    label_online_txt = label_online.text.strip() if label_online else ""

                    internal_pro_id = main_link.get('data-pro', "")
                    internal_s_code = main_link.get('data-s', "")
                    internal_site_id = main_link.get('data-site', "")
                    
                    # Attributes on the <li> tag itself (parent 'p')
                    internal_maingroup = p.get('data-maingroup', "")
                    internal_subgroup = p.get('data-subgroup', "")
                    internal_type = p.get('data-type', "")
                    internal_vehicle = p.get('data-vehicle', "")
                    internal_ordertype = p.get('data-ordertypeid', "")

                    # 2. Price Logic
                    price_el = p.select_one('.price')
                    raw_price = price_el.text.strip() if price_el else "0"
                    clean_price = ''.join(filter(str.isdigit, raw_price))
                    promo_price = int(clean_price) if clean_price else 0

                    old_price_el = p.select_one('.price-old')
                    raw_old_price = old_price_el.text.strip() if old_price_el else "0"
                    clean_old_price = ''.join(filter(str.isdigit, raw_old_price))
                    listed_price = int(clean_old_price) if clean_old_price else 0

                    if promo_price == 0 and listed_price > 0: promo_price = listed_price
                    if listed_price == 0 and promo_price > 0: listed_price = promo_price

                    # 3. Status & Tags
                    stock_status = "Yes" if promo_price > 0 else "No"
                    
                    installment_el = p.select_one('.item-installment')
                    installment = installment_el.text.strip() if installment_el else ""
                    
                    discount_el = p.select_one('.percent')
                    discount_percent = discount_el.text.strip() if discount_el else ""

                    # 4. Rating
                    vote_txt = p.select_one('.vote-txt b')
                    rating = vote_txt.text.strip() if vote_txt else ""
                    
                    vote_count_el = p.select_one('.vote-count')
                    vote_count = vote_count_el.text.strip() if vote_count_el else ""

                    # 5. Promotions
                    promo_el = p.select_one('.text-gift')
                    promo_text = promo_el.text.strip() if promo_el else ""
                    
                    # Standardize Record
                    record = {
                        "Product_ID": product_id,
                        "SKU": sku,
                        "Product_Name": name,
                        "Brand": brand,
                        "Category": category,
                        "Color": color,
                        "Specs": specs,
                        "Variants": variants,
                        "Ton_Kho": stock_status,
                        "Gia_Niem_Yet": listed_price,
                        "Gia_Khuyen_Mai": promo_price,
                        "Discount_Percent": discount_percent,
                        "Installment": installment,
                        "Rating": rating,
                        "Vote_Count": vote_count,
                        "Date": get_vietnam_time(),
                        "Khuyen_Mai": promo_text,
                        "Thanh_Toan": "", 
                        "Link": full_link,
                        "Image_URL": image_url,
                        "Label_Online": label_online_txt,
                        "Internal_Pro_ID": internal_pro_id,
                        "Internal_S_Code": internal_s_code,
                        "Internal_Maingroup": internal_maingroup,
                        "Internal_Subgroup": internal_subgroup,
                        "Internal_Type": internal_type,
                        "Internal_Vehicle": internal_vehicle,
                        "Internal_OrderType": internal_ordertype,
                        "screenshot_name": "API_Scrape"
                    }
                    # ---------------------------------------------------------
                    # VARIANT HANDLING
                    # ---------------------------------------------------------
                    # 1. Add Main Record (Already done above, but need to ensure it has the correct Variant Name)
                    # The main record corresponds to the 'active' variant usually.
                    
                    # 2. Find ALL variants (including the active one) to ensure we get all SKUs/IDs
                    # Note: The APIs often return the "Active" item as the main <li>.
                    #       The .merge__item list contains ALL options including the active one.
                    
                    variants_list = p.select('.merge__item')
                    
                    # If NO variants list is found, usage existing record as unique
                    if not variants_list:
                        all_products.append(record)
                        batch_count += 1
                    else:
                        # If variants exist, we iterate them to create rows
                        # We try to match the Main Record's ID to one of them to fill in the Price
                        
                        has_added_main = False
                        
                        for v in variants_list:
                            v_text = v.text.strip()
                            v_id = v.get('data-id')
                            v_url = v.get('data-url', '')
                            
                            # Construct Name
                            # Logic: Remove ANY other variant text from the name, then ensure current variant is present
                            base_name = name
                            for clean_v in variants_list:
                                clean_txt = clean_v.text.strip()
                                # Remove "256GB" if we are adding "512GB"
                                if clean_txt in base_name:
                                    base_name = base_name.replace(clean_txt, "").strip()
                            
                            # Clean up double spaces
                            base_name = " ".join(base_name.split())
                            full_name = f"{base_name} {v_text}"
                                
                            # Determine Price & Stock
                            # If this variant ID matches the Main Product ID (from <li>), use the main price
                            is_main_variant = (v_id == product_id)
                            
                            if is_main_variant:
                                # Update the MAIN record with the specific variant name if needed
                                record["Product_Name"] = full_name
                                record["Variants"] = v_text # Specific variant
                                all_products.append(record)
                                has_added_main = True
                            else:
                                # Create a NEW record for this variant
                                # We lack specific Price/SKU for inactive variants in this view.
                                # PROPOSAL: Use 0 for price to indicate "Check Link".
                                
                                new_rec = record.copy()
                                new_rec["Product_ID"] = v_id
                                new_rec["Product_Name"] = full_name
                                new_rec["Variants"] = v_text
                                new_rec["Gia_Niem_Yet"] = 0
                                new_rec["Gia_Khuyen_Mai"] = 0
                                new_rec["Ton_Kho"] = "Check Link"
                                new_rec["SKU"] = "" # Unknown for inactive
                                new_rec["Link"] = full_link # Same link usually, or construct specific?
                                
                                all_products.append(new_rec)
                            
                            batch_count += 1

                print(f"✅ Got {batch_count} items.")
                total_found += batch_count
                
                page_index += 1
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

    date_str = get_vietnam_time()
    save_dir = f"content/{date_str}"
    os.makedirs(save_dir, exist_ok=True)
    
    # Filename now includes the brand (e.g. 2-mw-apple-2026-01-13-api.csv)
    filename = f"{save_dir}/2-mw-{TARGET_BRAND.lower()}-{date_str}-api.csv"
    
    df = pd.DataFrame(data)
    
    # Extended Column List
    cols = ["Product_ID", "SKU", "Product_Name", "Brand", "Category", 
            "Color", "Specs", "Variants",
            "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", 
            "Discount_Percent", "Installment", "Rating", "Vote_Count",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Image_URL", 
            "Label_Online", "Internal_Pro_ID", "Internal_S_Code", 
            "Internal_Maingroup", "Internal_Subgroup", 
            "Internal_Type", "Internal_Vehicle", "Internal_OrderType",
            "screenshot_name"]
            
    for c in cols:
        if c not in df.columns: df[c] = ""
        
    df = df[cols]
    
    df.to_csv(filename, index=False)
    print(f"💾 Saved {len(df)} records to: {filename}")

if __name__ == "__main__":
    data = fetch_products_via_api()
    save_to_csv(data)
