import os
import glob
import pandas as pd
import numpy as np

# --- CONFIG ---
OUTPUT_DIR = "analysis_result"

def get_latest_comparison_file():
    """Finds the latest semantic comparison CSV."""
    files = glob.glob(f"{OUTPUT_DIR}/apple_price_comparison_*_semantic.csv")
    if not files:
        return None
    # Sort by name (date is in name YYYY-MM-DD)
    return sorted(files)[-1]

def analyze_prices(df):
    """
    Performs price analysis: Min, Max, Spread, Winner.
    """
    # Identify Price Columns (ending with _Price)
    price_cols = [c for c in df.columns if c.endswith("_Price")]
    
    if not price_cols:
        print("❌ No price columns found.")
        return df, None

    print(f"💰 Analyzing prices across: {price_cols}")
    
    # ensure numeric
    for c in price_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # Row-wise stats
    df['Min_Price'] = df[price_cols].min(axis=1)
    df['Max_Price'] = df[price_cols].max(axis=1)
    df['Price_Spread'] = df['Max_Price'] - df['Min_Price']
    df['Spread_Pct'] = (df['Price_Spread'] / df['Min_Price'] * 100).round(1)
    
    # Identify Winner (Cheapest)
    # This is tricky if multiple have same min price. We pick first or list all.
    # Let's list the column name of the min.
    
    def find_winner(row):
        best_price = row['Min_Price']
        if pd.isna(best_price):
            return "N/A"
        
        winners = []
        for col in price_cols:
            if row[col] == best_price:
                # customized name: "FPT_Price" -> "FPT"
                cleaned_name = col.replace("_Price", "")
                winners.append(cleaned_name)
        
        return ", ".join(winners)

    df['Cheapest_Retailer'] = df.apply(find_winner, axis=1)
    
    return df, price_cols

def generate_summary(df, price_cols):
    """Generates aggregate stats."""
    
    print("\n--- 🏆 RETAILER LEADERBOARD 🏆 ---")
    
    summary_stats = []
    
    for col in price_cols:
        retailer = col.replace("_Price", "")
        
        # Win Rate (Count how many times they are in 'Cheapest_Retailer')
        # Note: 'Cheapest_Retailer' is a string like "FPT, Viettel".
        win_count = df['Cheapest_Retailer'].apply(lambda x: retailer in x if isinstance(x, str) else False).sum()
        
        # Average Price (of items they sell)
        avg_price = df[col].mean()
        
        # Coverage (How many items they have matched/valid price for)
        coverage = df[col].count()
        coverage_pct = (coverage / len(df)) * 100
        
        summary_stats.append({
            "Retailer": retailer,
            "Wins": win_count,
            "Avg_Price_M": round(avg_price / 1_000_000, 2), # In Millions
            "Coverage_Pct": round(coverage_pct, 1)
        })
        
    summary_df = pd.DataFrame(summary_stats)
    summary_df['Win_Rate_%'] = (summary_df['Wins'] / len(df) * 100).round(1)
    
    # Sort by Wins
    summary_df = summary_df.sort_values(by="Wins", ascending=False)
    
    print(summary_df.to_string(index=False))
    return summary_df

def main():
    print("🚀 Starting Apple Price Leaderboard Analysis...")
    
    # 1. Load Data
    infile = get_latest_comparison_file()
    if not infile:
        print("❌ No comparison file found. Run apple_price_analysis.py first.")
        return
        
    print(f"📄 Loading: {infile}")
    df = pd.read_csv(infile)
    
    # 2. Analyze
    analyzed_df, price_cols = analyze_prices(df)
    
    # 3. Generate Summary
    if price_cols:
        summary_df = generate_summary(analyzed_df, price_cols)
        
    # 4. Save
    base_name = os.path.basename(infile)
    out_name = base_name.replace("comparison", "leaderboard").replace("_semantic", "_stats")
    out_path = f"{OUTPUT_DIR}/{out_name}"
    
    # Reorder columns for clarity
    # Anchor_Name | Cheapest_Retailer | Min_Price | FPT | MW | ...
    
    meta_cols = ['Anchor_Name', 'Anchor_Color', 'Cheapest_Retailer', 'Min_Price', 'Price_Spread', 'Spread_Pct']
    final_cols = meta_cols + price_cols
    
    # filter columns that exist
    final_cols = [c for c in final_cols if c in analyzed_df.columns]
    
    analyzed_df[final_cols].to_csv(out_path, index=False)
    print(f"\n✅ Leaderboard Saved to: {out_path}")
    
    # Show Top Spreads (Biggest Diffs)
    print("\n--- 🚨 TOP 5 PRICE VARIATIONS ---")
    top_spreads = analyzed_df.sort_values(by='Price_Spread', ascending=False).head(5)
    print(top_spreads[['Anchor_Name', 'Price_Spread', 'Cheapest_Retailer', 'Min_Price']].to_string(index=False))

if __name__ == "__main__":
    main()
