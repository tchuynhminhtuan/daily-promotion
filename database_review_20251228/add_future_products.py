
import json
import shutil

DB_FILE = "apple_products_db.json"
BACKUP_FILE = "apple_products_db.json.bak"

NEW_PRODUCTS = {
    "iPhone 16": {"Family": "iPhone", "Model": "iPhone 16", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPhone 16 Plus": {"Family": "iPhone", "Model": "iPhone 16 Plus", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPhone 16 Pro": {"Family": "iPhone", "Model": "iPhone 16 Pro", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB", "1TB"]}},
    "iPhone 16 Pro Max": {"Family": "iPhone", "Model": "iPhone 16 Pro Max", "Specs": {"Dung Lượng": ["256GB", "512GB", "1TB"]}},
    "iPhone 16e": {"Family": "iPhone", "Model": "iPhone 16e", "Specs": {"Dung Lượng": ["128GB", "256GB"]}},
    "iPhone 17": {"Family": "iPhone", "Model": "iPhone 17", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPhone Air": {"Family": "iPhone", "Model": "iPhone Air", "Specs": {"Dung Lượng": ["128GB", "256GB"]}},
    
    "iPad (A16) Wi-Fi": {"Family": "iPad", "Model": "iPad (A16) Wi-Fi", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPad (A16) Wi-Fi + Cellular": {"Family": "iPad", "Model": "iPad (A16) Wi-Fi + Cellular", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPad mini (A17 Pro)": {"Family": "iPad", "Model": "iPad mini (A17 Pro)", "Specs": {"Dung Lượng": ["128GB", "256GB", "512GB"]}},
    "iPad Pro 11 inch (M5)": {"Family": "iPad", "Model": "iPad Pro 11 inch (M5)", "Specs": {"Dung Lượng": ["256GB", "512GB", "1TB", "2TB"]}},
    "iPad Pro 13 inch (M5)": {"Family": "iPad", "Model": "iPad Pro 13 inch (M5)", "Specs": {"Dung Lượng": ["256GB", "512GB", "1TB", "2TB"]}},

    "Apple Watch Series 10": {"Family": "Apple Watch", "Model": "Apple Watch Series 10", "Specs": {"Kích Thước": ["42", "46"]}},
    "Apple Watch Series 11": {"Family": "Apple Watch", "Model": "Apple Watch Series 11", "Specs": {"Kích Thước": ["42", "46"]}},
    "Apple Watch SE 3": {"Family": "Apple Watch", "Model": "Apple Watch SE 3", "Specs": {"Kích Thước": ["40", "44"]}},
    "Apple Watch Ultra 3": {"Family": "Apple Watch", "Model": "Apple Watch Ultra 3", "Specs": {"Kích Thước": ["49"]}},
    
    "MacBook Pro (14 inch, M5)": {"Family": "Mac", "Model": "MacBook Pro (14 inch, M5)", "Specs": {"Bộ Nhớ": ["16GB", "24GB", "32GB"], "Dung Lượng": ["512GB", "1TB"]}},
    "MacBook Pro (16 inch, M5)": {"Family": "Mac", "Model": "MacBook Pro (16 inch, M5)", "Specs": {"Bộ Nhớ": ["24GB", "36GB", "48GB"], "Dung Lượng": ["512GB", "1TB"]}},
    "Mac mini (2024)": {"Family": "Mac", "Model": "Mac mini (2024)", "Specs": {"Chip": ["M4", "M4 Pro"], "Bộ Nhớ": ["16GB", "24GB", "32GB", "48GB"], "Dung Lượng": ["256GB", "512GB", "1TB"]}},
    "iMac (24 inch, 2024)": {"Family": "Mac", "Model": "iMac (24 inch, 2024)", "Specs": {"Chip": ["M4"], "Bộ Nhớ": ["16GB", "24GB", "32GB"], "Dung Lượng": ["256GB", "512GB"]}}
}

def add_products():
    print(f"🔧 Injecting Future Products into {DB_FILE}...")
    shutil.copy(DB_FILE, BACKUP_FILE)
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    count = 0
    for key, item in NEW_PRODUCTS.items():
        data[key] = item
        count += 1
        print(f"  Processed: {key}")
            
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Added {count} new products.")

if __name__ == "__main__":
    add_products()
