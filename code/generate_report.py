import argparse
import sys
import pandas as pd
import os
import glob
import re
import html

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

if AUTO_SELECT_DATES:
    available_dates = get_available_dates(BASE_DIR)
    if len(available_dates) >= 2:
        # Strictly compare the two most recent dates found
        DATES = available_dates[-2:]
        print(f"🔄 Auto-selecting the 2 most recent dates: {DATES}")
    elif available_dates:
        DATES = available_dates
        print(f"⚠️ Only found these dates: {DATES}")
    else:
        print("❌ No date folders found in content/. Using fallback.")
        DATES = ["2025-12-19", "2025-12-20"] # Fallback
else:
    # Option 2: Hardcoded manual selection
    DATES = [
        # "2025-11-29", "2025-12-01","2025-12-05", "2025-12-08", 
        "2025-12-20", "2025-12-23"
    ]

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


class DataLoader:
    """Handles loading and normalizing data from multiple CSV sources."""
    
    @staticmethod
    def load_all_data(dates=None, base_dir=None):
        target_dates = dates if dates else DATES
        target_base_dir = base_dir if base_dir else BASE_DIR
        all_data = []
        print("📥 Đang tải dữ liệu...")
        
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
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                
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
             print("💡 Đang xử lý Ma trận Giá (Bỏ qua lưu file CSV)...")
        
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
                    
                    if curr_text != prev_text:
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

