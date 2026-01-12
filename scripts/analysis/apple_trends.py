import pandas as pd
import numpy as np
import os

# --- CONFIG ---
INPUT_FILE = "analysis_result/apple_price_history_master.csv"
OUTPUT_DIR = "analysis_result"

def analyze_trends(df):
    """
    Analyzes price history for trends.
    """
    # Convert dates
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Identify Price Columns
    price_cols = [c for c in df.columns if c.endswith("_Price") and c != "Min_Price" and c != "Max_Price"]
    # Ensure they are numeric
    for c in price_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    print(f"📈 Analyzing {len(df)} rows across {len(price_cols)} retailers...")
    
    # Group by Anchor Product (+Color) to analyze specific SKU trends
    # We use 'Anchor_Name' + 'Anchor_Color' as ID
    df['SKU'] = df['Anchor_Name'].astype(str) + " - " + df['Anchor_Color'].fillna("").astype(str)
    
    sku_stats = []
    
    grouped = df.groupby('SKU')
    
    for sku, group in grouped:
        if len(group) < 3: continue # Need at least few data points
        
        group = group.sort_values('Date')
        
        # Calculate 'Market Average Price' per day
        # (Average of all valid retailer prices for that SKU on that day)
        # We can just take mean of price_cols
        group['Daily_Avg'] = group[price_cols].mean(axis=1)
        
        first_price = group['Daily_Avg'].iloc[0]
        last_price = group['Daily_Avg'].iloc[-1]
        
        if pd.isna(first_price) or pd.isna(last_price) or first_price == 0:
            change_pct = 0
        else:
            change_pct = ((last_price - first_price) / first_price) * 100
            
        # Volatility: Std Dev of Daily Avg
        volatility = group['Daily_Avg'].std()
        
        # Who is cheapest most often for this SKU?
        # We need to find min col per row
        # ... logic similar to leaderboard but over time
        
        sku_stats.append({
            "SKU": sku,
            "Days_Tracked": len(group),
            "First_Price_Avg": first_price,
            "Last_Price_Avg": last_price,
            "Change_Pct": round(change_pct, 2),
            "Volatility": round(volatility, 2),
            "Min_Price_Seen": group[price_cols].min().min(),
            "Max_Price_Seen": group[price_cols].max().max()
        })
        
    stats_df = pd.DataFrame(sku_stats)
    return stats_df

def generate_insights(stats_df):
    """Generates textual insights."""
    
    print("\n--- 📉 PRICE DECAY (Top Drops) ---")
    drops = stats_df.sort_values('Change_Pct').head(5)
    print(drops[['SKU', 'Change_Pct', 'First_Price_Avg', 'Last_Price_Avg']].to_string(index=False))
    
    print("\n--- 🎢 MOST VOLATILE PRODUCTS ---")
    volatile = stats_df.sort_values('Volatility', ascending=False).head(5)
    print(volatile[['SKU', 'Volatility', 'Days_Tracked']].to_string(index=False))
    
    print("\n--- 🗿 MOST STABLE PRICES ---")
    stable = stats_df[stats_df['Volatility'] == 0].head(5)
    print(stable[['SKU', 'Volatility', 'Last_Price_Avg']].to_string(index=False))

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        return
        
    print("🚀 Starting Apple Market Trend Analysis...")
    df = pd.read_csv(INPUT_FILE)
    
    stats_df = analyze_trends(df)
    
    if stats_df.empty:
        print("⚠️ Not enough data to generate trends.")
        return
        
    generate_insights(stats_df)
    
    out_file = f"{OUTPUT_DIR}/apple_price_trends.csv"
    stats_df.to_csv(out_file, index=False)
    print(f"\n✅ Trend Report Saved to: {out_file}")

if __name__ == "__main__":
    main()
