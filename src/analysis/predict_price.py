
import sqlite3
import pandas as pd
import numpy as np
import argparse
import sys
from datetime import datetime

DB_PATH = "catalog/price_history.db"

def load_data(product_key=None):
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT 
        p.key,
        p.name,
        h.date,
        h.price,
        h.retailer
    FROM price_history h
    JOIN products p ON h.product_id = p.id
    """
    
    if product_key:
        query += f" WHERE p.key = '{product_key}'"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return None
        
    # FIX: Clean date column (handle '-specs' suffix artifact)
    df['date'] = df['date'].astype(str).str.replace(r'-specs.*', '', regex=True)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date', 'price']) # Clean up rows with invalid dates or prices
    return df

def get_product_analysis(df, product_key):
    # Filter for specific product
    subset = df[df['key'] == product_key].copy()
    if subset.empty:
        return None

    # 1. Daily Average Price (across all retailers)
    daily = subset.groupby('date')['price'].min().reset_index() # Use Min price as the "market best"
    daily = daily.sort_values('date')
    daily.set_index('date', inplace=True)
    
    # 2. Moving Averages
    daily['SMA_30'] = daily['price'].rolling(window=30).mean()
    daily['SMA_7'] = daily['price'].rolling(window=7).mean()
    
    # 3. Seasonality (Monthly Index)
    daily['month'] = daily.index.month
    monthly_avg = daily.groupby('month')['price'].mean()
    overall_mean = daily['price'].mean()
    seasonality = monthly_avg / overall_mean

    # 4. Current State
    current_price = daily['price'].iloc[-1]
    current_date = daily.index[-1]
    sma_30 = daily['SMA_30'].iloc[-1]
    
    # 5. Recommendation Logic
    signal = "HOLD"
    reason = []
    
    # Trend Signal
    if pd.isna(sma_30):
        reason.append("Not enough data for trend analysis.")
    elif current_price < sma_30 * 0.95:
        signal = "BUY NOW"
        reason.append("Price is significantly below 30-day average (-5% dips).")
    elif current_price > sma_30 * 1.05:
        signal = "WAIT"
        reason.append("Price is currently high (above 30-day trend).")
    
    # Seasonality Signal
    current_month = current_date.month
    next_month = (current_month % 12) + 1
    
    if current_month in seasonality and next_month in seasonality:
        curr_idx = seasonality[current_month]
        next_idx = seasonality[next_month]
        
        if next_idx < curr_idx * 0.98:
            signal = "WAIT"
            reason.append(f"Historical data suggests prices drop in Month {next_month}.")
            
    return {
        "product_key": product_key,
        "latest_date": current_date.strftime('%Y-%m-%d'),
        "current_price": float(current_price),
        "sma_30": float(sma_30) if not pd.isna(sma_30) else None,
        "recommendation": signal,
        "reasons": reason,
        "seasonality_index": seasonality.to_dict()
    }

def analyze_product(df, product_key):
    result = get_product_analysis(df, product_key)
    if not result:
        print(f"No data found for {product_key}")
        return

    print(f"\n📊 ANALYSIS FOR: {result['product_key']}")
    print(f"📅 Latest Date: {result['latest_date']}")
    print(f"💰 Current Best Price: {result['current_price']:,.0f} VND")
    if result['sma_30']:
        print(f"📉 30-Day Average: {result['sma_30']:,.0f} VND")
    else:
        print(f"📉 30-Day Average: N/A")
    
    print(f"\n🚦 RECOMMENDATION: {result['recommendation']}")
    for r in result['reasons']:
        print(f"   - {r}")
        
    print("\n🗓️  Monthly Seasonality Index (1.0 = Average):")
    for m, idx in result['seasonality_index'].items():
        bar = "█" * int((idx - 0.8) * 50) if idx > 0.8 else "" 
        print(f"   Month {m:02d}: {idx:.3f} {bar}")

def main():
    parser = argparse.ArgumentParser(description="Predict product price trends.")
    parser.add_argument("key", nargs="?", help="Product Key (e.g., iphone_15_128gb)")
    parser.add_argument("--list", action="store_true", help="List available keys")
    
    args = parser.parse_args()
    
    if args.list:
        conn = sqlite3.connect(DB_PATH)
        products = pd.read_sql_query("SELECT key, name, COUNT(*) as count FROM products p JOIN price_history h ON p.id = h.product_id GROUP BY key ORDER BY count DESC LIMIT 20", conn)
        conn.close()
        print(products)
        return

    if not args.key:
        print("Please provide a product key or use --list")
        sys.exit(1)
        
    df = load_data(args.key)
    if df is None:
        print("Database is empty or could not be read.")
        return
        
    analyze_product(df, args.key)

if __name__ == "__main__":
    main()
