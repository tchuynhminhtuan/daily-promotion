import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'catalog/price_history.db'

def analyze_prices():
    conn = sqlite3.connect(DB_PATH)
    
    # query last 30 days
    query = """
    SELECT 
        p.key as product_key,
        p.name as product_name,
        ph.date,
        ph.retailer,
        ph.price,
        ph.variant,
        ph.source
    FROM price_history ph
    JOIN products p ON ph.product_id = p.id
    WHERE ph.date >= date('now', '-30 days')
    AND length(ph.date) = 10
    AND ph.price > 0
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No data found in the last 30 days.")
        return

    df['date'] = pd.to_datetime(df['date'])
    
    # Fill missing retailer from source
    def get_retailer(source):
        if not source: return 'Unknown'
        if 'fpt' in source: return 'FPT Shop'
        if 'mw' in source: return 'Mobile World'
        if 'cps' in source: return 'CellphoneS'
        if 'ddv' in source: return 'Di Dong Viet'
        if 'hoangha' in source: return 'HoangHa Mobile'
        if 'viettel' in source: return 'Viettel Store'
        return 'Unknown'
        
    df['retailer'] = df['source'].apply(get_retailer)
    
    # Max price filter to remove potential anomalies (e.g. 0 or very high errors)
    df = df[df['price'] > 100000] # > 100k
    
    print(f"Loaded {len(df)} records from {df['date'].min().date()} to {df['date'].max().date()}\n")
    print(df.head())
    print("\nData Types:")
    print(df.dtypes)
    print("\nUnique Product Keys:")
    print(df['product_key'].unique()[:20])
    print(f"Total Unique Keys: {df['product_key'].nunique()}")
    print("\nSample Retailers:")
    print(df['retailer'].unique())
    
    # 1. Biggest Price Drops (Absolute & %) OVERALL per product key/variant
    # We group by product_key, retailer, variant first to find drops within a single item listing
    df_sorted = df.sort_values(['product_key', 'retailer', 'variant', 'date'])
    
    insights = []
    
    # Group by unique product trackable (Product + Storage/Color Variant + Retailer)
    # Note: 'variant' column in DB might be messy, let's check unique values briefly later or assume it handles storage/color
    
    groups = df.groupby(['product_key', 'retailer', 'variant'])
    
    for name, group in groups:
        if len(group) < 2:
            continue
            
        prod_key, retailer, variant = name
        
        start_price = group.iloc[0]['price']
        end_price = group.iloc[-1]['price']
        max_price = group['price'].max()
        min_price = group['price'].min()
        
        # Current vs Max drop
        drop_from_peak = max_price - end_price
        drop_pct = (drop_from_peak / max_price) * 100 if max_price > 0 else 0
        
        # Trend
        change = end_price - start_price
        change_pct = (change / start_price) * 100 if start_price > 0 else 0
        
        volatility = group['price'].std()
        
        if drop_pct > 1 or abs(change_pct) > 1: # Lowered threshold to 1%
            insights.append({
                'product': prod_key,
                'retailer': retailer,
                'variant': variant,
                'current_price': end_price,
                'max_price': max_price,
                'drop_pct': drop_pct,
                'change_pct': change_pct,
                'volatility': volatility
            })
            
    df_insights = pd.DataFrame(insights)
    print(f"DEBUG: Found {len(df_insights)} insights with >1% change")
    
    if not df_insights.empty:
        print("--- 🔥 GIẢM GIÁ MẠNH NHẤT (Top drops from peak in 30 days) ---")
        top_drops = df_insights.sort_values('drop_pct', ascending=False).head(10)
        for _, row in top_drops.iterrows():
            print(f"- {row['product']} ({row['variant']}) @ {row['retailer']}:")
            print(f"  Giảm {row['drop_pct']:.1f}% đỉnh: {row['max_price']:,.0f} -> {row['current_price']:,.0f}")
            
        print("\n--- 📉 XU HƯỚNG TĂNG/GIẢM (Start vs End) ---")
        top_changes = df_insights.sort_values('change_pct').head(5) # Biggest drops
        for _, row in top_changes.iterrows():
             print(f"- {row['product']} ({row['variant']}) @ {row['retailer']}: Giảm {abs(row['change_pct']):.1f}% từ đầu tháng")
             
        top_increases = df_insights.sort_values('change_pct', ascending=False).head(5)
        for _, row in top_increases.iterrows():
             if row['change_pct'] > 0:
                print(f"- {row['product']} ({row['variant']}) @ {row['retailer']}: Tăng {row['change_pct']:.1f}%")

    # 2. Retailer Comparison (Price War)
    # Find products sold by multiple retailers and compare current prices
    latest_date = df['date'].max()
    current_prices = df[df['date'] == latest_date].copy()
    
    # Clean variant to just Storage/Capacity mostly if we can, to ensure apples-to-apples
    # For now, let's try to match on product_key and (if possible) rough variant matching
    # Group by product_key and calculate price spread
    
    price_spreads = current_prices.groupby(['product_key']).agg(
        num_retailers=('retailer', 'nunique'),
        min_price=('price', 'min'),
        max_price=('price', 'max'),
        retailers=('retailer', lambda x: list(x.unique()))
    ).reset_index()
    
    price_spreads['spread'] = price_spreads['max_price'] - price_spreads['min_price']
    price_spreads['spread_pct'] = (price_spreads['spread'] / price_spreads['min_price']) * 100
    
    # Filter for items sold by >1 retailer
    print(f"DEBUG: Found {len(price_spreads)} unique products today. {len(price_spreads[price_spreads['num_retailers'] > 1])} sold by >1 retailer.")
    
    multi_retailer = price_spreads[price_spreads['num_retailers'] > 1].sort_values('spread_pct', ascending=False)
    
    if not multi_retailer.empty:
        print("\n--- ⚔️ CHÊNH LỆCH GIÁ GIỮA CÁC ĐẠI LÝ (Hiện tại) ---")
        for _, row in multi_retailer.head(10).iterrows():
            print(f"- {row['product_key']}: Chênh {row['spread_pct']:.1f}% ({row['spread']:,.0f}đ)")
            print(f"  Range: {row['min_price']:,.0f} - {row['max_price']:,.0f} (Retailers: {', '.join(row['retailers'])})")

if __name__ == "__main__":
    analyze_prices()
