#!/usr/bin/env python3
"""
Generate HTML Report from Normalized Mapping CSV
Uses standardized product names from 10-Normalize_and_Analyze.py output
"""

import pandas as pd
import os
import glob
from datetime import datetime

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
NORMALIZED_DIR = os.path.join(PROJECT_ROOT, "analysis", "normalized")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "index.html")

def load_latest_normalized_csv():
    """Load the most recent normalized mapping CSV"""
    pattern = os.path.join(NORMALIZED_DIR, "normalized_mapping_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No normalized mapping CSV found in {NORMALIZED_DIR}")
    
    latest_file = max(files, key=os.path.getctime)
    print(f"📥 Loading normalized data from: {latest_file}")
    
    df = pd.read_csv(latest_file)
    print(f"📊 Loaded {len(df)} products")
    return df, latest_file

def generate_html_report(df, source_file):
    """Generate interactive HTML report"""
    
    # Get unique retailers and products
    retailers = sorted(df['retailer'].unique())
    products = sorted(df['product_name'].unique())
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    source_basename = os.path.basename(source_file)
    
    html = f"""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>So sánh giá sản phẩm Apple | Daily Promotion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@700;800&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-body: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --accent-blue: #3b82f6;
            --border: #e2e8f0;
            --success: #10b981;
            --danger: #ef4444;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Inter', sans-serif;
            margin: 0;
            background: var(--bg-body);
            color: var(--text-primary);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1, h2 {{ 
            font-family: 'Outfit', sans-serif;
            color: #0f172a;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            letter-spacing: -0.02em;
        }}
        
        .meta {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        label {{
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }}
        
        select, input {{
            padding: 8px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.95rem;
            background: white;
            color: var(--text-primary);
        }}
        
        select:focus, input:focus {{
            outline:  none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }}
        
        #searchInput {{
            min-width: 300px;
            flex: 1;
        }}
        
        .stats {{
            color: var(--text-secondary);
            font-weight: 600;
        }}
        
        .product-grid {{
            display: grid;
            gap: 20px;
        }}
        
        .product-card {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .product-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        
        .product-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }}
        
        .product-name {{
            font-weight: 700;
            font-size: 1.15rem;
            color: #0f172a;
            flex: 1;
        }}
        
        .retailers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .retailer-item {{
            padding: 12px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        
        .retailer-name {{
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 5px;
        }}
        
        .price {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent-blue);
        }}
        
        .best-price {{
            background: #ecfdf5 !important;
            border-color: var(--success) !important;
        }}
        
        .best-price .price {{
            color: var(--success);
        }}
        
        .best-badge {{
            display: inline-block;
            background: var(--success);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-left: 8px;
        }}
        
        .view-link {{
            display: inline-block;
            margin-top: 8px;
            color: var(--accent-blue);
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        .view-link:hover {{
            text-decoration: underline;
        }}
        
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2rem; }}
            .controls {{ flex-direction: column; align-items: stretch; }}
            #searchInput {{ min-width: unset; }}
            .retailers-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 So sánh giá sản phẩm Apple</h1>
            <p class="meta">Cập nhật: {timestamp} | Nguồn: {source_basename}</p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="retailerFilter">Kênh:</label>
                <select id="retailerFilter">
                    <option value="ALL">Tất cả</option>
    """
    
    for retailer in retailers:
        html += f'                    <option value="{retailer}">{retailer}</option>\n'
    
    html += """
                </select>
            </div>
            
            <div class="control-group">
                <label for="categoryFilter">Danh mục:</label>
                <select id="categoryFilter">
                    <option value="ALL">Tất cả</option>
                    <option value="iPhone">iPhone</option>
                    <option value="iPad">iPad</option>
                    <option value="Mac">Mac</option>
                    <option value="Watch">Watch</option>
                </select>
            </div>
            
            <div class="control-group" style="flex: 1;">
                <label for="searchInput">Tìm kiếm:</label>
                <input type="text" id="searchInput" placeholder="Nhập tên sản phẩm...">
            </div>
            
            <div class="stats" id="stats"></div>
        </div>
        
        <div class="product-grid" id="productGrid"></div>
        <div class="no-results" id="noResults" style="display: none;">
            <p>❌ Không tìm thấy sản phẩm phù hợp</p>
        </div>
    </div>
    
    <script>
        const data = """
    
    # Convert dataframe to JSON
    json_data = df.to_json(orient='records')
    html += json_data
    
    html += """;
        
        let allProducts = {};
        
        // Group by product_name
        data.forEach(item => {
            const productName = item.product_name;
            if (!allProducts[productName]) {
                allProducts[productName] = {
                    name: productName,
                    category: item.category,
                    retailers: []
                };
            }
            allProducts[productName].retailers.push({
                retailer: item.retailer,
                price: item.price,
                url: item.url || '#',
                color: item.variant_color || '',
                storage: item.variant_storage || ''
            });
        });
        
        // Convert to array and sort
        let productsList = Object.values(allProducts);
        productsList.sort((a, b) => a.name.localeCompare(b.name));
        
        function renderProducts(products) {
            const grid = document.getElementById('productGrid');
            const noResults = document.getElementById('noResults');
            
            if (products.length === 0) {
                grid.style.display = 'none';
                noResults.style.display = 'block';
                return;
            }
            
            grid.style.display = 'grid';
            noResults.style.display = 'none';
            
            grid.innerHTML = products.map(product => {
                // Find best price
                const prices = product.retailers.map(r => r.price).filter(p => p > 0);
                const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
                
                const retailersHTML = product.retailers
                    .filter(r => r.price > 0)
                    .sort((a, b) => a.price - b.price)
                    .map(r => {
                        const isBest = r.price === minPrice;
                        return `
                            <div class="retailer-item ${isBest ? 'best-price' : ''}">
                                <div class="retailer-name">
                                    ${r.retailer}
                                    ${isBest ? '<span class="best-badge">Tốt nhất</span>' : ''}
                                </div>
                                <div class="price">${r.price.toLocaleString('vi-VN')}đ</div>
                                <a href="${r.url}" target="_blank" class="view-link">Xem sản phẩm →</a>
                            </div>
                        `;
                    }).join('');
                
                return `
                    <div class="product-card">
                        <div class="product-header">
                            <div class="product-name">${product.name}</div>
                        </div>
                        <div class="retailers-grid">
                            ${retailersHTML}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function filterProducts() {
            const retailerFilter = document.getElementById('retailerFilter').value;
            const categoryFilter = document.getElementById('categoryFilter').value;
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            
            let filtered = productsList.filter(product => {
                // Category filter
                if (categoryFilter !== 'ALL' && product.category !== categoryFilter) {
                    return false;
                }
                
                // Retailer filter
                if (retailerFilter !== 'ALL') {
                    const hasRetailer = product.retailers.some(r => r.retailer === retailerFilter);
                    if (!hasRetailer) return false;
                }
                
                // Search filter
                if (searchText && !product.name.toLowerCase().includes(searchText)) {
                    return false;
                }
                
                return true;
            });
            
            // Update stats
            document.getElementById('stats').textContent = 
                `Hiển thị ${filtered.length}/${productsList.length} sản phẩm`;
            
            renderProducts(filtered);
        }
        
        // Event listeners
        document.getElementById('retailerFilter').addEventListener('change', filterProducts);
        document.getElementById('categoryFilter').addEventListener('change', filterProducts);
        document.getElementById('searchInput').addEventListener('input', filterProducts);
        
        // Initial render
        filterProducts();
    </script>
</body>
</html>
    """
    
    return html

def main():
    print("🚀 Generating normalized product report...")
    
    # Load data
    df, source_file = load_latest_normalized_csv()
    
    # Generate HTML
    html = generate_html_report(df, source_file)
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report saved to: {OUTPUT_PATH}")
    print(f"📊 Total products: {len(df)}")
    print(f"🏪 Retailers: {', '.join(sorted(df['retailer'].unique()))}")

if __name__ == "__main__":
    main()
