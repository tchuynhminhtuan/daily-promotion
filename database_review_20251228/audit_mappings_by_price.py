
import sqlite3
import statistics

DB_FILE = "apple_prices.db"

def audit_prices():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print("🔍 Auditing Mappings using Price Logic...")
    
    # 1. Get all prices grouped by Normalized Key
    c.execute('''
        SELECT m.normalized_key, p.price, p.raw_name, p.retailer, p.date
        FROM prices p
        JOIN mappings m ON p.raw_name = m.raw_name
        WHERE p.price > 0 AND m.normalized_key IS NOT NULL
    ''')
    rows = c.fetchall()
    
    # Organize by Key
    grouped = {}
    for key, price, raw, retailer, date in rows:
        if key not in grouped: grouped[key] = []
        grouped[key].append({
            'price': price,
            'raw': raw,
            'retailer': retailer,
            'date': date
        })
        
    suspects = []
    
    print(f"📊 Analyzing {len(grouped)} Product Groups...")
    
    for key, items in grouped.items():
        if len(items) < 3: continue # Need reliable baseline
        
        prices = [x['price'] for x in items]
        median_price = statistics.median(prices)
        
        if median_price < 100000: continue # Skip accessories/junk if median is tiny
        
        # Thresholds: 
        # Low: 50% of Median (e.g. Accessory mapped to Product?)
        # High: 180% of Median (e.g. Pro Max mapped to Regular?)
        low_thresh = median_price * 0.5
        high_thresh = median_price * 1.8
        
        for item in items:
            p = item['price']
            if p < low_thresh or p > high_thresh:
                deviation = "LOW" if p < low_thresh else "HIGH"
                suspects.append({
                    'key': key,
                    'raw': item['raw'],
                    'price': p,
                    'median': median_price,
                    'dev': deviation,
                    'retailer': item['retailer']
                })
    
    # Report Findings
    if not suspects:
        print("✅ No significant price anomalies found.")
        return

    print(f"\n⚠️  Found {len(suspects)} Potential Mis-Mappings (Price Outliers):\n")
    
    # Sort by Deviation Severity (Ratio)
    suspects.sort(key=lambda x: abs(x['price'] - x['median']), reverse=True)
    
    deduped_suspects = {} # Dedupe by raw_name to avoid spamming daily records
    for s in suspects:
        deduped_suspects[s['raw']] = s
        
    for raw, s in deduped_suspects.items():
        print(f"❌ '{raw}' ({s['retailer']})")
        print(f"   Mapped To: {s['key']}")
        print(f"   Price: {s['price']:,} ₫  (Median: {s['median']:,} ₫)")
        print(f"   Deviation: {s['dev']} ({(s['price']/s['median']*100):.0f}%)")
        print("-" * 50)

if __name__ == "__main__":
    audit_prices()
