import os
import glob
from datetime import datetime

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
GITHUB_REPO = "tchuynhminhtuan/daily-promotion"
BRANCH = "main"

# HTML Template Parts
# Shared Nav Bar (Updated for Premium Look)
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
    /* Premium Nav Styling */
    .nav-container {
        display: flex;
        justify-content: center;
        margin-bottom: 40px;
    }
    .nav-bar {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 12px 30px;
        border-radius: 50px;
        display: flex;
        align-items: center;
        gap: 40px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .nav-logo {
        color: white;
        font-weight: 800;
        font-family: 'Outfit', sans-serif;
        font-size: 1.1em;
        letter-spacing: 0.5px;
    }
    .nav-links {
        display: flex;
        gap: 8px;
        background: rgba(0,0,0,0.2);
        padding: 4px;
        border-radius: 30px;
    }
    .nav-link {
        color: #94a3b8;
        text-decoration: none;
        font-weight: 600;
        padding: 8px 20px;
        border-radius: 24px;
        transition: all 0.3s ease;
        font-size: 0.95em;
    }
    .nav-link:hover {
        color: white;
    }
    .nav-link.active {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
    }
    .nav-info {
        color: #64748b;
        font-size: 0.85em;
        font-weight: 500;
    }
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
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            --accent-glow: rgba(139, 92, 246, 0.5);
        }}
        
        body {{ 
            font-family: 'Inter', sans-serif; 
            margin: 0; 
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
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
            background: linear-gradient(to right, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            letter-spacing: -1px;
        }}
        .header-subtitle {{ font-size: 1.25em; color: var(--text-secondary); max-width: 600px; margin: 0 auto; }}
        
        /* Grid */
        .tool-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); 
            gap: 30px; 
            perspective: 1000px;
        }}
        
        /* Card Styling */
        .tool-card {{ 
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 30px;
            display: flex;
            flex-direction: column;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
            group-hover:;
        }}
        
        .tool-card:hover {{ 
            transform: translateY(-8px) scale(1.02); 
            box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5); 
            border-color: rgba(255,255,255,0.2);
        }}
        
        .tool-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 100px;
            background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%);
            pointer-events: none;
        }}
        
        /* Icon */
        .icon-container {{
            width: 64px; height: 64px;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
            font-size: 32px;
            margin-bottom: 24px;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.1);
        }}
        
        /* Content */
        .card-title {{ font-size: 1.5em; font-weight: 700; margin: 0 0 10px 0; color: white; }}
        .card-desc {{ color: var(--text-secondary); font-size: 0.95em; line-height: 1.6; flex-grow: 1; margin-bottom: 25px; }}
        
        /* Buttons */
        .btn {{ 
            display: inline-flex; align-items: center; justify-content: center;
            padding: 12px 24px; border-radius: 12px; 
            text-decoration: none; font-weight: 600; transition: all 0.3s ease;
            width: 100%; box-sizing: border-box;
            gap: 8px;
        }}
        
        .btn-colab {{ 
            background: rgba(255,255,255,0.05); 
            color: white; 
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .btn-colab:hover {{ 
            background: rgba(255,255,255,0.1); 
            border-color: rgba(255,255,255,0.3);
        }}
        
        .btn-primary {{ 
            background: var(--accent-gradient); 
            color: white; border: none;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }}
        .btn-primary:hover {{ 
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5);
            transform: translateY(-1px);
        }}

        /* Status Badges */
        .badge {{
            position: absolute; top: 20px; right: 20px;
            padding: 4px 10px; border-radius: 20px;
            font-size: 0.75em; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-new {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}

        /* Footer */
        .footer {{ margin-top: 80px; text-align: center; color: rgba(255,255,255,0.2); font-size: 0.85em; }}
    </style>
</head>
<body>
    {NAV_BAR_HTML.replace('active', '')} <!-- Simple hack to reset active class for tools page -->
    
    <div class="container">
        <div class="header-section">
            <div class="header-title">Command Center</div>
            <div class="header-subtitle">Centralized hub for scraper automation, pricing analysis, and Google Colab notebooks.</div>
        </div>
        
        <div class="tool-grid">
"""

def generate_tools_page():
    print(f"🔍 Scanning for notebooks in {PROJECT_ROOT}...")
    notebooks = glob.glob(os.path.join(PROJECT_ROOT, "*.ipynb"))
    notebooks.sort()
    
    html_content = HTML_HEAD
    
    # 1. SPECIAL CARD: The Report (Visual Anchor)
    html_content += """
        <div class="tool-card" style="border-color: rgba(139, 92, 246, 0.3);">
            <div class="badge badge-new">Core</div>
            <div class="icon-controller">
                <div class="icon-container" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2)); color: #a78bfa;">
                    📊
                </div>
            </div>
            <div class="card-title">Analysis Report</div>
            <div class="card-desc">
                Access the latest daily price comparison report. Visualizes stock status, promotions, and competitive pricing across all retailers.
            </div>
            <a href="index.html" class="btn btn-primary">
                View Report <span>→</span>
            </a>
        </div>
    """
    
    # 2. NOTEBOOK CARDS
    for nb_path in notebooks:
        filename = os.path.basename(nb_path)
        name_clean = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
        
        # Icon & Color Logic
        icon = "⚡️"
        
        if "Viettel" in filename: icon = "🔴"
        elif "FPT" in filename: icon = "⚫️"
        elif "HoangHa" in filename: icon = "🟢"
        elif "DiDongViet" in filename: icon = "📱"
        elif "TheGioiDiDong" in filename: icon = "🟡"
        elif "CPS" in filename: icon = "💎"
        elif "Generate" in filename: icon = "⚙️"
        
        colab_url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/{filename}"
        
        html_content += f"""
        <div class="tool-card">
            <div class="icon-container">{icon}</div>
            <div class="card-title">{name_clean}</div>
            <div class="card-desc">
                Direct access to <code>{filename}</code>. Run automation logic individually in the cloud.
            </div>
            <a href="{colab_url}" target="_blank" class="btn btn-colab">
                <span>Open in Colab</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>
        </div>
        """
        
    html_content += """
        </div> <!-- End Grid -->
        
        <div class="footer">
            Generated automatically by <code>generate_tools_page.py</code> • Last updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
        </div>
    </div> <!-- End Container -->

    <script>
        // Active Link Logic
        document.querySelectorAll('.nav-link').forEach(link => {
            const current = link.getAttribute('href');
            if(window.location.pathname.includes(current) || (current === 'tools.html' && window.location.pathname.includes('tools'))) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    </script>
</body>
</html>
    """
    
    output_path = os.path.join(DOCS_DIR, "tools.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✨ Premium Tools Page Generated: {output_path}")

if __name__ == "__main__":
    generate_tools_page()
