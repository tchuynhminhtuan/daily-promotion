"""
Price Trend Analysis: Stock, Color, Price relationships
Analyze data from data/raw/ to find patterns
"""
import pandas as pd
import glob
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
RAW_DIR = BASE_DIR / "data/raw"

def load_all_data():
    """Load all CSV files from data/raw/ AND Market Promotion/"""
    all_data = []
    
    # 1. Load from data/raw/ (new format)
    date_dirs = sorted(RAW_DIR.glob("202*"))
    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        for csv_file in date_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, sep=';', encoding='utf-8')
                if 'Product_Name' not in df.columns:
                    continue
                df['Date'] = date_str
                df['Source_File'] = csv_file.name
                all_data.append(df)
            except:
                pass
    
    # 2. Load from Market Promotion/ (legacy format - recursive)
    legacy_dir = BASE_DIR / "Market Promotion"
    legacy_csvs = list(legacy_dir.rglob("*.csv"))
    print(f"📂 Found {len(legacy_csvs)} CSV files in Market Promotion/")
    
    for csv_file in legacy_csvs:
        try:
            # Try different separators
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(csv_file, sep=sep, encoding='utf-8', on_bad_lines='skip')
                    if len(df.columns) > 2:
                        break
                except:
                    continue
            
            # Normalize column names
            df.columns = [c.strip() for c in df.columns]
            
            # Extract date from filename or path
            date_str = None
            parts = str(csv_file).split('/')
            for part in parts:
                if part.startswith('202') and len(part) == 10:  # YYYY-MM-DD
                    date_str = part
                    break
            if not date_str:
                # Try to extract from filename
                import re
                match = re.search(r'(\d{4}-\d{2}-\d{2})', str(csv_file))
                if match:
                    date_str = match.group(1)
            
            if date_str and 'Product_Name' in df.columns:
                df['Date'] = date_str
                df['Source_File'] = csv_file.name
                all_data.append(df)
        except Exception as e:
            pass
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def analyze_stock_price_correlation(df):
    """Analyze if stock status correlates with price changes"""
    print("\n" + "="*60)
    print("📊 STOCK vs PRICE ANALYSIS")
    print("="*60)
    
    # Clean data
    df['Gia_Khuyen_Mai'] = pd.to_numeric(df['Gia_Khuyen_Mai'], errors='coerce')
    df['Ton_Kho'] = df['Ton_Kho'].astype(str).str.lower().str.strip()
    
    # Group by product and date
    product_history = df.groupby(['Product_Name', 'Date']).agg({
        'Gia_Khuyen_Mai': 'mean',
        'Ton_Kho': 'first'
    }).reset_index()
    
    # Find products that went out of stock
    products_with_stock_changes = []
    for product in product_history['Product_Name'].unique():
        prod_data = product_history[product_history['Product_Name'] == product].sort_values('Date')
        stock_states = prod_data['Ton_Kho'].tolist()
        prices = prod_data['Gia_Khuyen_Mai'].tolist()
        dates = prod_data['Date'].tolist()
        
        # Check if stock changed from yes to no or vice versa
        for i in range(1, len(stock_states)):
            if stock_states[i-1] == 'yes' and stock_states[i] == 'no':
                if len(prices) > 1 and not pd.isna(prices[i-1]):
                    products_with_stock_changes.append({
                        'product': product[:50],
                        'event': 'OUT_OF_STOCK',
                        'date': dates[i],
                        'last_price': prices[i-1]
                    })
            elif stock_states[i-1] == 'no' and stock_states[i] == 'yes':
                products_with_stock_changes.append({
                    'product': product[:50],
                    'event': 'BACK_IN_STOCK',
                    'date': dates[i],
                    'new_price': prices[i] if not pd.isna(prices[i]) else 'N/A'
                })
    
    print(f"\n📦 Products with stock status changes: {len(products_with_stock_changes)}")
    for item in products_with_stock_changes[:10]:
        print(f"  {item['event']:<15} | {item['date']} | {item['product']}")
    
    return products_with_stock_changes

