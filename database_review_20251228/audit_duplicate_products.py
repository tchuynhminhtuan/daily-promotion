
import sqlite3
import statistics
from difflib import SequenceMatcher

DB_FILE = "apple_prices.db"

def similar_name(a, b):
    return SequenceMatcher(None, a, b).ratio()

def audit_duplicates():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print("🔍 Auditing for Duplicate Products (Split Keys)...")
    
    # 1. Get stats per Normalized Key
    c.execute('''
        SELECT m.normalized_key, p.price
        FROM prices p
        JOIN mappings m ON p.raw_name = m.raw_name
        WHERE p.price > 0 AND m.normalized_key IS NOT NULL
    ''')
    rows = c.fetchall()
    
    # Group Prices
    key_stats = {}
    for key, price in rows:
        if key not in key_stats: key_stats[key] = []
        key_stats[key].append(price)
        
    # Calculate Medians
    stats = []
    for key, prices in key_stats.items():
        if len(prices) < 2: continue
        median = statistics.median(prices)
        stats.append({
            'key': key,
            'median': median,
            'count': len(prices)
        })
        
    print(f"📊 Analyzing {len(stats)} Unique Product Keys for overlap...")
    
    # Compare Pairwise (Optimized: Sort by Price first to limit search window)
    stats.sort(key=lambda x: x['median'])
    
    potential_dupes = []
    
    for i in range(len(stats)):
        current = stats[i]
        # Look ahead at items with similar price
        for j in range(i + 1, len(stats)):
            compare = stats[j]
            
            # Price Diff %
            price_diff = abs(current['median'] - compare['median']) / current['median']
            
            if price_diff > 0.05: # Stop if prices diverge > 5%
                break
                
            # If prices are super close, check Name Similarity
            name_sim = similar_name(current['key'], compare['key'])
            
            # Heuristic: 
            # If Price is < 2% diff AND Name is > 60% similar -> Suspect
            if price_diff < 0.02 and name_sim > 0.6:
                potential_dupes.append((current, compare, price_diff, name_sim))

    if not potential_dupes:
        print("✅ No obvious duplicate keys found.")
        return

    print(f"\n⚠️  Found {len(potential_dupes)} Pairs of Potential Split Products:\n")
    
    # Sort by Similarity
    potential_dupes.sort(key=lambda x: x[3], reverse=True)
    
    for d in potential_dupes[:50]: # Show top 50
        item1, item2, pdiff, nsim = d
        print(f"🔹 Pair:")
        print(f"   1. {item1['key']} (Median: {item1['median']:,} ₫)")
        print(f"   2. {item2['key']} (Median: {item2['median']:,} ₫)")
        print(f"   diff: {pdiff*100:.1f}% | Sim: {nsim*100:.0f}%")
        print("-" * 40)

if __name__ == "__main__":
    audit_duplicates()
