import argparse
import sys
import pandas as pd
import os
import glob
import re
import html

import yaml

# --- Configuration ---
# Determine the project root directory (parent of 'code')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.join(PROJECT_ROOT, "content")
# --- Date Selection Options ---
# Option 1: Auto-select the two most recent dates (Default)
# Option 2: Hardcoded specific dates (Set AUTO_SELECT_DATES = False)
AUTO_SELECT_DATES = True

def get_available_dates(base_dir):
    """Scans content directory for date-like folders (YYYY-MM-DD) and returns them sorted."""
    if not os.path.exists(base_dir):
        return []
    
    dates = []
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    try:
        entries = os.listdir(base_dir)
        for entry in entries:
            full_path = os.path.join(base_dir, entry)
            if os.path.isdir(full_path) and date_pattern.match(entry):
                dates.append(entry)
    except OSError:
        return []
        
    return sorted(dates)

# Default DATES logic (can be overridden)
def get_default_dates(base_dir):
    available_dates = get_available_dates(base_dir)
    if len(available_dates) >= 2:
        return available_dates[-2:]
    elif available_dates:
        return available_dates
    return ["2025-12-19", "2025-12-20"] # Fallback

# For backward compatibility with other scripts that use the global DATES
DATES = get_default_dates(BASE_DIR)

# Output Paths
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis_result")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# GitHub Pages Directory (Root/docs)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

PRICE_MATRIX_FILE = os.path.join(OUTPUT_DIR, "price_matrix.csv")
PROMO_DIFF_CSV = os.path.join(OUTPUT_DIR, "promo_diff_report.csv")
# Save HTML to docs/index.html for GitHub Pages hosting
PROMO_DIFF_HTML = os.path.join(DOCS_DIR, "index.html")

# Column Mapping (Superset)
COLUMN_MAPPING = {
    "Product_Name": "Product Name",
    "Color": "Color",
    "Gia_Niem_Yet": "Listed Price",
    "Gia_Khuyen_Mai": "Promo Price",
    "Khuyen_Mai": "Promotion Details",
    "Thanh_Toan": "Payment Promo",
    "Uu_Dai_Them": "Payment Promo", # MW uses this
    "Voucher_Image": "Voucher",
    "Other_promotion": "Other Promo",
    "Link": "Link",
    "Ton_Kho": "Stock"
}



# --- Shared Helpers ---
def clean_price(price):
    if pd.isna(price): return None
    if isinstance(price, (int, float)): 
        val = float(price)
    else:
        s = str(price)
        s_clean = re.sub(r'[.,]', '', s) 
        matches = re.findall(r'\d+', s_clean)
        if not matches: return None
        val = None
        for m in matches:
            v = float(m)
            if v > 100000 and v < 200000000: 
                 val = v
                 break
                 
    if val and 100000 <= val < 200000000:
        return val
    return None

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text
    
def normalize_storage(text):
    text = str(text).lower()
    match = re.search(r'(\d+)\s*(gb|tb)', text)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        return f"{val}{unit}"
    return None

class ProductNormalizer:
    """Enriches product names using Golden Catalog and Specs."""
    
    def __init__(self):
        self.catalog = {}
        catalog_path = os.path.join(PROJECT_ROOT, "product_catalog_golden_v2.yaml")
        if os.path.exists(catalog_path):
            with open(catalog_path, 'r') as f:
                self.catalog = yaml.safe_load(f)
        else:
            print(f"⚠️ Warning: Catalog not found at {catalog_path}")

    def match_product(self, row_name):
        row_name_norm = normalize_text(row_name)
        best_match_key = None
        best_match_len = 0
        
        for key, info in self.catalog.items():
            cat_name = normalize_text(info['name'])
            if cat_name in row_name_norm:
                if len(cat_name) > best_match_len:
                    best_match_len = len(cat_name)
                    best_match_key = key
        return best_match_key

    def enrich_name(self, name, specs):
        if pd.isna(name): return name
        name_str = str(name)
        specs_str = str(specs) if pd.notna(specs) else ""
        
        # 1. Try to match Catalog
        key = self.match_product(name_str)
        if key:
            golden_name = self.catalog[key]['name']
            
            # 2. Extract Storage
            storage = normalize_storage(name_str)
            if not storage:
                storage = normalize_storage(specs_str)
            
            if storage:
                return f"{golden_name} ({storage})"
            return golden_name
            
        # Fallback
        return name_str.strip()

class DataLoader:
    """Handles loading and normalizing data from multiple CSV sources."""
    
    @staticmethod
    def load_all_data(dates=None, base_dir=None):
        target_dates = dates if dates else DATES
        target_base_dir = base_dir if base_dir else BASE_DIR
        all_data = []
        print("📥 Đang tải dữ liệu...")
        
        normalizer = ProductNormalizer()
        
        for date_str in target_dates:
            day_dir = os.path.join(target_base_dir, date_str)
            if not os.path.exists(day_dir):
                print(f"Skipping missing directory: {day_dir}")
                continue
                
            file_patterns = {
                "FPT": f"1-fpt-{date_str}.csv",
                "MW": f"2-mw-{date_str}.csv",
                "Viettel": f"3-viettel-{date_str}.csv",
                "HoangHa": f"4-hoangha-{date_str}.csv",
                "DDV": f"5-ddv-{date_str}.csv",
                "CPS": f"6-cps-{date_str}.csv"
            }
            
            for channel_name, filename in file_patterns.items():
                file_path = os.path.join(day_dir, filename)
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path, sep=None, engine='python')
                        df = df.rename(columns=COLUMN_MAPPING)
                        df['Channel'] = channel_name
                        
                        # Apply Name Enrichment if Tech_Specs exists
                        if 'Tech_Specs' in df.columns:
                            # Fill NA for specs to avoid errors
                            df['Tech_Specs'] = df['Tech_Specs'].fillna("")
                            df['Product Name'] = df.apply(
                                lambda row: normalizer.enrich_name(
                                    row.get('Product Name', ''), 
                                    row.get('Tech_Specs', '')
                                ), axis=1
                            )
                        
                        # Merge "Other Promo" into "Payment Promo" if it exists (User Request)
                        if "Other Promo" in df.columns:
                            if "Payment Promo" not in df.columns:
                                df["Payment Promo"] = ""
                            
                            # Vectorized combination with separator handling
                            df["Payment Promo"] = df["Payment Promo"].fillna("").astype(str)
                            df["Other Promo"] = df["Other Promo"].fillna("").astype(str)
                            
                            mask_both = (df["Payment Promo"] != "") & (df["Other Promo"] != "")
                            mask_other_only = (df["Payment Promo"] == "") & (df["Other Promo"] != "")
                            
                            # 1. Both exist: join with " | "
                            df.loc[mask_both, "Payment Promo"] = df.loc[mask_both, "Payment Promo"] + " | " + df.loc[mask_both, "Other Promo"]
                            
                            # 2. Only Other exists: move it to Payment
                            df.loc[mask_other_only, "Payment Promo"] = df.loc[mask_other_only, "Other Promo"]
                            
                            # Drop Other Promo to avoid confusion
                            df = df.drop(columns=["Other Promo"])

                        # Date formatting
                        dt_obj = pd.to_datetime(date_str)
                        day_suffix = dt_obj.strftime('%a').upper()
                        df['Date'] = f"{date_str}-{day_suffix}"
                        df['_RawDate'] = date_str # Keep sortable date
                        
                        # Normalize numeric columns
                        for col in ['Listed Price', 'Promo Price']:
                            if col in df.columns:
                                df[col] = df[col].apply(clean_price)
                                
                        all_data.append(df)
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
        
        if not all_data:
            print("No data loaded!")
            return pd.DataFrame()
            
        return pd.concat(all_data, ignore_index=True)