def analyze_color_price(df):
    """Analyze price differences by color"""
    print("\n" + "="*60)
    print("🎨 COLOR vs PRICE ANALYSIS")
    print("="*60)
    
    df['Gia_Khuyen_Mai'] = pd.to_numeric(df['Gia_Khuyen_Mai'], errors='coerce')
    # Filter out invalid prices (< 100k)
    df = df[df['Gia_Khuyen_Mai'] > 100000].copy()
    
    # Find products with multiple colors
    color_analysis = df.groupby(['Product_Name', 'Color']).agg({
        'Gia_Khuyen_Mai': 'mean',
        'Ton_Kho': lambda x: (x.astype(str).str.lower() == 'yes').sum()
    }).reset_index()
    color_analysis.columns = ['Product_Name', 'Color', 'Avg_Price', 'Stock_Days']
    
    # Find price differences within same product
    price_diffs = []
    for product in color_analysis['Product_Name'].unique():
        prod_colors = color_analysis[color_analysis['Product_Name'] == product]
        if len(prod_colors) > 1:
            max_price = prod_colors['Avg_Price'].max()
            min_price = prod_colors['Avg_Price'].min()
            if max_price > 0 and min_price > 0:
                diff_pct = (max_price - min_price) / min_price * 100
                if diff_pct > 1:  # More than 1% difference
                    price_diffs.append({
                        'product': product[:40],
                        'colors': len(prod_colors),
                        'min_price': min_price,
                        'max_price': max_price,
                        'diff_pct': diff_pct
                    })
    
    price_diffs = sorted(price_diffs, key=lambda x: x['diff_pct'], reverse=True)[:10]
    
    print(f"\n🎨 Top products with color price differences:")
    for item in price_diffs:
        print(f"  {item['diff_pct']:5.1f}% | {item['product']}")
    
    return price_diffs

def analyze_price_trends(df):
    """Analyze overall price trends"""
    print("\n" + "="*60)
    print("📈 PRICE TREND ANALYSIS (30+ days)")
    print("="*60)
    
    df['Gia_Khuyen_Mai'] = pd.to_numeric(df['Gia_Khuyen_Mai'], errors='coerce')
    # Filter out invalid prices (< 100k)
    df = df[df['Gia_Khuyen_Mai'] > 100000].copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Get products with enough data points
    product_counts = df.groupby('Product_Name')['Date'].nunique()
    products_with_history = product_counts[product_counts >= 10].index.tolist()
    
    print(f"\n📅 Products with 10+ days of data: {len(products_with_history)}")
    
    # Calculate trends
    trends = []
    for product in products_with_history[:100]:  # Limit to 100 for speed
        prod_data = df[df['Product_Name'] == product].sort_values('Date')
        prices = prod_data.groupby('Date')['Gia_Khuyen_Mai'].mean().dropna()
        
        if len(prices) >= 10:
            first_price = prices.iloc[0]
            last_price = prices.iloc[-1]
            if first_price > 0:
                change_pct = (last_price - first_price) / first_price * 100
                trends.append({
                    'product': product[:45],
                    'first_price': first_price,
                    'last_price': last_price,
                    'change_pct': change_pct,
                    'days': len(prices)
                })
    
    # Sort by biggest drops
    drops = sorted([t for t in trends if t['change_pct'] < -2], key=lambda x: x['change_pct'])[:10]
    increases = sorted([t for t in trends if t['change_pct'] > 2], key=lambda x: x['change_pct'], reverse=True)[:10]
    
    print(f"\n🔻 BIGGEST PRICE DROPS:")
    for item in drops:
        print(f"  {item['change_pct']:6.1f}% | {item['product']}")
    
    print(f"\n🔺 BIGGEST PRICE INCREASES:")
    for item in increases:
        print(f"  {item['change_pct']:+6.1f}% | {item['product']}")
    
    return {'drops': drops, 'increases': increases}

if __name__ == "__main__":
    print("🔄 Loading data...")
    df = load_all_data()
    
    if df.empty:
        print("❌ No data found!")
    else:
        print(f"✅ Loaded {len(df):,} records from {df['Date'].nunique()} dates")
        print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
        
        stock_analysis = analyze_stock_price_correlation(df)
        color_analysis = analyze_color_price(df)
        trend_analysis = analyze_price_trends(df)
        
        print("\n" + "="*60)
        print("✨ ANALYSIS COMPLETE")
        print("="*60)
