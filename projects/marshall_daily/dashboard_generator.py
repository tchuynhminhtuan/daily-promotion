import os
import pandas as pd
import glob
import json
from datetime import datetime

def generate_dashboard():
    # 1. Load all CSVs
    content_path = os.path.join(os.path.dirname(__file__), "content/*.csv")
    csv_files = glob.glob(content_path)
    csv_files.sort() # Ensure temporal order
    
    if not csv_files:
        print("No CSV files found in content/.")
        return

    all_data = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, sep=";")
            all_data.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not all_data:
        return

    main_df = pd.concat(all_data, ignore_index=True)
    main_df['Price'] = pd.to_numeric(main_df['Price'], errors='coerce').fillna(0).astype(int)
    
    # Latest Data for Table
    latest_date = main_df['Date'].max().split()[0]
    latest_df = main_df[main_df['Date'].str.contains(latest_date)].copy()
    
    # Sort by Price
    latest_df = latest_df.sort_values(by="Price", ascending=True)

    # 2. Prepare Chart Data (Trend for a few top models)
    # Group by Date and Site for Acton III (sample model)
    # We'll just pick the top 5 unique products by name frequency
    top_products = latest_df['Product Name'].value_counts().head(5).index.tolist()
    
    chart_data = {}
    for prod in top_products:
        prod_df = main_df[main_df['Product Name'] == prod].copy()
        prod_df['ShortDate'] = prod_df['Date'].apply(lambda x: x.split()[0])
        # Group by date/site to get min price
        trend = prod_df.groupby(['ShortDate', 'Site'])['Price'].min().unstack().fillna(0).to_dict()
        chart_data[prod] = trend

    # 3. HTML Template
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Marshall Daily Tracker</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --accent: #f59e0b;
            --text: #f8fafc;
            --muted: #94a3b8;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            max-width: 1200px;
            width: 100%;
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(to right, #f59e0b, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }}
        .table-container {{
            overflow-x: auto;
            background: var(--card-bg);
            border-radius: 16px;
            padding: 20px;
             border: 1px solid rgba(255,255,255,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        th {{
            color: var(--muted);
            font-weight: 500;
        }}
        .price {{
            color: var(--accent);
            font-weight: 700;
        }}
        .stock-yes {{ color: #10b981; }}
        .stock-no {{ color: #ef4444; }}
        a {{ color: inherit; text-decoration: none; border-bottom: 1px solid var(--accent); }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .site-fpt {{ background: #ea580c22; color: #ea580c; border: 1px solid #ea580c; }}
        .site-mw {{ background: #fbbf2422; color: #fbbf24; border: 1px solid #fbbf24; }}
        .site-cps {{ background: #dc262622; color: #dc2626; border: 1px solid #dc2626; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Marshall Daily Price Tracker</h1>
            <p style="color: var(--muted)">Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </header>

        <div class="grid">
            <div class="card">
                <h3>Price Trends</h3>
                <canvas id="trendChart"></canvas>
            </div>
            <div class="card">
                <h3>Market Summary</h3>
                <div style="font-size: 2rem; font-weight: 700; color: var(--accent)">{len(latest_df)}</div>
                <p style="color: var(--muted)">Live Products Tracked Today</p>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0;">
                <div style="display: flex; justify-content: space-between;">
                    <span>FPT: {len(latest_df[latest_df['Site'] == 'FPT'])}</span>
                    <span>MW: {len(latest_df[latest_df['Site'] == 'MW'])}</span>
                    <span>CPS: {len(latest_df[latest_df['Site'] == 'CPS'])}</span>
                </div>
            </div>
        </div>

        <div class="table-container">
            <h3>Live Price List (Best Prices First)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Site</th>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Links</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for _, row in latest_df.iterrows():
        site_cls = f"site-{row['Site'].lower()}"
        stock_cls = "stock-yes" if row['Stock'] == 'Yes' else "stock-no"
        price_fmt = f"{row['Price']:,} \u20AB".replace(",", ".")
        html_content += f"""
                    <tr>
                        <td><span class="badge {site_cls}">{row['Site']}</span></td>
                        <td>{row['Product Name']}</td>
                        <td><span class="price">{price_fmt}</span></td>
                        <td><span class="{stock_cls}">{row['Stock']}</span></td>
                        <td><a href="{row['Link']}" target="_blank">View</a></td>
                    </tr>
        """

    html_content += f"""
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        const data = {json.dumps(chart_data)};
        
        // Simplified trend chart for the first product
        const firstProd = Object.keys(data)[0];
        const prodData = data[firstProd];
        const labels = Object.keys(prodData);
        
        // Flatten sites
        const sites = ['FPT', 'MW', 'CPS'];
        const datasets = sites.map(site => ({{
            label: site,
            data: labels.map(date => prodData[date] ? prodData[date][site] || 0 : 0),
            borderColor: site === 'FPT' ? '#ea580c' : (site === 'MW' ? '#fbbf24' : '#dc2626'),
            fill: false,
            tension: 0.1
        }})).filter(ds => ds.data.some(v => v > 0));

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: datasets
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'top', labels: {{ color: '#f8fafc' }} }},
                    title: {{ display: true, text: 'Price Trend: ' + firstProd, color: '#f8fafc' }}
                }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    output_html = os.path.join(os.path.dirname(__file__), "index.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard generated at {output_html}")

if __name__ == "__main__":
    generate_dashboard()