class PriceMatrixGenerator:
    """Generates the Price Matrix CSV and provides a Price Lookup Service."""
    
    def __init__(self, df, skip_csv=False):
        self.df = df
        self.skip_csv = skip_csv
        self.price_lookup = {} # Key: (Channel, Product, Color, Date), Value: Price

    def run(self):
        print("⚡ Đang tạo Ma trận Giá...")
        if self.df.empty: return

        # 1. Collapse Colors (Group by attributes to see if colors share same price)
        df_collapsed = self._collapse_for_matrix(self.df)
        
        # 2. Pivot for Matrix CSV
        if not self.skip_csv:
             self._generate_csv(df_collapsed)
        else:
             print("💡 Đang xử lý Ma trận Giá (Bỏ qua lưu file CSV matrix)...")
        
        # 3. Build Lookup (Use the collapsed DF or original? Original is safer for specific lookups, 
        #    but we often compare on the "collapsed" entity in Diff Report. 
        #    However, Diff Report collapses text, Matrix collapses Price. 
        #    Let's build lookup from the PIVOT data to be consistent with the matrix output.)
        
        # Actually, best source for lookup is the melted version of the matrix 
        # OR just the raw data if we want exactness. 
        # Let's use the raw dataframe for exact lookups to match the Promo Diff logic which iterates raw rows.
        # Wait, Promo Diff *also* iterates collapsed rows.
        # Let's populate lookup from the raw data first, it covers all bases.
        self._build_lookup(self.df)

    def _collapse_for_matrix(self, df):
        # We NO LONGER collapse colors. We just prepare the data.
        # This ensures every color variant is preserved.
        
        df_filled = df.copy()
        
        # Safe fills for pivoting
        str_cols = ['Channel', 'Date', 'Product Name', 'Promotion Details', 'Color']
        for col in str_cols:
            if col in df_filled.columns:
                df_filled[col] = df_filled[col].fillna("N/A")
                
        # We don't need to groupby anymore if we want to keep every color.
        # However, we should handle if there are strictly identical rows (duplicates).
        # Let's drop explicit duplicates to be safe.
        df_filled = df_filled.drop_duplicates(subset=['Channel', 'Date', 'Product Name', 'Color'])
        
        return df_filled

    def _generate_csv(self, df):
        pivot_cols = ['Channel', 'Product Name', 'Color']
        pivot_price = df.pivot_table(
            index=pivot_cols,
            columns='Date',
            values='Promo Price',
            aggfunc='first'
        )
        
        # Calculate Delta Columns
        dates = sorted(list(df['Date'].unique()))
        if len(dates) > 1:
            for i in range(1, len(dates)):
                curr_date = dates[i]
                prev_date = dates[i-1]
                diff_col = f"Diff_{prev_date}_to_{curr_date}"
                pivot_price[diff_col] = pivot_price[curr_date] - pivot_price[prev_date]

        # Format Int64
        for col in pivot_price.columns:
            if pd.api.types.is_numeric_dtype(pivot_price[col]):
                pivot_price[col] = pivot_price[col].round(0).astype('Int64')

        pivot_price.to_csv(PRICE_MATRIX_FILE)
        print(f"Price Matrix saved to: {PRICE_MATRIX_FILE}")

    def _build_lookup(self, df):
        # We build a lookup from (Channel, Product, Color, Date) -> Price
        # We use the raw DF because Promo Diff might iterate strictly over specific colors
        for _, row in df.iterrows():
            key = (row['Channel'], row['Product Name'], row['Color'], row['Date'])
            self.price_lookup[key] = row['Promo Price']
            
    def get_price(self, channel, product, color, date):
        # Direct lookup
        val = self.price_lookup.get((channel, product, color, date))
        
        # Fallback: if "All Colors" exists in matrix but we are asking for specific color?
        # This is complex. If Promo Diff uses "All Colors", it matches. 
        # If Promo Diff splits colors, we expect raw data to have it.
        # Since we populated from raw DF, exact match should work.
        return val

