import pandas as pd
import os
import glob

# Configuration
BASE_DIR = "/Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/content"
DATES = ["2025-11-29", "2025-12-01","2025-12-05", "2025-12-08", "2025-12-13"]
OUTPUT_FILE = os.path.join(BASE_DIR, "analysis_result", "price_matrix.csv")

# Column Mapping to normalize different CSV headers
COLUMN_MAPPING = {
    "Product_Name": "Product Name",
    "Color": "Color",
    "Gia_Niem_Yet": "Listed Price",
    "Gia_Khuyen_Mai": "Promo Price",
    "Khuyen_Mai": "Promotion Details",
    "Thanh_Toan": "Payment Promo",
    "Uu_Dai_Them": "Payment Promo", # MW uses this
    "Voucher_Image": "Voucher"
}

def load_data():
    all_data = []
    
    for date_str in DATES:
        day_dir = os.path.join(BASE_DIR, date_str)
        if not os.path.exists(day_dir):
            print(f"Warning: Directory not found: {day_dir}")
            continue
            
        file_patterns = {
            "FPT": f"1-fpt-{date_str}.csv",
            "MW": f"2-mw-{date_str}.csv",
            "Viettel": f"3-viettel-{date_str}.csv",
            "CPS": f"6-cps-{date_str}.csv"
        }
        
        for channel_name, filename in file_patterns.items():
            file_path = os.path.join(day_dir, filename)
            if os.path.exists(file_path):
                try:
                    # Read CSV, handling potential delimiters
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    
                    # Normalize Columns
                    df = df.rename(columns=COLUMN_MAPPING)
                    
                    # Add Metadata
                    df['Channel'] = channel_name
                    
                    # Format date with day of week (e.g. 2025-12-05-FRI)
                    dt_obj = pd.to_datetime(date_str)
                    day_suffix = dt_obj.strftime('%a').upper()
                    df['Date'] = f"{date_str}-{day_suffix}"
                    
                    # Ensure numeric prices
                    for col in ['Listed Price', 'Promo Price']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
            else:
                print(f"Warning: File not found: {file_path}")
                
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data, ignore_index=True)

def collapse_colors(df):
    """
    Groups products by Channel, Date, and Product Name.
    If multiple colors have the same Promo Price and Promotion Details,
    collapse them into 'All Colors'.
    """
    # Columns to check for identical values
    group_cols = ['Channel', 'Date', 'Product Name', 'Promo Price', 'Promotion Details']
    
    # We also want to keep listed price if it's consistent, but key is promo price
    # Let's include Listed Price in grouping to be safe, if it exists
    if 'Listed Price' in df.columns:
        group_cols.append('Listed Price')

    # Fill NaNs carefully to avoid converting numerics to strings
    df_filled = df.copy()
    
    # Fill string columns with "N/A"
    str_cols = ['Channel', 'Date', 'Product Name', 'Promotion Details', 'Color']
    for col in str_cols:
        if col in df_filled.columns:
            df_filled[col] = df_filled[col].fillna("N/A")
            
    # Fill numeric columns with -1 (sentinel)
    num_cols = ['Listed Price', 'Promo Price']
    for col in num_cols:
        if col in df_filled.columns:
            df_filled[col] = df_filled[col].fillna(-1)
    
    # helper to aggregate colors
    def agg_colors(x):
        colors = sorted(list(set(x)))
        if len(colors) > 1:
            return "All Colors"
        return colors[0]

    collapsed = df_filled.groupby(group_cols)['Color'].apply(agg_colors).reset_index()
    
    # Revert sentinels to NaN (optional, but good for cleanliness)
    for col in num_cols:
         if col in collapsed.columns:
             collapsed[col] = collapsed[col].replace(-1, float('nan'))
             
    return collapsed

def generate_matrix(df):
    if df.empty:
        print("No data to process.")
        return

    # Pivot Data
    # Index: Channel, Product Name, Color
    # Columns: Date
    # Values: Promo Price
    
    # We need to handle cases where 'Listed Price' or others might differ, 
    # but our collapse_colors groups by them, so they are unique per group.
    
    pivot_cols = ['Channel', 'Product Name', 'Color']
    
    # Pivot for Promo Price
    pivot_price = df.pivot_table(
        index=pivot_cols,
        columns='Date',
        values='Promo Price',
        aggfunc='first' # Should be unique after collapse
    )
    
    # Calculate Changes (Delta)
    # Assuming chronological order in DATES
    dates = sorted(list(df['Date'].unique()))
    
    if len(dates) > 1:
        for i in range(1, len(dates)):
            curr_date = dates[i]
            prev_date = dates[i-1]
            diff_col = f"Diff_{prev_date}_to_{curr_date}"
            pivot_price[diff_col] = pivot_price[curr_date] - pivot_price[prev_date]

    # Convert numeric columns to nullable integers for cleaner output
    # This leaves NaNs as empty/blank in CSV usually, or we can fill them if desired.
    # 'Int64' allows NaNs.
    cols_to_convert = list(pivot_price.columns)
    for col in cols_to_convert:
        # Check if column is numeric (dates and diffs)
        if pd.api.types.is_numeric_dtype(pivot_price[col]):
            pivot_price[col] = pivot_price[col].round(0).astype('Int64')

    # Save
    print(pivot_price.head())
    pivot_price.to_csv(OUTPUT_FILE)
    print(f"Price matrix saved to: {OUTPUT_FILE}")

def main():
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} rows.")
    
    print("Collapsing colors...")
    df_collapsed = collapse_colors(df)
    print(f"Collapsed to {len(df_collapsed)} rows.")
    
    print("Generating matrix...")
    generate_matrix(df_collapsed)

if __name__ == "__main__":
    main()
