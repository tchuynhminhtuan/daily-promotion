
import sqlite3
import pandas as pd
import os

DB_FILE = "apple_prices.db"
OUTPUT_FILE = "tableau_data.csv"

def export_to_csv():
    if not os.path.exists(DB_FILE):
        print(f"❌ Database not found: {DB_FILE}")
        return

    print(f"🚀 Connecting to {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)

    # Join Products and Prices to get a flat table
    query = """
    SELECT 
        pr.date as Date,
        p.family as Family,
        p.model_key as Model,
        pr.retailer as Retailer,
        pr.price as Price,
        pr.original_price as Listed_Price,
        pr.in_stock as In_Stock,
        pr.url as URL
    FROM prices pr
    JOIN products p ON pr.product_id = p.id
    WHERE pr.price > 0
    ORDER BY p.family, p.model_key, pr.date
    """

    print("📊 Fetching data...")
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("⚠️ No data found to export!")
        return

    # Post-processing for Tableau Friendliness
    # Ensure Date is YYYY-MM-DD (Handle bad dates gracefully)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']) # Drop rows with invalid dates
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    # Calculate Savings (if Listed Price exists)
    df['Discount_Amount'] = df['Listed_Price'] - df['Price']
    df['Discount_Pct'] = (df['Discount_Amount'] / df['Listed_Price'] * 100).fillna(0).round(1)

    print(f"💾 Saving {len(df)} rows to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig') # utf-8-sig for Excel/Tableau compatibility
    print("✅ Export Complete!")

if __name__ == "__main__":
    export_to_csv()