class HTMLGenerator:
    def __init__(self, df, output_file):
        self.df = df
        self.output_file = output_file
        
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
            <title>Báo cáo So sánh Khuyến mãi</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; line-height: 1.5; color: #333; }}
                h1 {{ color: #2c3e50; font-size: 1.5rem; margin-bottom: 5px; }}
                .comparison-info {{ font-size: 1.1em; color: #555; margin-top: 0; margin-bottom: 20px; }}
                .controls {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 25px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; border: 1px solid #e9ecef; position: sticky; top: 0; z-index: 1000; }}
                .control-group {{ display: flex; align-items: center; gap: 8px; flex: 1 1 auto; }}
                label {{ font-weight: 600; font-size: 0.9em; white-space: nowrap; }}
                select, input {{ padding: 8px; border-radius: 4px; border: 1px solid #ccc; }}
                .product-block {{ background: #fff; border: 1px solid #dee2e6; margin-bottom: 20px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
                .product-header {{ font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; }}
                .price-change-down {{ color: #28a745; font-weight: bold; }}
                .price-change-up {{ color: #dc3545; font-weight: bold; }}
                .diff-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }}
                .diff-table th, .diff-table td {{ border: 1px solid #eee; padding: 10px; text-align: left; vertical-align: top; width: 50%; }}
                .added {{ background: #d4edda; color: #155724; padding: 2px 4px; border-radius: 2px; }}
                .removed {{ background: #f8d7da; color: #721c24; text-decoration: line-through; padding: 2px 4px; border-radius: 2px; }}
                .stock-tag {{ font-size: 0.75em; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-left: 8px; vertical-align: middle; }}
                .stock-yes {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
                .stock-no {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
                .hidden {{ display: none !important; }}
                @media (max-width: 600px) {{ .controls {{ position: static; flex-direction: column; align-items: stretch; }} .diff-table th, .diff-table td {{ padding: 5px; }} }}
            </style>
        </head>
        <body>
            <h1>Báo cáo So sánh Khuyến mãi</h1>
            <p style="color: grey; margin-bottom: 5px;">Generated: {pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M')}</p>
            {comparison_line}
            
            <div class="controls">
                 <div class="control-group">
                    <label for="dateFilter">Ngày:</label>
                    <select id="dateFilter">
                        <option value="ALL">Tất cả</option>
                        {date_opts}
                    </select>
                </div>
                <div class="control-group">
                    <label for="channelFilter">Kênh:</label>
                    <select id="channelFilter">
                        <option value="ALL">Tất cả</option>
                        {channel_opts}
                    </select>
                </div>
                <!-- Stock Filter -->
                <div class="control-group">
                    <label for="stockFilter">Kho hàng:</label>
                    <select id="stockFilter">
                        <option value="ALL">Tất cả</option>
                        <option value="YES">Còn hàng</option>
                        <option value="NO">Hết hàng</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="promoFilter">Thay đổi KM:</label>
                    <select id="promoFilter">
                        <option value="YES" selected>Có thay đổi (Mặc định)</option>
                        <option value="ALL">Tất cả (Bao gồm không đổi)</option>
                        <option value="NO">Không thay đổi</option>
                        <option value="NEW">Mới xuất hiện</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="priceFilter">Thay đổi Giá:</label>
                    <select id="priceFilter">
                        <option value="ALL">Tất cả</option>
                        <option value="UP">Tăng Giá</option>
                        <option value="DOWN">Giảm Giá</option>
                        <option value="NO">Không Đổi</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="sortPrice">Sắp xếp Giá:</label>
                    <select id="sortPrice">
                        <option value="DEFAULT">Mặc định</option>
                        <option value="ASC">Thấp - Cao</option>
                        <option value="DESC">Cao - Thấp</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="searchInput">Tìm kiếm:</label>
                    <input type="text" id="searchInput" placeholder="Ví dụ: iPhone 15...">
                </div>
                 <div class="control-group" style="margin-left: auto;">
                    <span id="matchCount"></span>
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
                document.addEventListener('DOMContentLoaded', function() {
                    const dateSelect = document.getElementById('dateFilter');
                    const channelSelect = document.getElementById('channelFilter');
                    const stockSelect = document.getElementById('stockFilter');
                    const promoSelect = document.getElementById('promoFilter');
                    const priceSelect = document.getElementById('priceFilter');
                    const sortSelect = document.getElementById('sortPrice');
                    const searchInput = document.getElementById('searchInput');
                    const reportContainer = document.getElementById('report-container');
                    let productBlocks = Array.from(document.querySelectorAll('.product-block'));
                    const matchCountDisplay = document.getElementById('matchCount');

                    function updateView() {
                        const selectedDate = dateSelect.value;
                        const selectedChannel = channelSelect.value;
                        const selectedStock = stockSelect.value;
                        const selectedPromo = promoSelect.value; // YES (Default), ALL, NO, NEW
                        const selectedPrice = priceSelect.value;
                        const sortMode = sortSelect.value;
                        const searchTerm = searchInput.value.toLowerCase().trim();
                        
                        let visibleBlocks = [];

                        // 1. Filter
                        productBlocks.forEach(block => {
                            const blockDate = block.getAttribute('data-date');
                            const blockChannel = block.getAttribute('data-channel');
                            const blockStock = block.getAttribute('data-stock');
                            const blockPromoChange = block.getAttribute('data-promo-change'); // YES, NO
                            const blockStatus = block.getAttribute('data-status'); // CHANGED, UNCHANGED, NEW
                            const blockPriceChange = block.getAttribute('data-price-change');
                            const blockProduct = block.getAttribute('data-product'); 
                            
                            const matchesDate = (selectedDate === 'ALL' || blockDate === selectedDate);
                            const matchesChannel = (selectedChannel === 'ALL' || blockChannel === selectedChannel);
                            
                            // Stock Filter
                            let matchesStock = true;
                            if (selectedStock === 'YES') {
                                matchesStock = (blockStock && blockStock.toLowerCase().includes('yes'));
                            } else if (selectedStock === 'NO') {
                                matchesStock = (!blockStock || !blockStock.toLowerCase().includes('yes'));
                            }
                            
                            // Promo Filter Logic
                            let matchesPromo = false;
                            if (selectedPromo === 'ALL') matchesPromo = true;
                            else if (selectedPromo === 'YES') {
                                // YES means Changed OR New (Anything interesting)
                                if (blockStatus === 'CHANGED' || blockStatus === 'NEW') matchesPromo = true;
                            }
                            else if (selectedPromo === 'NO') {
                                if (blockStatus === 'UNCHANGED') matchesPromo = true;
                            }
                            else if (selectedPromo === 'NEW') {
                                if (blockStatus === 'NEW') matchesPromo = true;
                            }

                            const matchesPrice = (selectedPrice === 'ALL' || blockPriceChange === selectedPrice);
                            const matchesSearch = (blockProduct.includes(searchTerm));

                            if (matchesDate && matchesChannel && matchesPromo && matchesSearch && matchesPrice && matchesStock) {
                                block.classList.remove('hidden');
                                visibleBlocks.push(block);
                            } else {
                                block.classList.add('hidden');
                            }
                        });
                        
                        // 2. Sort visible blocks
                        productBlocks.sort((a, b) => {
                            if (sortMode === 'DEFAULT') {
                                return parseInt(a.getAttribute('data-index')) - parseInt(b.getAttribute('data-index'));
                            }
                            
                            const priceA = parseFloat(a.getAttribute('data-price')) || 0;
                            const priceB = parseFloat(b.getAttribute('data-price')) || 0;
                            
                            if (sortMode === 'ASC') {
                                return priceA - priceB;
                            } else { // DESC
                                return priceB - priceA;
                            }
                        });
                        
                        // Re-append to container
                        productBlocks.forEach(block => reportContainer.appendChild(block));
                        
                        matchCountDisplay.textContent = `Hiển thị ${visibleBlocks.length} mục`;
                    }

                    dateSelect.addEventListener('change', updateView);
                    channelSelect.addEventListener('change', updateView);
                    stockSelect.addEventListener('change', updateView);
                    promoSelect.addEventListener('change', updateView);
                    priceSelect.addEventListener('change', updateView);
                    sortSelect.addEventListener('change', updateView);
                    searchInput.addEventListener('input', updateView);
                    
                    updateView();
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
            link_html = f'<div style="margin-bottom: 5px;"><a href="{link_url}" target="_blank" style="font-size: 0.9em; color: #007bff; text-decoration: none;">Xem sản phẩm &rarr;</a></div>'

        # Styling based on Status
        border_style = "border: 1px solid #dee2e6;"
        badge_html = ""
        if status == "NEW":
            border_style = "border: 1px solid #28a745; background-color: #f0fff4;"
            badge_html = '<span style="background: #28a745; color: white; font-size: 0.7em; padding: 2px 5px; border-radius: 3px; margin-left: 5px;">MỚI</span>'
        elif status == "CHANGED":
             border_style = "border: 1px solid #ffc107;" # Warning/Yellow usually for changes
        
        # Stock Badge
        stock_badge = ""
        if stock_val == "YES":
             stock_badge = '<span class="stock-tag stock-yes">Còn hàng</span>'
        else:
             stock_badge = '<span class="stock-tag stock-no">Hết hàng</span>'

        safe_channel = html.escape(str(channel))
        safe_product = html.escape(str(product)).lower()
        safe_date = html.escape(str(date))
        
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
             data-price="{current_price}">
            <div class="product-header">
                <span>{channel} - {product} - {color} {badge_html} {stock_badge}</span>
                {price_html}
            </div>
            {link_html}
        """
        
        if 'Changed_Promotion Details' in row:
             block += self._render_section(row, "Khuyến mãi", "Old_Promotion Details", "New_Promotion Details", "text-promo", row.get('Changed_Promotion Details'))
             
        if 'Changed_Payment Promo' in row:
             block += self._render_section(row, "Thanh toán", "Old_Payment Promo", "New_Payment Promo", "text-payment", row.get('Changed_Payment Promo'))

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
             unique_id = f"toggle-{title}-{row.get('Channel')}-{row.get('Product Name')}-{row.get('Color')}".replace(" ", "_").replace(".", "") + str(id(row))
             
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
    # Priority: Env Var -> Global Config
    base_dir = os.getenv("DAILY_PROMOTION_BASE_DIR", BASE_DIR)
    
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
    price_gen = PriceMatrixGenerator(df, skip_csv=is_interactive)
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
