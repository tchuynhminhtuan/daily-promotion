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
        print(f"🔄 Auto-selecting latest dates from {len(available_dates)} available...")
        DATES = available_dates[-2:]
        print(f"✅ Selected: {DATES}")
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
        "2025-12-19", "2025-12-20"
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
    "Link": "Link"
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
    
    def __init__(self, df, price_generator, output_file=None, skip_csv=False):
        self.df = df
        self.price_gen = price_generator
        self.output_file = output_file or PROMO_DIFF_CSV # Default if not provided
        self.skip_csv = skip_csv

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
            # If output_file is a CSV path, derive HTML path or use default
            # But usually for interactive we might pass a specific HTML path
            # Let's standardize: If skip_csv is True, output_file might be HTML
            
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
        df = df.sort_values(by=['Channel', 'Product Name', 'Color', '_RawDate'])
        
        cols_to_compare = ['Promotion Details', 'Payment Promo']
        valid_cols = [c for c in cols_to_compare if c in df.columns]
        
        changes = []
        grouped = df.groupby(['Channel', 'Product Name', 'Color'])
        
        for _, group in grouped:
            if len(group) < 2: continue
            
            for i in range(1, len(group)):
                curr_row = group.iloc[i]
                prev_row = group.iloc[i-1]
                
                # Fetch Prices directly from row since we grouped by price
                curr_price = curr_row.get('Promo Price')
                prev_price = prev_row.get('Promo Price')
                
                # Fallback: If grouping separated them, it's possible we are comparing T1(PriceA) vs T2(PriceB) 
                # ONLY if Text + Channel also match.
                # If prices differ but everything else matches, they are in the SAME group in `grouped` iteration?
                # WAIT. Grouped iteration is by `['Channel', 'Product Name', 'Color']`.
                # If `_collapse_for_promo` produced "Black" (Price 120) and "Silver" (Price 100).
                # Then `grouped` will see Group "Black" and Group "Silver".
                # Loop compares T1 vs T2 for "Black". 
                # So `curr_row` and `prev_row` are correct.
                # Price is just a value in the row now.
                
                has_change = False
                change_record = {
                    "Channel": curr_row['Channel'],
                    "Product Name": curr_row['Product Name'],
                    "Color": curr_row['Color'],
                    "Date": curr_row['Date'],
                    "Prev_Date": prev_row['Date'],
                    "New_Price": curr_price,
                    "Old_Price": prev_price,
                    "Link": curr_row.get('Link', '')
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
                
                # Compare Price (Force inclusion if price changed)
                # Convert to float for comparison safety
                try:
                    p1 = float(curr_price) if pd.notna(curr_price) else 0
                    p2 = float(prev_price) if pd.notna(prev_price) else 0
                    if p1 != p2 and p1 > 0 and p2 > 0:
                        has_change = True
                except:
                    pass

                if has_change:
                    changes.append(change_record)
        
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
        
        html_head = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo cáo So sánh Khuyến mãi</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; line-height: 1.5; color: #333; }}
                h1 {{ color: #2c3e50; font-size: 1.5rem; }}
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
                .hidden {{ display: none !important; }}
                @media (max-width: 600px) {{ .controls {{ position: static; flex-direction: column; align-items: stretch; }} .diff-table th, .diff-table td {{ padding: 5px; }} }}
            </style>
        </head>
        <body>
            <h1>Báo cáo So sánh Khuyến mãi</h1>
            <p style="color: grey;">Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
            
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
                <div class="control-group">
                    <label for="promoFilter">Thay đổi KM:</label>
                    <select id="promoFilter">
                        <option value="ALL">Tất cả</option>
                        <option value="YES">Có thay đổi</option>
                        <option value="NO">Không</option>
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
            container_content += self._render_block(row)
            
        html_foot = """
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const dateSelect = document.getElementById('dateFilter');
                    const channelSelect = document.getElementById('channelFilter');
                    const promoSelect = document.getElementById('promoFilter');
                    const priceSelect = document.getElementById('priceFilter');
                    const searchInput = document.getElementById('searchInput');
                    const productBlocks = document.querySelectorAll('.product-block');
                    const matchCountDisplay = document.getElementById('matchCount');

                    function filterItems() {
                        const selectedDate = dateSelect.value;
                        const selectedChannel = channelSelect.value;
                        const selectedPromo = promoSelect.value;
                        const selectedPrice = priceSelect.value;
                        const searchTerm = searchInput.value.toLowerCase().trim();
                        let visibleCount = 0;

                        productBlocks.forEach(block => {
                            const blockDate = block.getAttribute('data-date');
                            const blockChannel = block.getAttribute('data-channel');
                            const blockPromoChange = block.getAttribute('data-promo-change');
                            const blockPriceChange = block.getAttribute('data-price-change');
                            const blockProduct = block.getAttribute('data-product'); 
                            
                            const matchesDate = (selectedDate === 'ALL' || blockDate === selectedDate);
                            const matchesChannel = (selectedChannel === 'ALL' || blockChannel === selectedChannel);
                            const matchesPromo = (selectedPromo === 'ALL' || blockPromoChange === selectedPromo);
                            const matchesPrice = (selectedPrice === 'ALL' || blockPriceChange === selectedPrice);
                            const matchesSearch = (blockProduct.includes(searchTerm));

                            if (matchesDate && matchesChannel && matchesPromo && matchesSearch && matchesPrice) {
                                block.classList.remove('hidden');
                                visibleCount++;
                            } else {
                                block.classList.add('hidden');
                            }
                        });
                        
                        matchCountDisplay.textContent = `Hiển thị ${visibleCount} mục`;
                    }

                    dateSelect.addEventListener('change', filterItems);
                    channelSelect.addEventListener('change', filterItems);
                    promoSelect.addEventListener('change', filterItems);
                    priceSelect.addEventListener('change', filterItems);
                    searchInput.addEventListener('input', filterItems);
                    
                    filterItems();
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

    def _render_block(self, row):
        channel = row.get('Channel', 'Unknown')
        product = row.get('Product Name', 'Unknown')
        color = row.get('Color', 'Unknown')
        date = row.get('Date', '')
        prev_date = row.get('Prev_Date', '')
        
        # Calculate Change Statuses for Filter
        promo_changed = 'NO'
        if row.get('Changed_Promotion Details') == 'YES' or row.get('Changed_Payment Promo') == 'YES':
            promo_changed = 'YES'
        
        price_changed = 'NO'
        try:
             p1 = float(row.get('New_Price', 0)) if pd.notna(row.get('New_Price')) else 0
             p2 = float(row.get('Old_Price', 0)) if pd.notna(row.get('Old_Price')) else 0
             if p1 > 0 and p2 > 0:
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

        safe_channel = html.escape(str(channel))
        safe_product = html.escape(str(product)).lower()
        safe_date = html.escape(str(date))
        
        block = f"""
        <div class="product-block" 
             data-channel="{safe_channel}" 
             data-product="{safe_product}" 
             data-date="{safe_date}" 
             data-promo-change="{promo_changed}" 
             data-price-change="{price_changed}">
            <div class="product-header">
                <span>{channel} - {product} - {color}</span>
                {price_html}
            </div>
            {link_html}
            <div class="meta-info">So sánh: {prev_date} vs {date}</div>
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
                if val == 0: return None, "0" 
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
            else:
                return f'<span class="price-tag">{new_str}</span>'
                
        if new_str and (not old_str or old_str == "0"):
             return f'<span class="price-tag">{new_str}</span>'

        if old_str and not new_str:
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
             return f"""
            <div class="section-title {css_class}">{title}</div>
            <div style="color: #6c757d; font-style: italic; margin-left:15px; margin-top:5px; font-size: 0.95em;">
                Không có thay đổi
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
    promo_gen = PromoDiffGenerator(df, price_gen, output_file=output_html_path, skip_csv=is_interactive)
    promo_gen.run()
    
    print("\n" + "✨"*20)
    print("🎯 QUÁ TRÌNH HOÀN TẤT THÀNH CÔNG!")
    if is_interactive:
        print(f"📌 Xem báo cáo tại: {output_html_path}")
    print("✨"*20 + "\n")

if __name__ == "__main__":
    main()
