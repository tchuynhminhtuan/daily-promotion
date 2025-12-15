import pandas as pd
import os
import glob
import re

# Configuration
BASE_DIR = "/Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/content"
DATES = ["2025-11-29", "2025-12-01","2025-12-05", "2025-12-08", "2025-12-13"]
OUTPUT_FILE = os.path.join(BASE_DIR, "analysis_result", "promo_diff_report.csv")

# Column Mapping
COLUMN_MAPPING = {
    "Product_Name": "Product Name",
    "Color": "Color",
    "Khuyen_Mai": "Promotion Details",
    "Thanh_Toan": "Payment Promo",
    "Uu_Dai_Them": "Payment Promo",
    "Other_promotion": "Other Promo"
}

def load_data():
    all_data = []
    for date_str in DATES:
        day_dir = os.path.join(BASE_DIR, date_str)
        if not os.path.exists(day_dir):
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
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    df = df.rename(columns=COLUMN_MAPPING)
                    df['Channel'] = channel_name
                    
                    # Date formatting
                    dt_obj = pd.to_datetime(date_str)
                    day_suffix = dt_obj.strftime('%a').upper()
                    df['Date'] = f"{date_str}-{day_suffix}"
                    df['_RawDate'] = date_str # Keep sortable date
                    
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                
    if not all_data:
        return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

def normalize_text(text):
    """
    Normalizes promotion text for comparison:
    1. Handles NaNs.
    2. Removes extra whitespace.
    3. Splits by lines, strips each line, sorts lines (to ignore order changes).
    4. Re-joins.
    """
    if pd.isna(text) or str(text).strip() == "":
        return ""
    
    text = str(text)
    
    # Simple cleanup
    # Remove special chars that might be inconsistent like non-breaking spaces
    text = text.replace('\xa0', ' ').replace('\u200b', '')
    
    # Split by newlines or semicolons if used as separators
    # Assuming newlines are the main separator in the cell
    lines = re.split(r'[\n\r]+', text)
    
    # Clean and filter empty lines
    clean_lines = [line.strip() for line in lines if line.strip()]
    
    # Sort to ignore order changes
    clean_lines.sort()
    
    return " | ".join(clean_lines)

def collapse_colors_text(df):
    """
    similar to price matrix, but grouping by TEXT fields now.
    """
    # Columns involved in comparison
    text_cols = ['Promotion Details', 'Payment Promo']
    
    # Helper to check if cols exist
    existing_text_cols = [c for c in text_cols if c in df.columns]
    
    group_cols = ['Channel', 'Date', '_RawDate', 'Product Name'] + existing_text_cols
    
    # Fill N/As for grouping
    df_filled = df.copy()
    for col in existing_text_cols:
        df_filled[col] = df_filled[col].fillna("")
        df_filled[col] = df_filled[col].apply(normalize_text)

    # Aggregator for color
    def agg_colors(x):
        colors = sorted(list(set(x)))
        if len(colors) > 1:
            return "All Colors"
        return colors[0]

    collapsed = df_filled.groupby(group_cols)['Color'].apply(agg_colors).reset_index()
    return collapsed

def generate_diff(df):
    if df.empty:
        return

    # Sort to ensure chronological order for comparison
    df = df.sort_values(by=['Channel', 'Product Name', 'Color', '_RawDate'])
    
    # Identify changes
    # We will lag the text columns within each group (Channel, Product, Color)
    
    cols_to_compare = ['Promotion Details', 'Payment Promo']
    valid_cols = [c for c in cols_to_compare if c in df.columns]
    
    changes = []
    
    # Group by key entities
    grouped = df.groupby(['Channel', 'Product Name', 'Color'])
    
    for name, group in grouped:
        # If only 1 record, no history to compare
        if len(group) < 2:
            continue
            
        # Get lists
        dates = group['Date'].tolist()
        
        for i in range(1, len(group)):
            curr_row = group.iloc[i]
            prev_row = group.iloc[i-1]
            
            has_change = False
            change_record = {
                "Channel": curr_row['Channel'],
                "Product Name": curr_row['Product Name'],
                "Color": curr_row['Color'],
                "Date": curr_row['Date'],
                "Prev_Date": prev_row['Date']
            }
            
            for col in valid_cols:
                curr_text = curr_row[col]
                prev_text = prev_row[col]
                
                if curr_text != prev_text:
                    has_change = True
                    change_record[f"Changed_{col}"] = "YES"
                    change_record[f"Old_{col}"] = prev_text
                    change_record[f"New_{col}"] = curr_text
                else:
                    change_record[f"Changed_{col}"] = "NO"
                    change_record[f"Old_{col}"] = "" # Keep empty if no change to reduce clutter? Or keep for context?
                    change_record[f"New_{col}"] = ""
                    
            if has_change:
                changes.append(change_record)
                
    if changes:
        diff_df = pd.DataFrame(changes)
        # Reorder columns: Changed_Col -> New_Col -> Old_Col
        base_cols = ["Channel", "Product Name", "Color", "Date", "Prev_Date"]
        
        dynamic_cols = []
        for col in valid_cols:
            if f"Changed_{col}" in diff_df.columns:
                dynamic_cols.append(f"Changed_{col}")
            if f"New_{col}" in diff_df.columns:
                dynamic_cols.append(f"New_{col}")
            if f"Old_{col}" in diff_df.columns:
                dynamic_cols.append(f"Old_{col}")
                
        # Ensure we don't miss any others (sanity check)
        used_cols = set(base_cols + dynamic_cols)
        remaining_cols = [c for c in diff_df.columns if c not in used_cols]
        
        diff_df = diff_df[base_cols + dynamic_cols + remaining_cols]
        
        diff_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Promo Diff Report saved to: {OUTPUT_FILE}")
        print(diff_df.head())
    else:
        print("No text changes detected.")

def main():
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} rows.")

    print("Collapsing & Normalizing...")
    df_collapsed = collapse_colors_text(df)
    print(f"Collapsed to {len(df_collapsed)} unique promo groups.")
    
    print("Generating Diff Report...")
    generate_diff(df_collapsed)

if __name__ == "__main__":
    main()
