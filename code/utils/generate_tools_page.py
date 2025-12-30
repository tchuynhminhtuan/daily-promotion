import os
import glob
from datetime import datetime

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
GITHUB_REPO = "tchuynhminhtuan/daily-promotion"
BRANCH = "main"

# HTML Template Parts
# Shared Nav Bar (Clean Light Look)
NAV_BAR_HTML = """
<div class="nav-container">
    <div class="nav-bar">
        <div class="nav-logo">🚀 Daily Promotion</div>
        <div class="nav-links">
            <a href="index.html" class="nav-link">Home</a>
            <a href="tools.html" class="nav-link active">Tools</a>
        </div>
        <div class="nav-info">Dashboard v2.0</div>
    </div>
</div>
<style>
    /* Clean Light Nav Styling */
    .nav-container { display: flex; justify-content: center; margin-bottom: 40px; }
    .nav-bar {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(0,0,0,0.05);
        padding: 8px 12px;
        border-radius: 50px;
        display: flex; align-items: center; gap: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
    }
    .nav-logo { 
        color: #1e293b; font-weight: 800; font-family: 'Outfit', sans-serif; font-size: 1.1em; padding-left: 12px; 
    }
    .nav-links { display: flex; gap: 6px; background: #f1f5f9; padding: 4px; border-radius: 30px; }
    .nav-link {
        color: #64748b; text-decoration: none; font-weight: 500; padding: 8px 16px; 
        border-radius: 20px; transition: all 0.2s ease; font-size: 0.9em;
    }
    .nav-link:hover { color: #1e293b; background: #ffffff; }
    .nav-link.active {
        background: #ffffff; color: #0f172a; font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .nav-info { color: #94a3b8; font-size: 0.85em; font-weight: 500; }
</style>
"""

HTML_HEAD = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automation Hub | Daily Promotion</title>
    
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
        }}
        
        body {{ 
            font-family: 'Inter', sans-serif; 
            margin: 0; 
            background-color: var(--bg-body);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        /* Typography */
        h1, h2, h3 {{ font-family: 'Outfit', sans-serif; }}
        
        /* Layout */
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        /* Header Section */
        .header-section {{ text-align: center; margin-bottom: 60px; position: relative; }}
        .header-title {{ 
            font-size: 3.5em; 
            font-weight: 800; 
            color: #0f172a;
            letter-spacing: -0.02em;
            margin-bottom: 10px;
        }}
        .header-subtitle {{ font-size: 1.1em; color: var(--text-secondary); max-width: 600px; margin: 0 auto; line-height: 1.6; }}
        
        /* Grid */
        .tool-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); 
            gap: 24px; 
        }}
        
        /* Card Styling */
        .tool-card {{ 
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: var(--shadow-sm);
            position: relative;
            overflow: hidden;
        }}
        
        .tool-card:hover {{ 
            transform: translateY(-4px); 
            box-shadow: var(--shadow-card); 
            border-color: #cbd5e1;
        }}
<<<<<<< HEAD
=======
        
        .tool-card::before {{ content: none; }}
>>>>>>> 446a32b (feat(ui): switch to apple-style clean light theme)
        
        /* Icon */
        .icon-container {{
            width: 56px; height: 56px;
            background: #f1f5f9;
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 28px;
            margin-bottom: 20px;
        }}
        
        /* Content */
        .card-title {{ font-size: 1.25em; font-weight: 600; margin: 0 0 8px 0; color: #0f172a; }}
<<<<<<< HEAD
        .card-desc {{ color: var(--text-secondary); font-size: 0.95em; line-height: 1.6; flex-grow: 1; margin-bottom: 20px; }}
=======
        .card-desc {{ color: var(--text-secondary); font-size: 0.95em; line-height: 1.5; flex-grow: 1; margin-bottom: 20px; }}
>>>>>>> 446a32b (feat(ui): switch to apple-style clean light theme)
        
        /* Buttons */
        .btn {{ 
            display: inline-flex; align-items: center; justify-content: center;
            padding: 10px 20px; border-radius: 10px; 
            text-decoration: none; font-weight: 500; transition: all 0.2s ease;
            width: 100%; box-sizing: border-box;
            gap: 8px; font-size: 0.95em;
        }}
        
        .btn-colab {{ 
            background: #0f172a; color: white; 
            box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.1);
        }}
        .btn-colab:hover {{ 
            background: #334155; 
            transform: translateY(-1px);
            box-shadow: 0 6px 8px -1px rgba(15, 23, 42, 0.15);
        }}
        
        .btn-primary {{ 
            background: var(--accent-gradient); 
            color: white; 
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        }}
        .btn-primary:hover {{ 
            transform: translateY(-1px);
            box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
            filter: brightness(1.1);
        }}
    </style>
</head>
<body>
    {NAV_BAR_HTML}

    <div class="container">
        <div class="header-section">
            <div class="header-title">Daily Automation Tools</div>
            <div class="header-subtitle">
                Access your automated cleaning scripts, report generators, and utility tools directly from here.
            </div>
        </div>
        
        <div class="tool-grid">
"""

HTML_FOOT = """
        </div>
        
        <div style="text-align: center; margin-top: 60px; color: #94a3b8; font-size: 0.9em;">
            &copy; 2025 Daily Promotion Automation Hub
        </div>
    </div>
</body>
</html>
"""

def generate_tools_page():
    # Find all ipynb files in project root
    notebooks = glob.glob(os.path.join(PROJECT_ROOT, "*.ipynb"))
    notebooks.sort()
    
    tools_html = ""
    
    for nb_path in notebooks:
        filename = os.path.basename(nb_path)
        name = os.path.splitext(filename)[0]
        
        # Determine Icon & Desc based on name
        icon = "📊"
        desc = "Process data and generate reports."
        
        if "HoangHa" in name:
            icon = "📱"
            desc = "Scrape and process HoangHaMobile implementation."
        elif "DiDongViet" in name:
            icon = "🏷️"
            desc = "Scrape and process DiDongViet implementation."
        elif "CPS" in name:
            icon = "📱"
            desc = "CellphoneS Scraper and Analyzer tool."
        elif "TheGioiDiDong" in name:
            icon = "🌐"
            desc = "MWG (TheGioiDiDong) data automation."
        elif "Viettel" in name:
            icon = "🔴"
            desc = "ViettelStore automation scripts."
        elif "Generate" in name:
            icon = "⚡"
            desc = "Core report generator utility."
            
        colab_url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/{filename}"
        
        tools_html += f"""
            <div class="tool-card">
                <div class="icon-container">{icon}</div>
                <div class="card-title">{name}</div>
                <div class="card-desc">{desc}</div>
                <a href="{colab_url}" target="_blank" class="btn btn-colab">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                    Open in Colab
                </a>
            </div>
        """
        
    full_html = HTML_HEAD + tools_html + HTML_FOOT
    
    output_path = os.path.join(DOCS_DIR, "tools.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    print(f"✅ Generated Tools Page at: {output_path}")

if __name__ == "__main__":
    generate_tools_page()