class PromoDiffGenerator:
    """Generates the Promotion Difference CSV and HTML Report."""
    
    def __init__(self, df, price_generator, output_file=None, skip_csv=False, include_all=False):
        self.df = df
        self.price_gen = price_generator
        self.output_file = output_file or PROMO_DIFF_CSV # Default if not provided
        self.skip_csv = skip_csv
        self.include_all = include_all

    def run(self):
        print("🔍 Đang phân tích thay đổi khuyến mãi...")
        if self.df.empty: return

        # 1. Normalize Text & Collapse for Promo View
        df_collapsed = self._collapse_for_promo(self.df)
        
        # 2. Identify Changes
        df_diff = self._identify_changes(df_collapsed)
        
        if df_diff is not None and not df_diff.empty:
            # 3. Save CSV
            if not self.skip_csv:
                df_diff.to_csv(self.output_file, index=False)
                print(f"✅ Đã lưu CSV thay đổi KM tại: {self.output_file}")
            else:
                print("🌐 Đang tạo báo cáo HTML (Bỏ qua lưu file CSV)...")
            
            # 4. Save HTML
            html_path = PROMO_DIFF_HTML
            if self.skip_csv and self.output_file.endswith('.html'):
                html_path = self.output_file
            
            self._save_html(df_diff, html_path)
        else:
            print("⚠️ Không tìm thấy thay đổi khuyến mãi nào.")

    def _collapse_for_promo(self, df):
        # We NO LONGER collapse colors. We just normalize text.
        
        df_filled = df.copy()
        
        # Normalize Text
        text_cols = ['Promotion Details', 'Payment Promo']
        existing_text_cols = [c for c in text_cols if c in df.columns]
        
        for col in existing_text_cols:
            df_filled[col] = df_filled[col].fillna("").apply(self._normalize_text)
            
        # Ensure we have unique rows per Channel/Product/Color/Date
        # In case raw data had duplicates.
        # Include Link in subset? Just keep the first valid link if duplicates exist.
        df_filled = df_filled.drop_duplicates(subset=['Channel', 'Date', 'Product Name', 'Color'])
            
        return df_filled

    def _normalize_text(self, text):
        if pd.isna(text) or str(text).strip() == "":
            return ""
        text = str(text).replace('\xa0', ' ').replace('\u200b', '')
        lines = re.split(r'[\n\r]+', text)
        clean_lines = []
        for line in lines:
            if not line.strip(): continue
            # Remove leading numbers/bullets (e.g., "1.", "1)", "-", "•")
            cleaned = re.sub(r'^(\d+[\.\)]|[-•])\s*', '', line.strip())
            if cleaned:
                clean_lines.append(cleaned)
        
        clean_lines.sort()
        return " | ".join(clean_lines)

    def _identify_changes(self, df):
        # Ensure correct date order for comparison
        # We want to identify T (Current) vs T-1 (Previous)
        # Sort by Channel -> Product -> Color -> Date (Oldest to Newest)
        df = df.sort_values(by=['Channel', 'Product Name', 'Color', '_RawDate'])
        
        dates_sorted = sorted(df['_RawDate'].unique())
        if len(dates_sorted) < 2:
            print("⚠️ Not enough dates to compare.")
            if self.include_all:
                 # If only 1 date exists, return everything as NEW
                 target_date = dates_sorted[0]
                 # Reuse logic below or just dump all
                 pass
        
        # We generally care about the transition from T-1 to T (Latest pair)
        # Even if df has 10 dates, we usually only care about the latest 2 passed to this class.
        # Let's assume df contains exactly the dates we want to compare.
        
        cols_to_compare = ['Promotion Details', 'Payment Promo']
        valid_cols = [c for c in cols_to_compare if c in df.columns]
        
        changes = []
        grouped = df.groupby(['Channel', 'Product Name', 'Color'])
        
        # Logic: 
        # For each group:
        # 1. If we have > 1 row: Compare the Last (Newest) vs Second Last (Previous).
        # 2. If we have 1 row: 
        #    - If it's the NEWEST date -> It's a NEW LISTING (Previous missing).
        #    - If it's the OLDER date -> It's REMOVED (Current missing).
        
        # We need to know what is "Newest" and "Previous" globally to tag properly.
        global_dates = sorted(list(df['Date'].unique()))
        if not global_dates: return pd.DataFrame()
        
        # Assume last one is "New" (target), second last is "Old" (reference)
        # Wait, sorted by string might be tricky with "Mon", "Tue". 
        # We should rely on _RawDate sorting in the loop.
        
        for _, group in grouped:
            # Sort group by _RawDate just to be safe
            group = group.sort_values('_RawDate')
            
            # Case 1: At least 2 records (Comparision possible)
            if len(group) >= 2:
                # Compare the last two records
                curr_row = group.iloc[-1]
                prev_row = group.iloc[-2]
                
                # Fetch Prices
                curr_price = curr_row.get('Promo Price')
                prev_price = prev_row.get('Promo Price')
                
                has_change = False
                change_record = {
                    "Channel": curr_row['Channel'],
                    "Product Name": curr_row['Product Name'],
                    "Color": curr_row['Color'],
                    "Date": curr_row['Date'],
                    "Prev_Date": prev_row['Date'],
                    "New_Price": curr_row.get('Promo Price'),
                    "Old_Price": prev_row.get('Promo Price'),
                    "Link": curr_row.get('Link', ''),
                    "Stock": curr_row.get('Stock', 'Unknown'), # Pass Stock
                    "Status": "UNCHANGED" # Default
                }
                
                # Compare Text
                for col in valid_cols:
                    curr_text = curr_row[col]
                    prev_text = prev_row[col]
                    
                    # Helper for set comparison
                    def get_items(t):
                         if pd.isna(t) or str(t).strip() == "": return set()
                         return {x.strip() for x in str(t).split('|') if x.strip()}

                    curr_set = get_items(curr_text)
                    prev_set = get_items(prev_text)

                    # Compare Sets instead of Raw Strings
                    if curr_set != prev_set:
                        has_change = True
                        change_record[f"Changed_{col}"] = "YES"
                        change_record[f"Old_{col}"] = prev_text
                        change_record[f"New_{col}"] = curr_text
                    else:
                        change_record[f"Changed_{col}"] = "NO"
                        change_record[f"Old_{col}"] = prev_text 
                        change_record[f"New_{col}"] = curr_text

                
                # Compare Price
                try:
                    p1 = float(curr_price) if pd.notna(curr_price) else 0
                    p2 = float(prev_price) if pd.notna(prev_price) else 0
                    if p1 != p2 and p1 > 0 and p2 > 0:
                        has_change = True
                except: pass

                if has_change:
                     change_record["Status"] = "CHANGED"
                     changes.append(change_record)
                elif self.include_all:
                     # Add unchanged record
                     changes.append(change_record)

            # Case 2: Only 1 record (New or Removed)
            elif self.include_all and len(group) == 1:
                 # Check if this single record is from the LATEST date
                 row = group.iloc[0]
                 # Is this the latest date in our dataset?
                 # We can check if it matches the *global* latest date.
                 # But we can simpler check: 
                 # If row['_RawDate'] is the last in dates_sorted -> NEW
                 # If row['_RawDate'] is NOT the last -> REMOVED (Old data, no new counterpart)
                 
                 if row['_RawDate'] == dates_sorted[-1]:
                     # It's a NEW Item
                     record = {
                        "Channel": row['Channel'],
                        "Product Name": row['Product Name'],
                        "Color": row['Color'],
                        "Date": row['Date'],
                        "Prev_Date": "N/A", # No prev
                        "New_Price": row.get('Promo Price'),
                        "Old_Price": 0, # Was not there
                        "Link": row.get('Link', ''),
                        "Stock": row.get('Stock', 'Unknown'), # Pass Stock
                        "Status": "NEW"
                     }
                     # Fill text cols
                     for col in valid_cols:
                         record[f"Changed_{col}"] = "YES" # Technically new content
                         record[f"Old_{col}"] = ""
                         record[f"New_{col}"] = row[col]
                     
                     changes.append(record)

        return pd.DataFrame(changes)

    def _find_fallback_price(self, channel, product, date):
        # Inefficient but functional fallback:
        # Scan self.price_gen.price_lookup keys
        for key, val in self.price_gen.price_lookup.items():
            # key: (Channel, Product, Color, Date)
            if key[0] == channel and key[1] == product and key[3] == date:
                return val
        return None

    def _save_html(self, df, path):
        # Use HTMLGenerator class to keep this clean
        HTMLGenerator(df, path).generate()

import markdown

