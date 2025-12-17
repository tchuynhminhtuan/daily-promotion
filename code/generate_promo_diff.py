import pandas as pd
import os
import glob
import re
import html

# Configuration
BASE_DIR = "/Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/content"
# ... imports (keeping existing)
PRICE_MATRIX_FILE = os.path.join(BASE_DIR, "analysis_result", "price_matrix.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "analysis_result", "promo_diff_report.csv")
HTML_OUTPUT_FILE = os.path.join(BASE_DIR, "analysis_result", "promo_diff_readable.html")

DATES = [
    "2025-11-29", "2025-12-01","2025-12-05", "2025-12-08", "2025-12-13", "2025-12-17"
]

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

# New function to load prices
def load_prices():
    """
    Loads the price matrix into a lookup dictionary.
    Key: (Channel, Product Name, Color, Date)
    Value: Price (str or int)
    """
    if not os.path.exists(PRICE_MATRIX_FILE):
        print("Price matrix file not found.")
        return {}
    
    try:
        df_price = pd.read_csv(PRICE_MATRIX_FILE)
        # Melt the dataframe to have a long format: Channel, Product Name, Color, Date, Price
        # Currently columns are like: Channel, Product Name, Color, 2025-11-29-SAT, ...
        
        # Identify date columns (columns that contain '2025')
        date_cols = [c for c in df_price.columns if '2025-' in c and 'Diff_' not in c]
        id_vars = ['Channel', 'Product Name', 'Color']
        
        # Ensure we only stick to valid columns
        valid_date_cols = [c for c in date_cols if c in df_price.columns]
        valid_id_vars = [c for c in id_vars if c in df_price.columns]
        
        melted = df_price.melt(id_vars=valid_id_vars, value_vars=valid_date_cols, var_name='Date', value_name='Price')
        
        # Create lookup
        price_lookup = {}
        for _, row in melted.iterrows():
            key = (row['Channel'], row['Product Name'], row['Color'], row['Date'])
            price_lookup[key] = row['Price']
            
        return price_lookup
    except Exception as e:
        print(f"Error loading price matrix: {e}")
        return {}

def generate_diff(df):
    if df.empty:
        return

    # Load prices
    price_lookup = load_prices()

    # Sort to ensure chronological order for comparison
    df = df.sort_values(by=['Channel', 'Product Name', 'Color', '_RawDate'])
    
    # Identify changes
    cols_to_compare = ['Promotion Details', 'Payment Promo']
    valid_cols = [c for c in cols_to_compare if c in df.columns]
    
    changes = []
    
    # Group by key entities
    grouped = df.groupby(['Channel', 'Product Name', 'Color'])
    
    for name, group in grouped:
        if len(group) < 2:
            continue
            
        for i in range(1, len(group)):
            curr_row = group.iloc[i]
            prev_row = group.iloc[i-1]
            
            # Key for price lookup
            key_curr = (curr_row['Channel'], curr_row['Product Name'], curr_row['Color'], curr_row['Date'])
            key_prev = (prev_row['Channel'], prev_row['Product Name'], prev_row['Color'], prev_row['Prev_Date'] if 'Prev_Date' in prev_row else prev_row['Date']) 
            # Note: prev_row['Date'] is the correct key for the previous date's price
            key_prev_actual = (curr_row['Channel'], curr_row['Product Name'], curr_row['Color'], prev_row['Date'])

            curr_price = price_lookup.get(key_curr, "")
            prev_price = price_lookup.get(key_prev_actual, "")
            
            has_change = False
            change_record = {
                "Channel": curr_row['Channel'],
                "Product Name": curr_row['Product Name'],
                "Color": curr_row['Color'],
                "Date": curr_row['Date'],
                "Prev_Date": prev_row['Date'],
                "New_Price": curr_price,
                "Old_Price": prev_price
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
                    change_record[f"Old_{col}"] = "" 
                    change_record[f"New_{col}"] = ""

            # Check if price changed (optional: add logic to flag pure price changes)
            # For now, we only report if comparison strings changed or if we force it.
            # But the user asked to INTEGRATE price into the report.
            # If price changed but promo didn't, should it show? 
            # Assuming 'Promo Diff' focuses on text, but let's include price in the view.
            # If ONLY price changes, it might NOT trigger this if we only check `valid_cols`.
            # Let's add price change detection.
            
            if str(curr_price) != str(prev_price) and str(curr_price) != "" and str(prev_price) != "": 
                 has_change = True # Trigger report for price change?
                 # If we want to report price changes too, enabling this.

            if has_change:
                changes.append(change_record)
                
    if changes:
        diff_df = pd.DataFrame(changes)
        
        # Save CSV (include prices)
        diff_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Promo Diff Report saved to: {OUTPUT_FILE}")
        
        # Generate HTML Report
        save_html_report(diff_df)
    else:
        print("No changes detected.")

def parse_items(text):
    """Splits text by '|', strips whitespace, and returns a set of items."""
    if pd.isna(text) or str(text).strip() == "":
        return set()
    
    # Text is usually "Item 1 | Item 2 | ..."
    items = str(text).split('|')
    return {item.strip() for item in items if item.strip()}

def save_html_report(df):
    # Get unique channels and dates
    channels = sorted(df['Channel'].unique().tolist()) if not df.empty else []
    channel_options = "".join([f'<option value="{c}">{c}</option>' for c in channels])
    
    dates = sorted(df['Date'].unique().tolist(), reverse=True) if not df.empty else []
    date_options = "".join([f'<option value="{d}">{d}</option>' for d in dates])

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Promotion Difference Report</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; line-height: 1.4; }}
            h1 {{ color: #333; }}
            
            /* ... (keeping existing styles) ... */
            .controls {{
                background: #eee;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
                align-items: center;
                flex-wrap: wrap;
            }}
            .control-group {{ display: flex; align-items: center; gap: 10px; }}
            input[type="text"], select {{ padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; }}
            input[type="text"] {{ width: 300px; }}
            
            .product-block {{ 
                background: #f9f9f9; 
                border: 1px solid #ddd; 
                margin-bottom: 20px; 
                padding: 15px; 
                border-radius: 5px;
            }}
            .product-header {{ 
                font-weight: bold; 
                font-size: 1.1em; 
                margin-bottom: 5px; 
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
                display: flex;
                justify-content: space-between;
            }}
            .price-tag {{ color: #d32f2f; font-weight: bold; }}
            
            .meta-info {{ color: #666; font-size: 0.9em; margin-bottom: 10px; }}
            .diff-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed;}}
            .diff-table th {{ text-align: left; padding: 5px; background: #eee; border-bottom: 2px solid #ccc; width: 50%; }}
            .diff-table td {{ vertical-align: top; padding: 8px; border-bottom: 1px solid #eee; word-wrap: break-word;}}
            
            .diff-list {{ list-style-type: none; padding-left: 0; margin: 0; }}
            .diff-list li {{ padding: 3px 0; border-bottom: 1px dashed #eee; }}
            
            .added {{ color: green; background-color: #e6ffec; text-decoration: none; display: block;}}
            .removed {{ color: red; background-color: #ffe6e6; text-decoration: line-through; display: block; }}
            .common {{ color: #333; }}
            
            .section-title {{ font-weight: bold; margin-top: 10px; color: #555; text-transform: uppercase; font-size: 0.85em; }}
            
            .hidden {{ display: none !important; }}
            
            .price-change-down {{ color: green; font-weight: bold; }}
            .price-change-up {{ color: red; font-weight: bold; }}
            .price-stable {{ color: #333; }}
        </style>
    </head>
    <body>
        <h1>Promotion Changes Report</h1>
        <p>Generated from: {OUTPUT_FILE}</p>
        
        <div class="controls">
             <div class="control-group">
                <label for="dateFilter"><strong>Date:</strong></label>
                <select id="dateFilter">
                    <option value="ALL">All Dates</option>
                    {date_options}
                </select>
            </div>
            <div class="control-group">
                <label for="channelFilter"><strong>Channel:</strong></label>
                <select id="channelFilter">
                    <option value="ALL">All Channels</option>
                    {channel_options}
                </select>
            </div>
            <div class="control-group">
                <label for="searchInput"><strong>Search Product:</strong></label>
                <input type="text" id="searchInput" placeholder="Type to search product name...">
            </div>
             <div class="control-group" style="margin-left: auto;">
                <span id="matchCount"></span>
            </div>
        </div>
    """
    
    if df.empty:
        html_content += "<p>No changes found.</p></body></html>"
    else:
        for index, row in df.iterrows():
            channel = row.get('Channel', 'Unknown')
            product = row.get('Product Name', 'Unknown')
            color = row.get('Color', 'Unknown')
            date = row.get('Date', '')
            prev_date = row.get('Prev_Date', '')
            
            old_price = row.get('Old_Price', '')
            new_price = row.get('New_Price', '')
            
            # Helper for price display
            def format_price(p):
                if pd.isna(p) or str(p).strip() == "" or str(p).lower() == "nan":
                    return ""
                try:
                    return "{:,.0f}".format(float(p))
                except:
                    return str(p)

            formatted_old_price = format_price(old_price)
            formatted_new_price = format_price(new_price)
            
            price_display = ""
            if formatted_old_price or formatted_new_price:
                price_class = "price-stable"
                
                # Default logic
                if formatted_old_price and formatted_new_price:
                    try: 
                        old_val = float(old_price)
                        new_val = float(new_price)
                        diff = new_val - old_val
                        
                        formatted_diff = "{:,.0f}".format(diff)
                        if diff > 0:
                            formatted_diff = f"+{formatted_diff}"
                            
                        # Show Only Diff (User Request: "should be the diff ... not the formatted_new_price")
                        if diff < 0:
                            price_class = "price-change-down"
                            # Green for drop
                            price_display = f'<span class="{price_class}">{formatted_diff}</span>'
                        elif diff > 0:
                            price_class = "price-change-up"
                             # Red for increase
                            price_display = f'<span class="{price_class}">{formatted_diff}</span>'
                        else:
                            # No change, show current price
                            price_display = f'<span>{formatted_new_price}</span>'
                            
                    except:
                        # Fallback if parsing fails
                        if formatted_old_price != formatted_new_price:
                             # Just show change arrow if we can't calculate numeric diff
                             price_display = f'<span style="font-size: 0.9em; color: gray;">{formatted_old_price} &rarr; {formatted_new_price}</span>'
                        else:
                            price_display = f'<span>{formatted_new_price}</span>'
                            
                elif formatted_new_price:
                    # Old price missing, just show new
                     price_display = f'<span>{formatted_new_price}</span>'
                else:
                    # New price missing (delisted?), show old 
                     price_display = f'<span style="text-decoration: line-through; color: #999;">{formatted_old_price}</span>'

            # Escape attributes for safety
            safe_channel = html.escape(str(channel))
            safe_product = html.escape(str(product)).lower() # lower for easier search
            safe_date = html.escape(str(date))

            html_content += f"""
            <div class="product-block" data-channel="{safe_channel}" data-product="{safe_product}" data-date="{safe_date}">
                <div class="product-header">
                    <span>{channel} - {product} - {color}</span>
                    <span class="price-tag">{price_display}</span>
                </div>
                <div class="meta-info">Comparison: {prev_date} vs {date}</div>
            """
            # ... (Existing render_section logic) ... 
            
            # Helper to render a section
            def render_section(title, old_col, new_col):
                old_raw = row.get(old_col, "")
                new_raw = row.get(new_col, "")
                
                if (pd.isna(old_raw) or old_raw == "") and (pd.isna(new_raw) or new_raw == ""):
                    return ""
                    
                old_items = parse_items(old_raw)
                new_items = parse_items(new_raw)
                
                common = old_items.intersection(new_items)
                removed = old_items - new_items
                added = new_items - common
                
                sorted_common = sorted(list(common))
                sorted_removed = sorted(list(removed))
                sorted_added = sorted(list(added))
                
                left_html = "<ul class='diff-list'>"
                for item in sorted_removed:
                    left_html += f"<li class='removed'>{html.escape(item)}</li>"
                for item in sorted_common:
                    left_html += f"<li class='common'>{html.escape(item)}</li>"
                left_html += "</ul>"
                
                right_html = "<ul class='diff-list'>"
                for item in sorted_added:
                    right_html += f"<li class='added'>{html.escape(item)}</li>"
                for item in sorted_common:
                    right_html += f"<li class='common'>{html.escape(item)}</li>"
                right_html += "</ul>"
                
                return f"""
                <div class="section-title">{title}</div>
                <table class="diff-table">
                    <thead>
                        <tr>
                            <th>Old ({prev_date})</th>
                            <th>New ({date})</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{left_html}</td>
                            <td>{right_html}</td>
                        </tr>
                    </tbody>
                </table>
                """

            if 'Changed_Promotion Details' in df.columns:
                 html_content += render_section("Promotion Details", "Old_Promotion Details", "New_Promotion Details")
                 
            if 'Changed_Payment Promo' in df.columns:
                 html_content += render_section("Payment Promotion", "Old_Payment Promo", "New_Payment Promo")

            html_content += "</div>" # End product-block

    html_content += """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const dateSelect = document.getElementById('dateFilter');
            const channelSelect = document.getElementById('channelFilter');
            const searchInput = document.getElementById('searchInput');
            const productBlocks = document.querySelectorAll('.product-block');
            const matchCountDisplay = document.getElementById('matchCount');

            function filterItems() {
                const selectedDate = dateSelect.value;
                const selectedChannel = channelSelect.value;
                const searchTerm = searchInput.value.toLowerCase().trim();
                let visibleCount = 0;

                productBlocks.forEach(block => {
                    const blockDate = block.getAttribute('data-date');
                    const blockChannel = block.getAttribute('data-channel');
                    // Product data is already lowercased in attribute
                    const blockProduct = block.getAttribute('data-product'); 
                    
                    const matchesDate = (selectedDate === 'ALL' || blockDate === selectedDate);
                    const matchesChannel = (selectedChannel === 'ALL' || blockChannel === selectedChannel);
                    const matchesSearch = (blockProduct.includes(searchTerm));

                    if (matchesDate && matchesChannel && matchesSearch) {
                        block.classList.remove('hidden');
                        visibleCount++;
                    } else {
                        block.classList.add('hidden');
                    }
                });
                
                matchCountDisplay.textContent = `Showing ${visibleCount} items`;
            }

            dateSelect.addEventListener('change', filterItems);
            channelSelect.addEventListener('change', filterItems);
            searchInput.addEventListener('input', filterItems);
            
            // Initial count
            filterItems();
        });
    </script>
    </body>
    </html>
    """
    
    try:
        with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML Promo Diff Report saved to: {HTML_OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving HTML report: {e}")

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