class HTMLGenerator:
    def __init__(self, df, output_file):
        self.df = df
        self.output_file = output_file
        
    def _get_latest_insights_html(self):
        """Scans reports dir for latest markdown and converts to HTML."""
        try:
            # Updated to read from docs/insights
            reports_dir = os.path.join(SCRIPT_DIR, '../docs/insights')
            files = glob.glob(os.path.join(reports_dir, '*_insights.md'))
            if not files:
                return ""
            
            latest_file = max(files, key=os.path.getmtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
                
            html_content = markdown.markdown(md_content)
            
            return f"""
            <div id="ai-insights-wrapper" style="text-align: center; margin-bottom: 10px;">
                <button id="toggleInsights" onclick="toggleInsights()">📊 Xem Phân Tích AI</button>
            </div>
            <div id="insightsPanel" class="insights-container hidden">
                {html_content}
            </div>
            """
        except Exception as e:
            print(f"Error loading insights: {e}")
            return ""

    def generate(self):
        channels = sorted(self.df['Channel'].unique().tolist())
        dates = sorted(self.df['Date'].unique().tolist(), reverse=True)
        channel_opts = "".join([f'<option value="{c}">{c}</option>' for c in channels])
        date_opts = "".join([f'<option value="{d}">{d}</option>' for d in dates])
        
        # Determine Comparison Dates for Header
        try:
            # Most freq current date
            curr_date = self.df['Date'].mode()[0]
            # Most freq prev date (excluding N/A)
            prev_dates = self.df[self.df['Prev_Date'] != 'N/A']['Prev_Date']
            if not prev_dates.empty:
                prev_date = prev_dates.mode()[0]
            else:
                prev_date = "N/A"
            
            # Translate
            curr_date_vn = self._translate_date(curr_date)
            prev_date_vn = self._translate_date(prev_date)
            comparison_line = f'<p class="comparison-info">So sánh: <strong>{prev_date_vn}</strong> vs <strong>{curr_date_vn}</strong></p>'
        except:
            comparison_line = ""

        html_head = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tổng hợp khuyến mãi | Daily Promotion</title>
            <!-- Fonts -->
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
            
            <style>
                :root {{
                    --bg-body: #f8fafc;
                    --card-bg: #ffffff;
                    --text-primary: #1e293b;
                    --text-secondary: #64748b;
                    --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    --card-border: rgba(226, 232, 240, 0.8);
                    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
                    --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                    --danger: #ef4444;
                    --success: #10b981;
                }}
                
                body {{ 
                    font-family: 'Inter', sans-serif; 
                    margin: 0; 
                    background-color: var(--bg-body);
                    color: var(--text-primary);
                    min-height: 100vh;
                    padding: 20px;
                }}

                h1, h2, h3 {{ font-family: 'Outfit', sans-serif; }}
                
                /* Nav Bar */
                .nav-container {{ display: flex; justify-content: center; margin-bottom: 30px; }}
                .nav-bar {{
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(0,0,0,0.05);
                    padding: 8px 12px;
                    border-radius: 50px;
                    display: flex; align-items: center; gap: 24px;
                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
                }}
                .nav-logo {{ 
                    color: #1e293b; font-weight: 800; font-family: 'Outfit', sans-serif; font-size: 1.1em; padding-left: 12px; 
                }}
                .nav-links {{ display: flex; gap: 6px; background: #f1f5f9; padding: 4px; border-radius: 30px; }}
                .nav-link {{
                    color: #64748b; text-decoration: none; font-weight: 500; padding: 8px 16px; 
                    border-radius: 20px; transition: all 0.2s ease; font-size: 0.9em;
                }}
                .nav-link:hover {{ color: #1e293b; background: #ffffff; }}
                .nav-link.active {{
                    background: #ffffff; color: #0f172a; font-weight: 600;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}

                /* Header Info */
                .page-header {{ text-align: center; margin-bottom: 30px; }}
                h1 {{ 
                    font-size: 2.5rem; margin-bottom: 5px; 
                    color: #0f172a;
                    letter-spacing: -0.02em;
                }}
                .meta-info {{ color: var(--text-secondary); font-size: 0.9em; }}
                .comparison-info {{ 
                    font-size: 1.1em; color: var(--text-secondary); margin-top: 10px; margin-bottom: 20px; 
                    background: #ffffff; display: inline-block; padding: 8px 16px; border-radius: 12px;
                    border: 1px solid var(--card-border);
                    box-shadow: var(--shadow-sm);
                }}
                
                @media (max-width: 768px) {{
                    .page-header h1 {{ font-size: 2rem; }}
                    .comparison-info {{ font-size: 0.95em; padding: 6px 12px; }}
                    body {{ padding: 20px 10px; }}
                }}

                /* Controls */
                .controls {{ 
                    background: var(--card-bg); 
                    backdrop-filter: blur(12px);
                    padding: 15px 25px; 
                    border-radius: 16px; 
                    margin-bottom: 25px; 
                    display: flex; gap: 20px; align-items: center; flex-wrap: wrap; 
                    border: 1px solid var(--card-border); 
                    position: sticky; top: 20px; z-index: 100; 
                    box-shadow: var(--shadow-card);
                }}
                .control-group {{ display: flex; align-items: center; gap: 10px; }}
                label {{ font-weight: 600; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }}
                
                select, input {{ 
                    background: #f8fafc; 
                    color: #1e293b; 
                    border: 1px solid #cbd5e1; 
                    padding: 8px 12px; border-radius: 8px; 
                    outline: none; transition: border-color 0.2s;
                }}
                select:focus, input:focus {{ border-color: #3b82f6; ring: 2px solid rgba(59, 130, 246, 0.1); }}
                
                #matchCount {{ color: var(--text-secondary); font-size: 0.9em; font-weight: 600; }}

                /* Product Blocks */
                .product-block {{ 
                    background: var(--card-bg); 
                    border: 1px solid var(--card-border); 
                    margin-bottom: 20px; padding: 20px; 
                    border-radius: 16px; 
                    box-shadow: var(--shadow-sm);
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .product-block:hover {{
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-card);
                }}
                
                .product-header {{ 
                    display: flex; justify-content: space-between; align-items: flex-start;
                    border-bottom: 1px solid #e2e8f0; 
                    padding-bottom: 12px; margin-bottom: 15px; 
                }}
                .product-title {{ font-size: 1.1em; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 10px; }}

                .diff-table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; font-size: 0.95em; }}
                .diff-table th, .diff-table td {{ 
                    border: 1px solid #e2e8f0; 
                    padding: 12px; text-align: left; vertical-align: top; width: 50%; color: #334155;
                }}
                .diff-table th {{ background: #f1f5f9; font-weight: 600; color: #475569; font-size: 0.85em; text-transform: uppercase; }}
                
                /* Changes */
                .price-change-down {{ color: var(--success); font-weight: 800; }}
                .price-change-up {{ color: var(--danger); font-weight: 800; }}
                
                .added {{ background: rgba(16, 185, 129, 0.1); color: #059669; padding: 2px 6px; border-radius: 4px; }}
                .removed {{ background: rgba(239, 68, 68, 0.1); color: #dc2626; text-decoration: line-through; padding: 2px 6px; border-radius: 4px; opacity: 0.7; }}
                
                .stock-tag {{ font-size: 0.75em; padding: 3px 8px; border-radius: 6px; font-weight: 700; margin-left: 8px; vertical-align: middle; text-transform: uppercase; letter-spacing: 0.5px; }}
                .stock-yes {{ background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }}
                .stock-no {{ background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }}
                
                .text-promo {{ color: #9333ea; font-weight: 600; }} /* Purple */
                .text-payment {{ color: #2563eb; font-weight: 600; }} /* Blue */
                
                .hidden {{ display: none !important; }}
                
                @media (max-width: 800px) {{ 
                    .controls {{ position: static; flex-direction: column; align-items: stretch; gap: 10px; }} 
                    .diff-table th, .diff-table td {{ padding: 8px; font-size: 0.9em; }} 
                    .product-block {{ padding: 15px; }}
                    .product-header {{ flex-direction: column; gap: 8px; }}
                    .product-title {{ font-size: 1em; }}
                }}
                #toggleInsights {{
                    background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
                    color: white; border: none; padding: 10px 20px;
                    border-radius: 20px; font-weight: 600; cursor: pointer;
                    margin: 20px auto; display: block;
                    box-shadow: 0 4px 6px -1px rgba(124, 58, 237, 0.3);
                    transition: transform 0.2s;
                    font-size: 1em;
                }}
                #toggleInsights:hover {{ transform: scale(1.05); }}
                .insights-container {{
                    background: #fff; padding: 30px; border-radius: 16px;
                    margin: 20px 0; border: 1px solid #e2e8f0;
                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
                    animation: fadeIn 0.3s ease-out;
                }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                .insights-container h1, .insights-container h2 {{ color: #4c1d95; margin-top: 1.5em; margin-bottom: 0.5em; }}
                .insights-container h1 {{ font-size: 1.8em; border-bottom: 2px solid #ddd6fe; padding-bottom: 10px; margin-top: 0; }}
                .insights-container h2 {{ font-size: 1.4em; }}
                .insights-container ul {{ padding-left: 20px; color: #374151; line-height: 1.6; }}
                .insights-container li {{ margin-bottom: 8px; }}
                .insights-container strong {{ color: #1e40af; }}
                .insights-container em {{ color: #6b7280; font-style: italic; }}
            </style>
        </head>
        <body>
            <div class="nav-container">
                <div class="nav-bar">
                    <div class="nav-logo">🚀 Daily Promotion</div>
                    <div class="nav-links">
                        <a href="index.html" class="nav-link active">Trang chủ</a>
                        <a href="tools.html" class="nav-link">Công cụ</a>
                    </div>
                </div>
            </div>
            
            <style>
                @media (max-width: 768px) {{
                    .nav-container {{ margin-bottom: 25px; }}
                    .nav-bar {{ gap: 8px; padding: 6px 8px; width: auto; justify-content: center; }}
                    .nav-logo {{ font-size: 1em; padding-left: 5px; }}
                    .nav-links {{ gap: 4px; }}
                    .nav-link {{ padding: 6px 10px; font-size: 0.85em; }}
                }}
            </style>

            <div class="page-header">
                <h1>Tổng hợp khuyến mãi</h1>
                <p class="meta-info">Cập nhật lúc: {pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M')}</p>
                {comparison_line}
            </div>
            
            <!-- AI Insights Section -->
            {self._get_latest_insights_html()}
            
            <script>
                function toggleInsights() {{
                    const panel = document.getElementById('insightsPanel');
                    if (panel.classList.contains('hidden')) {{
                        panel.classList.remove('hidden');
                        document.getElementById('toggleInsights').innerText = "❌ Đóng Phân Tích";
                    }} else {{
                        panel.classList.add('hidden');
                        document.getElementById('toggleInsights').innerText = "📊 Xem Phân Tích AI";
                    }}
                }}
            </script>
            
            <div class="controls">
                 <div class="control-group">
                    <label for="dateFilter">Ngày</label>
                    <select id="dateFilter">
                        <option value="ALL">Tất cả ngày</option>
                        {date_opts}
                    </select>
                </div>
                <div class="control-group">
                    <label for="channelFilter">Kênh</label>
                    <select id="channelFilter">
                        <option value="ALL">Tất cả kênh</option>
                        {channel_opts}
                    </select>
                </div>
                <div class="control-group">
                    <label for="stockFilter">Kho hàng</label>
                    <select id="stockFilter">
                        <option value="ALL">Tất cả</option>
                        <option value="YES">Còn hàng</option>
                        <option value="NO">Hết hàng</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="promoFilter">Thay đổi KM</label>
                    <select id="promoFilter">
                        <option value="YES">Có thay đổi</option>
                        <option value="ALL" selected>Tất cả</option>
                        <option value="NO">Không đổi</option>
                        <option value="NEW">Mới</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="priceFilter">Giá</label>
                    <select id="priceFilter">
                        <option value="ALL">Tất cả</option>
                        <option value="UP">Tăng Giá</option>
                        <option value="DOWN">Giảm Giá</option>
                        <option value="NO">Không Đổi</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="sortPrice">Sắp xếp</label>
                    <select id="sortPrice">
                        <option value="DEFAULT">Mặc định</option>
                        <option value="ASC">Giá: Thấp -> Cao</option>
                        <option value="DESC">Giá: Cao -> Thấp</option>
                    </select>
                </div>
                <div class="control-group" style="flex-grow: 1;">
                    <input type="text" id="searchInput" placeholder="Tìm sản phẩm..." style="width: 100%;">
                </div>
                 <div class="control-group">
                    <span id="matchCount">Đang tải...</span>
                </div>
            </div>
            
            <div id="report-container">
        """
        
        container_content = ""
        for index, row in self.df.iterrows():
            container_content += self._render_block(row, index)
            
        html_foot = """
            </div>
            
            <script>
                // DEBUG: Robust Error Handling
                window.onerror = function(msg, url, lineNo, columnNo, error) {
                    const status = document.getElementById('matchCount');
                    if (status) status.innerHTML = `<span style="color:red; font-weight:bold;">JS Error: ${msg} (Line ${lineNo})</span>`;
                    return false;
                };

                function debounce(func, wait) {
                    let timeout;
                    return function(...args) {
                        clearTimeout(timeout);
                        timeout = setTimeout(() => func.apply(this, args), wait);
                    };
                }

                document.addEventListener('DOMContentLoaded', () => {
                    try {
                        const dateSelect = document.getElementById('dateFilter');
                        const channelSelect = document.getElementById('channelFilter');
                        const stockSelect = document.getElementById('stockFilter');
                        const promoSelect = document.getElementById('promoFilter');
                        const priceSelect = document.getElementById('priceFilter');
                        const sortSelect = document.getElementById('sortPrice');
                        const searchInput = document.getElementById('searchInput');
                        const matchCountDisplay = document.getElementById('matchCount');
                        const reportContainer = document.getElementById('report-container');
                        
                        // Check if critical elements exist
                        if (!matchCountDisplay || !reportContainer) {
                            console.error("Critical elements missing");
                            return;
                        }

                        // Optimization 1: Cache DOM elements and Data
                        const productBlocks = Array.from(document.querySelectorAll('.product-block'));
                        
                        // Pre-parse data for fast filtering
                        const productData = productBlocks.map(block => ({
                            element: block,
                            date: block.getAttribute('data-date'),
                            channel: block.getAttribute('data-channel'),
                            stock: (block.getAttribute('data-stock') || "").toLowerCase(),
                            promoChange: block.getAttribute('data-promo-change'), 
                            status: block.getAttribute('data-status'),
                            priceChange: block.getAttribute('data-price-change'),
                            searchIndex: (block.getAttribute('data-search-content') || "").toLowerCase(),
                            price: parseFloat(block.getAttribute('data-price')) || 0,
                            index: parseInt(block.getAttribute('data-index')) || 0
                        }));

                        function updateView() {
                            try {
                                const selectedDate = dateSelect ? dateSelect.value : 'ALL';
                                const selectedChannel = channelSelect ? channelSelect.value : 'ALL';
                                const selectedStock = stockSelect ? stockSelect.value : 'ALL';
                                const selectedPromo = promoSelect ? promoSelect.value : 'ALL';
                                const selectedPrice = priceSelect ? priceSelect.value : 'ALL';
                                const sortMode = sortSelect ? sortSelect.value : 'DEFAULT';
                                
                                // Tokenize search terms (AND logic)
                                const rawSearch = searchInput ? searchInput.value.toLowerCase().trim() : "";
                                // Use explicit backslash for regex to satisfy Python and JS
                                const searchTokens = rawSearch.split(/\\s+/).filter(t => t.length > 0);
                                
                                let visibleCount = 0;
                                let needsSort = (sortMode !== 'DEFAULT');
                                
                                // 1. Filter Loop (Fast memory check)
                                productData.forEach(item => {
                                    const matchesDate = (selectedDate === 'ALL' || item.date === selectedDate);
                                    const matchesChannel = (selectedChannel === 'ALL' || item.channel === selectedChannel);
                                    
                                    // Stock Filter
                                    let matchesStock = true;
                                    if (selectedStock === 'YES') matchesStock = item.stock.includes('yes');
                                    else if (selectedStock === 'NO') matchesStock = !item.stock.includes('yes');
                                    
                                    // Promo Filter Logic
                                    let matchesPromo = false;
                                    if (selectedPromo === 'ALL') matchesPromo = true;
                                    else if (selectedPromo === 'YES') matchesPromo = (item.status === 'CHANGED' || item.status === 'NEW');
                                    else if (selectedPromo === 'NO') matchesPromo = (item.status === 'UNCHANGED');
                                    else if (selectedPromo === 'NEW') matchesPromo = (item.status === 'NEW');

                                    const matchesPrice = (selectedPrice === 'ALL' || item.priceChange === selectedPrice);
                                    
                                    // Global Search
                                    let matchesSearch = true;
                                    if (searchTokens.length > 0) {
                                        if (!item.searchIndex.includes(searchTokens[0])) {
                                            matchesSearch = false;
                                        } else {
                                            for (let i = 1; i < searchTokens.length; i++) {
                                                if (!item.searchIndex.includes(searchTokens[i])) {
                                                    matchesSearch = false;
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    if (matchesDate && matchesChannel && matchesPromo && matchesSearch && matchesPrice && matchesStock) {
                                        item.element.classList.remove('hidden');
                                        item.isVisible = true;
                                        visibleCount++;
                                    } else {
                                        item.element.classList.add('hidden');
                                        item.isVisible = false;
                                    }
                                });
                                
                                // 2. Sort Logic
                                if (needsSort) {
                                    const visibleItems = productData.filter(i => i.isVisible);
                                    visibleItems.sort((a, b) => {
                                        if (sortMode === 'ASC') return a.price - b.price;
                                        else if (sortMode === 'DESC') return b.price - a.price;
                                        return a.index - b.index;
                                    });
                                    const fragment = document.createDocumentFragment();
                                    visibleItems.forEach(item => fragment.appendChild(item.element));
                                    reportContainer.innerHTML = ''; 
                                    reportContainer.appendChild(fragment);
                                } else {
                                     const visibleItems = productData.filter(i => i.isVisible);
                                     visibleItems.sort((a, b) => a.index - b.index);
                                     const fragment = document.createDocumentFragment();
                                     visibleItems.forEach(item => fragment.appendChild(item.element));
                                     reportContainer.innerHTML = '';
                                     reportContainer.appendChild(fragment);
                                }
                                
                                matchCountDisplay.textContent = `Hiển thị ${visibleCount} mục`;
                                
                            } catch (err) {
                                console.error("UpdateView Error", err);
                                matchCountDisplay.innerHTML = `<span style="color:red">Error: ${err.message}</span>`;
                            }
                        }
                        
                        const debouncedUpdate = debounce(updateView, 300);

                        // Event Listeners - check existence first
                        if(dateSelect) dateSelect.addEventListener('change', updateView);
                        if(channelSelect) channelSelect.addEventListener('change', updateView);
                        if(stockSelect) stockSelect.addEventListener('change', updateView);
                        if(promoSelect) promoSelect.addEventListener('change', updateView);
                        if(priceSelect) priceSelect.addEventListener('change', updateView);
                        if(sortSelect) sortSelect.addEventListener('change', updateView);
                        if(searchInput) searchInput.addEventListener('input', debouncedUpdate);
                        
                        // Init view
                        setTimeout(() => updateView(), 10);
                        
                    } catch (e) {
                        const disp = document.getElementById('matchCount');
                        if(disp) disp.innerHTML = "Init Error: " + e.message;
                    }
                });
            </script>
        </body>
        </html>
        """
        
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(html_head + container_content + html_foot)
            print(f"HTML Report saved to: {self.output_file}")
        except Exception as e:
            print(f"Error saving HTML: {e}")

    def _translate_date(self, date_str):
        if not isinstance(date_str, str) or len(date_str) < 3:
            return date_str
        
        # Mapping for day suffix
        # Inputs like '2025-12-25-WED' or '2025-12-25-THU'
        suffix = date_str[-3:].upper()
        mapping = {
            'MON': 'T2',
            'TUE': 'T3',
            'WED': 'T4',
            'THU': 'T5',
            'FRI': 'T6',
            'SAT': 'T7',
            'SUN': 'CN'
        }
        
        if suffix in mapping:
            return date_str[:-3] + mapping[suffix]
        
        return date_str

    def _render_block(self, row, index):
        channel = row.get('Channel', 'Unknown')
        product = row.get('Product Name', 'Unknown')
        color = row.get('Color', 'Unknown')
        date = row.get('Date', '')
        prev_date = row.get('Prev_Date', '')
        status = row.get('Status', 'UNCHANGED')
        
        # Normalize Stock for HTML Attribute
        raw_stock = str(row.get('Stock', 'Unknown')).lower()
        stock_val = "YES" if "yes" in raw_stock else "NO"

        # Calculate Change Statuses for Filter
        promo_changed = 'NO'
        if status == 'CHANGED' or status == 'NEW':
            promo_changed = 'YES'
        
        price_changed = 'NO'
        current_price = 0
        try:
             p1 = float(row.get('New_Price', 0)) if pd.notna(row.get('New_Price')) else 0
             p2 = float(row.get('Old_Price', 0)) if pd.notna(row.get('Old_Price')) else 0
             current_price = p1
             if status != 'NEW' and p1 > 0 and p2 > 0:
                 if p1 > p2:
                     price_changed = 'UP'
                 elif p1 < p2:
                     price_changed = 'DOWN'
        except: pass

        # Price Display Logic
        price_html = self._get_price_html(row)
        
        # Link Logic
        link_url = row.get('Link', '')
        link_html = ""
        if pd.notna(link_url) and link_url != "":
            link_html = f'<div style="margin-bottom: 15px;"><a href="{link_url}" target="_blank" style="font-size: 0.9em; color: #2563eb; text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 4px;">View Product <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg></a></div>'

        # Styling based on Status
        # Default Light Mode Border
        border_style = "border: 1px solid var(--card-border);" 
        badge_html = ""
        
        if status == "NEW":
            border_style = "border: 1px solid rgba(16, 185, 129, 0.4); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);"
            badge_html = '<span style="background: #ecfdf5; color: #059669; font-size: 0.7em; padding: 2px 8px; border-radius: 12px; margin-left: 8px; font-weight: 700; border: 1px solid #a7f3d0;">NEW</span>'
        elif status == "CHANGED":
             border_style = "border: 1px solid rgba(245, 158, 11, 0.5);" # Warning/Amber
        
        # Stock Badge
        stock_badge = ""
        if stock_val == "YES":
             stock_badge = '<span class="stock-tag stock-yes">In Stock</span>'
        else:
             stock_badge = '<span class="stock-tag stock-no">Out of Stock</span>'

        safe_channel = html.escape(str(channel))
        safe_product = html.escape(str(product)).lower()
        safe_date = html.escape(str(date))
        
        # Determine Label
        # User requested channel NAME instead of ICON
        channel_badges = {
            "Viettel": ("ViettelStore", "#fee2e2", "#991b1b"), # Red
            "FPT": ("FPT Shop", "#f1f5f9", "#0f172a"),       # Dark
            "HoangHa": ("HoangHa", "#dcfce7", "#166534"),     # Green
            "DDV": ("DiDongViet", "#fae8ff", "#86198f"),      # Purple
            "CPS": ("CellphoneS", "#eff6ff", "#1e40af"),      # Blue
            "MW": ("TheGioiDiDong", "#fef9c3", "#854d0e")     # Yellow
        }
        
        display_name = safe_channel
        bg_col = "#f1f5f9"
        text_col = "#334155"
        
        for key, (name, bg, txt) in channel_badges.items():
            if key in str(channel):
                display_name = name
                bg_col = bg
                text_col = txt
                break

        icon_html = f'<span style="background: {bg_col}; color: {text_col}; padding: 4px 8px; border-radius: 6px; font-size: 0.8em; font-weight: 700; margin-right: 8px;">{display_name}</span>'

        # --- Global Search Index Generation ---
        # Combine all relevant fields into one normalized string
        # FIX: Include display_name so users can search "TheGioiDiDong" (MW) or "CellphoneS" (CPS)
        search_terms = [
            str(channel), str(display_name), str(product), str(color), 
            str(row.get('Promotion Details', '')), 
            str(row.get('Payment Promo', '')),
            "{:,.0f}".format(p1) if p1 > 0 else "", # New Price
            "{:,.0f}".format(p2) if p2 > 0 else ""  # Old Price
        ]
        search_raw = " ".join([t for t in search_terms if pd.notna(t) and str(t).strip() != ""])
        safe_search_index = html.escape(search_raw).lower()
        # --------------------------------------

        block = f"""
        <div class="product-block" 
             style="{border_style}"
             data-index="{index}"
             data-channel="{safe_channel}" 
             data-product="{safe_product}" 
             data-date="{safe_date}" 
             data-stock="{stock_val}"
             data-promo-change="{promo_changed}" 
             data-price-change="{price_changed}"
             data-status="{status}"
             data-search-content="{safe_search_index}"
             data-search-content="{safe_search_index}"
             data-price="{current_price}">
            <div class="product-header">
                <div class="product-title">
                    {icon_html}
                    <span>{product}</span>
                    <span style="opacity: 0.6; font-weight: 400; font-size: 0.9em;">({color})</span>
                    {badge_html} 
                    {stock_badge}
                </div>
                {price_html}
            </div>
            {link_html}
        """
        
        if 'Changed_Promotion Details' in row:
             block += self._render_section(row, "Khuyến Mãi", "Old_Promotion Details", "New_Promotion Details", "text-promo", row.get('Changed_Promotion Details'))
             
        if 'Changed_Payment Promo' in row:
             block += self._render_section(row, "Ưu Đãi Thanh Toán", "Old_Payment Promo", "New_Payment Promo", "text-payment", row.get('Changed_Payment Promo'))

        block += "</div>"
        return block

    def _get_price_html(self, row):
        old_price = row.get('Old_Price', '')
        new_price = row.get('New_Price', '')
        
        # Helper
        def fmt(p):
            if pd.isna(p) or str(p).strip() == "" or str(p).lower() == "nan": return None, None
            try: 
                val = float(p)
                if val == 0: return None, "Liên hệ" 
                return val, "{:,.0f}".format(val)
            except: return None, str(p)

        old_val, old_str = fmt(old_price)
        new_val, new_str = fmt(new_price)
        
        if not old_str and not new_str:
            return ""
            
        if old_val is not None and new_val is not None:
            diff = new_val - old_val
            diff_str = "{:,.0f}".format(diff)
            if diff > 0: diff_str = f"+{diff_str}"
            
            if diff < 0:
                return f'<span class="price-tag">{new_str} <span class="price-change-down">({diff_str})</span></span>'
            elif diff > 0:
                return f'<span class="price-tag">{new_str} <span class="price-change-up">({diff_str})</span></span>'
            
        # Fallback / No Diff / One is Missing / One is "Liên hệ"
        if new_str:
             if hasattr(self, 'price_gen') and new_str == "Liên hệ":
                  # Optional style for Contact
                  return f'<span class="price-tag" style="font-size:0.9em; color:#666;">{new_str}</span>'
             return f'<span class="price-tag">{new_str}</span>'

        if old_str:
            return f'<span class="price-tag" style="text-decoration: line-through; color: #999;">{old_str}</span>'
            
        return ""

    def _render_section(self, row, title, old_col, new_col, css_class="", change_status=None):
        old_raw = row.get(old_col, "")
        new_raw = row.get(new_col, "")
        
        if (pd.isna(old_raw) or old_raw == "") and (pd.isna(new_raw) or new_raw == ""):
             return f"""
            <div class="section-title {css_class}">{title}</div>
            <div style="color: #6c757d; font-style: italic; margin-left:15px; margin-top:5px; font-size: 0.95em;">
                Không có dữ liệu
            </div>
            """
            
        if change_status == 'NO':
             # Render Toggleable Section
             # It contains both Old and New (which are same) or just one of them.
             # Let's show "Prev" content as it represents the static state.
             
             content_html = self._render_static_content(row, old_col)
             # Sanitize ID to be safe for JS (alphanumeric only)
             raw_id = f"toggle-{title}-{row.get('Channel')}-{row.get('Product Name')}-{row.get('Color')}" + str(id(row))
             unique_id = re.sub(r'[^a-zA-Z0-9]', '_', raw_id)
             
             return f"""
            <div class="section-title {css_class}">{title}</div>
            <div style="color: #6c757d; font-style: italic; margin-left:15px; margin-top:5px; font-size: 0.95em;">
                Không có thay đổi 
                <a href="javascript:void(0)" onclick="document.getElementById('{unique_id}').classList.toggle('hidden');" style="font-size: 0.9em; text-decoration: underline; margin-left: 5px;">(Xem chi tiết)</a>
            </div>
            <div id="{unique_id}" class="hidden" style="margin-top: 10px; border-left: 3px solid #eee; padding-left: 10px;">
                {content_html}
            </div>
            """

        old_items = self._parse_items(old_raw)
        new_items = self._parse_items(new_raw)
        
        common = old_items.intersection(new_items)
        removed = old_items - new_items
        added = new_items - common
        
        def build_list(items, css_class):
            if not items: return ""
            lis = "".join([f"<li class='{css_class}'>{html.escape(i)}</li>" for i in sorted(list(items))])
            return f"<ul class='diff-list'>{lis}</ul>"

        left_content = build_list(removed, 'removed') + build_list(common, 'common')
        right_content = build_list(added, 'added') + build_list(common, 'common')
        
        d1 = row.get('Prev_Date', 'Old')
        d2 = row.get('Date', 'New')
        
        return f"""
        <div class="section-title {css_class}">{title}</div>
        <table class="diff-table">
            <thead>
                <tr>
                    <th>{d1}</th>
                    <th>{d2}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{left_content}</td>
                    <td>{right_content}</td>
                </tr>
            </tbody>
        </table>
        """

    def _render_static_content(self, row, col_name):
        raw_text = row.get(col_name, "")
        items = self._parse_items(raw_text)
        if not items: return "<em>Không có dữ liệu chi tiết</em>"
        
        lis = "".join([f"<li>{html.escape(i)}</li>" for i in sorted(list(items))])
        return f"<ul class='diff-list' style='color: #666;'>{lis}</ul>"

    def _parse_items(self, text):
        if pd.isna(text) or str(text).strip() == "":
            return set()
        items = str(text).split('|')
        return {item.strip() for item in items if item.strip()}

def get_available_dates(base_path):
    if not os.path.exists(base_path):
        print(f"❌ Lỗi: Không tìm thấy thư mục dữ liệu: {base_path}")
        return []
    
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    dates = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and date_pattern.match(d)]
    return sorted(dates, reverse=True)

def select_dates(available_dates):
    if not available_dates:
        print("❌ Không tìm thấy thư mục dữ liệu nào trong BASE_DIR.")
        return None, None

    print("\n" + "="*40)
    print("📅 CÁC NGÀY CÓ DỮ LIỆU HIỆN CÓ")
    print("="*40)
    for i, d in enumerate(available_dates):
        print(f" [{i}] Ngày: {d}")
    print("="*40)
    
    try:
        new_prompt = f"\n👉 Chọn số thứ tự ngày MỚI NHẤT [Mặc định 0 ({available_dates[0]})]: "
        new_idx = int(input(new_prompt) or 0)
        
        default_old = min(1, len(available_dates)-1)
        old_prompt = f"👉 Chọn số thứ tự ngày CŨ HƠN để so sánh [Mặc định {default_old} ({available_dates[default_old]})]: "
        old_idx = int(input(old_prompt) or default_old)
        
        if new_idx < 0 or new_idx >= len(available_dates) or old_idx < 0 or old_idx >= len(available_dates):
            print("⚠️ Lựa chọn không hợp lệ. Vui lòng thử lại.")
            return None, None
            
        return available_dates[new_idx], available_dates[old_idx]
    except ValueError:
        print("⚠️ Vui lòng chỉ nhập số thứ tự từ danh sách trên.")
        return None, None


def main():
    parser = argparse.ArgumentParser(description="Daily Promotion Report Generator")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode (prompt for dates)")
    args = parser.parse_args()

    # Determine Base Directory
    base_dir = BASE_DIR
    
    target_dates = DATES
    is_interactive = args.interactive
    
    print(f"🚀 --- BẮT ĐẦU TẠO BÁO CÁO (Interactive: {is_interactive}) ---")
    print(f"📁 Thư mục nguồn: {base_dir}")

    output_html_path = PROMO_DIFF_HTML

    if is_interactive:
        available = get_available_dates(base_dir)
        newer, older = select_dates(available)
        if not newer or not older:
             print("❌ Quá trình chọn ngày bị hủy hoặc thất bại.")
             return
        target_dates = [older, newer]
        print(f"\n🔄 Đang so sánh: {older} (Cũ) ➔ {newer} (Mới)...")
        
        # In interactive, we might want a specific filename or just default
        # Let's keep default docs/index.html so it works with GitHub pages
    
    # 1. Load Data
    # Pass target_dates and base_dir directly to DataLoader
    
    df = DataLoader.load_all_data(dates=target_dates, base_dir=base_dir)
    print(f"📊 Tổng số dòng dữ liệu đã tải: {len(df)}")
    
    if df.empty:
        print("❌ Không có dữ liệu. Đang thoát.")
        return
    
    # 2. Price Matrix
    # Use skip_csv=True to avoid generating the matrix CSV file as requested
    price_gen = PriceMatrixGenerator(df, skip_csv=True)
    price_gen.run()
    
    # 3. Promo Diff
    # If interactive, skip CSV and maybe use specific HTML output?
    # For now, we overwrite docs/index.html as requested.
    # Enable include_all=True to allow "Show All" in HTML
    promo_gen = PromoDiffGenerator(df, price_gen, output_file=output_html_path, skip_csv=is_interactive, include_all=True)
    promo_gen.run()
    
    print("\n" + "✨"*20)
    print("🎯 QUÁ TRÌNH HOÀN TẤT THÀNH CÔNG!")
    if is_interactive:
        print(f"📌 Xem báo cáo tại: {output_html_path}")
    print("✨"*20 + "\n")

if __name__ == "__main__":
    main()
