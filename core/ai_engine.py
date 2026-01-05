import os
import glob
import chromadb
import pandas as pd
from numbers_parser import Document
from sentence_transformers import SentenceTransformer
import argparse
import google.generativeai as genai
from audit_system import config as conf
import difflib
import html
import json
from datetime import datetime, timedelta

# --- CONFIG ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M")

DB_PATH = ".chroma_db"
COLLECTION_NAME = "audit_reports"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2" 
THRESHOLD_SEMANTIC = 0.82 

def setup_gemini():
    if conf.DEFAULT_API_KEY:
        genai.configure(api_key=conf.DEFAULT_API_KEY)
        return True
    return False

def verify_with_gemini(text_a, text_b):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Bạn là một chuyên gia ngôn ngữ học.
    So sánh 2 đoạn văn bản:
    [A]: "{text_a}"
    [B (Nguồn)]: "{text_b}"
    Hỏi: A có phải là bản viết lại (paraphrase) của B không?
    Trả lời ngắn gọn: Kết luận và Giải thích 1 câu.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gemini Error: {e}"

def generate_html_report(matches, sheet_name):
    """
    Generates a beautiful HTML report with Interactive Filtering
    """
    output_file = f"Result/ai_audit_{sheet_name}_{timestamp}.html"
    print(f"Generating HTML Report: {output_file}...")
    
    html_content = []
    
    # Collect unique values for Filters
    unique_topics = sorted(list(set([m['Suspect_Context'] for m in matches if m['Suspect_Context']])))
    unique_staff = sorted(list(set([m['Suspect'] for m in matches])))
    
    # --- HEADER & CSS ---
    html_content.append(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AI Semantic Audit - {sheet_name}</title>
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
                --card-border: rgba(226, 232, 240, 0.8);
                --shadow-sm: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
                --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                --danger: #ef4444;
                --success: #10b981;
                --warning: #f59e0b;
                --accent: #3b82f6;
                --purple: #8b5cf6;
            }}
            
            body {{ 
                font-family: 'Inter', sans-serif; 
                margin: 0; 
                background-color: var(--bg-body);
                color: var(--text-primary);
                padding: 30px;
                line-height: 1.5;
            }}

            h1, h2, h3 {{ font-family: 'Outfit', sans-serif; margin: 0; }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e2e8f0;
            }}
            
            .header h1 {{ 
                color: #0f172a; 
                font-size: 2.5rem; 
                letter-spacing: -0.02em; 
                margin-bottom: 10px;
            }}
            
            .meta-badge {{
                display: inline-block;
                padding: 6px 12px;
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
                font-size: 0.9rem;
                color: #64748b;
                box-shadow: var(--shadow-sm);
                margin: 0 5px;
            }}

            /* Controls Bar */
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
            
            select {{ 
                background: #f8fafc; 
                color: #1e293b; 
                border: 1px solid #cbd5e1; 
                padding: 8px 12px; border-radius: 8px; 
                outline: none; transition: border-color 0.2s;
            }}
            select:focus {{ border-color: #3b82f6; ring: 2px solid rgba(59, 130, 246, 0.1); }}
            
            #matchCount {{ color: var(--text-secondary); font-size: 0.9em; font-weight: 600; margin-left: auto; }}

            .match-card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 16px;
                margin-bottom: 30px;
                box-shadow: var(--shadow-sm);
                overflow: hidden;
            }}
            
            .match-header {{
                padding: 20px 25px;
                border-bottom: 1px solid #f1f5f9;
                background: linear-gradient(to right, #ffffff, #f8fafc);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .staff-names {{
                font-size: 1.1rem;
                font-weight: 700;
                color: #334155;
            }}
            .staff-names span {{ color: var(--accent); }}
            
            .score-badge {{
                font-family: 'Outfit', sans-serif;
                font-weight: 800;
                font-size: 1.1rem;
                padding: 6px 12px;
                border-radius: 8px;
                color: white;
                min-width: 80px;
                text-align: center;
            }}
            .score-danger {{ background: var(--danger); }}
            .score-warn   {{ background: var(--warning); }}
            
            .type-badge {{
                font-size: 0.75rem;
                text-transform: uppercase;
                font-weight: 800;
                padding: 4px 8px;
                border-radius: 6px;
                margin-right: 10px;
                letter-spacing: 0.05em;
            }}
            .type-peer {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}
            .type-self {{ background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; }}

            .ai-verdict {{
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                color: #166534;
                padding: 10px 20px;
                font-size: 0.9rem;
                border-top: 1px solid #f1f5f9;
            }}

            /* Diff Table */
            table.diff {{ width: 100%; border-collapse: separate; border-spacing: 0; font-family: 'Menlo', monospace; font-size: 0.9rem; color: #1e293b; }}
            table.diff th {{ background: #f8fafc; padding: 10px 20px; text-align: left; width: 50%; font-weight: 600; color: #64748b; border-bottom: 1px solid #e2e8f0; }}
            table.diff td {{ padding: 15px 20px; vertical-align: top; background: #fff; white-space: pre-wrap; }}
            .highlight-shared {{ background-color: #fee2e2; color: #b91c1c; font-weight: 600; border-bottom: 2px solid #ef4444; }}
            .highlight-unique {{ color: #15803d; opacity: 0.8; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Advanced AI Plagiarism Audit</h1>
            <div class="meta-badge">Target Sheet: {sheet_name}</div>
        </div>
        
        <!-- CONTROL PANEL -->
        <div class="controls">
            <div class="control-group">
                <label for="typeFilter">Type</label>
                <select id="typeFilter">
                    <option value="ALL">All Types</option>
                    <option value="PEER">📋 Copy from Others (Peer)</option>
                    <option value="SELF">🔄 Copy from Past (Self)</option>
                </select>
            </div>
            <div class="control-group">
                <label for="topicFilter">Topic</label>
                <select id="topicFilter">
                    <option value="ALL">All Topics</option>
                    {"".join([f'<option value="{t}">{t}</option>' for t in unique_topics])}
                </select>
            </div>
            <div class="control-group">
                <label for="staffFilter">Staff</label>
                <select id="staffFilter">
                    <option value="ALL">All Staff</option>
                    {"".join([f'<option value="{s}">{s}</option>' for s in unique_staff])}
                </select>
            </div>
             <div class="control-group">
                <label for="scoreFilter">Similarity</label>
                <select id="scoreFilter">
                    <option value="ALL">All Scores</option>
                    <option value="90">> 90% (Exact)</option>
                    <option value="80">> 80% (High)</option>
                    <option value="70">> 70% (Medium)</option>
                </select>
            </div>
            <span id="matchCount">Showing {len(matches)} Items</span>
        </div>

        <div id="resultsContainer">
    """)
    
    # --- MATCH CARDS ---
    for m in matches:
        score_class = "score-danger" if m['Distance'] < 0.1 else "score-warn"
        percentage = (1 - m['Distance']) * 100
        topic_safe = m.get('Suspect_Context', 'Unknown')
        match_type = m.get('Match_Type', 'PEER')
        
        type_badge = ""
        if match_type == "SELF":
            type_badge = '<span class="type-badge type-self">SELF-COPY</span>'
        else:
            type_badge = '<span class="type-badge type-peer">PEER-COPY</span>'
        
        # Prepare HTML Diff
        matcher = difflib.SequenceMatcher(None, m['Suspect_Text'], m['Source_Text'])
        html_suspect = []
        html_source = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            txt_susp = html.escape(m['Suspect_Text'][i1:i2]).replace('\\n', '<br>')
            txt_src  = html.escape(m['Source_Text'][j1:j2]).replace('\\n', '<br>')
            
            if tag == 'equal':
                html_suspect.append(f'<span class="highlight-shared">{txt_susp}</span>')
                html_source.append(f'<span class="highlight-shared">{txt_src}</span>')
            elif tag == 'replace':
                html_suspect.append(f'<span class="highlight-unique">{txt_susp}</span>')
                html_source.append(f'<span class="highlight-unique">{txt_src}</span>')
            elif tag == 'delete':
                html_suspect.append(f'<span class="highlight-unique">{txt_susp}</span>')
            elif tag == 'insert':
                html_source.append(f'<span class="highlight-unique">{txt_src}</span>')

        card = f"""
        <div class="match-card" 
             data-staff="{m['Suspect']}" 
             data-topic="{topic_safe}"
             data-score="{percentage:.1f}"
             data-type="{match_type}">
             
            <div class="match-header">
                <div>
                    <div style="font-size:0.8rem; text-transform:uppercase; color:#64748b; font-weight:700; letter-spacing:0.5px; margin-bottom:4px;">
                        {topic_safe}
                    </div>
                    <div class="staff-names">
                        {type_badge}
                        <span>{m['Suspect']}</span> 
                        <span class="meta-badge" style="font-size:0.75rem; color:#64748b; background:#f1f5f9; border:none; margin-left:5px;">
                            {m.get('Suspect_Col', '')}
                        </span>
                        
                        <span style="color:#cbd5e1; margin:0 10px;">➔</span> 
                        
                        {m['Source_Staff']} 
                        <span class="meta-badge" style="font-size:0.75rem; color:#64748b; background:#f1f5f9; border:none; margin-left:5px;">
                            {m.get('Source_Col', '')}
                        </span>
                        <small style="font-weight:400; color:#64748b">({m['Source_Sheet']})</small>
                    </div>
                </div>
                <div class="score-badge {score_class}">
                    Sim: {percentage:.1f}%
                </div>
            </div>
            
            <table class="diff">
                <thead>
                    <tr>
                        <th>Suspect (New Report)</th>
                        <th>Source (Historical Database)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{''.join(html_suspect)}</td>
                        <td>{''.join(html_source)}</td>
                    </tr>
                </tbody>
            </table>
        """
        
        if m.get('AI_Verdict') and m['AI_Verdict'] != "N/A":
            card += f"""
            <div class="ai-verdict">
                <strong>Gemini AI Analysis:</strong> {m['AI_Verdict']}
            </div>
            """
            
        card += "</div>"
        html_content.append(card)

    # --- JAVASCRIPT ---
    html_content.append("""
        </div> <!-- End Results Container -->
        
        <script>
            const typeFilter = document.getElementById('typeFilter');
            const topicFilter = document.getElementById('topicFilter');
            const staffFilter = document.getElementById('staffFilter');
            const scoreFilter = document.getElementById('scoreFilter');
            const cards = document.querySelectorAll('.match-card');
            const matchCount = document.getElementById('matchCount');
            
            function filterResults() {
                const type = typeFilter.value;
                const topic = topicFilter.value;
                const staff = staffFilter.value;
                const score = scoreFilter.value;
                let visibleCount = 0;
                
                cards.forEach(card => {
                    const cardType = card.getAttribute('data-type');
                    const cardStaff = card.getAttribute('data-staff');
                    const cardTopic = card.getAttribute('data-topic');
                    const cardScore = parseFloat(card.getAttribute('data-score'));
                    
                    let show = true;
                    
                    if (type !== 'ALL' && cardType !== type) show = false;
                    if (topic !== 'ALL' && cardTopic !== topic) show = false;
                    if (staff !== 'ALL' && cardStaff !== staff) show = false;
                    
                    if (score !== 'ALL') {
                        if (score === '90' && cardScore < 90) show = false;
                        if (score === '80' && cardScore < 80) show = false;
                        if (score === '70' && cardScore < 70) show = false;
                    }
                    
                    card.style.display = show ? 'block' : 'none';
                    if(show) visibleCount++;
                });
                
                matchCount.textContent = `Showing ${visibleCount} Items`;
            }
            
            typeFilter.addEventListener('change', filterResults);
            topicFilter.addEventListener('change', filterResults);
            staffFilter.addEventListener('change', filterResults);
            scoreFilter.addEventListener('change', filterResults);
        </script>
    </body></html>
    """)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_content))
    
    print(f"Report report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Advanced AI Plagiarism Audit")
    parser.add_argument("--sheet", default=conf.DEFAULT_INSIGHT_SHEET, help="Sheet to audit")
    parser.add_argument("--staff", help="Specific staff to audit (optional)")
    parser.add_argument("--ai-check", action="store_true", help="Enable Gemini verification")
    parser.add_argument("--check-self", action="store_true", help="Check for Self-Plagiarism (Lazy Copying)")
    args = parser.parse_args()
    
    print(f"--- AI AUDIT SYSTEM STARTING (Target: {args.sheet}) ---")
    if args.check_self:
        print("  [Mode] Self-Plagiarism Check: ENABLED (Will flag repetitions from own past reports)")
    else:
        print("  [Mode] Self-Plagiarism Check: DISABLED (Focusing on Peer Plagiarism)")
    
    # 1. Init System
    print("Loading Vector DB & AI Model...")
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except:
        print("[!] DB Collection not found. Please run db_builder.py first.")
        return

    model = SentenceTransformer(MODEL_NAME)
    
    has_gemini = False
    if args.ai_check:
        has_gemini = setup_gemini()
        if not has_gemini:
            print("[!] Warning: No API Key found in config. Gemini disabled.")
    
    # 2. Find Targets
    base_dir = conf.BASE_DIR
    workspaces = glob.glob(os.path.join(base_dir, "* - CS Work Space")) or glob.glob(os.path.join(base_dir, "* - CS"))
    
    matches_found = []

    for ws in workspaces:
        folder = os.path.basename(ws)
        staff_name = folder.replace(" - CS Work Space", "").replace(" - CS", "").strip()
        
        if args.staff and args.staff.lower() not in staff_name.lower():
            continue
            
        print(f"\nScanning: {staff_name}")
        report_files = glob.glob(os.path.join(ws, "*Insight*.numbers"))
        
        if not report_files:
            continue
            
        try:
            doc = Document(report_files[0])
            sheet = next((s for s in doc.sheets if args.sheet in s.name), None)
            
            if not sheet:
                continue
                
            entries_to_check = []
            
            # --- IMPROVED PARSING WITH CONTEXT ---
            for table in sheet.tables:
                rows = table.rows(values_only=True)
                if not rows: continue
                df = pd.DataFrame(rows[1:], columns=rows[0])
                
                # Identify Logic similar to db_builder
                detail_col = next((c for c in df.columns if "detail" in str(c).lower()), None)
                if detail_col:
                    df[detail_col] = df[detail_col].ffill()
                
                valid_cols = [c for c in df.columns if "detail" not in str(c).lower() and "category" not in str(c).lower()]
                for col in valid_cols:
                    for idx, val in df[col].items():
                        v = str(val).strip()
                        if len(v) > 50: 
                            # Context Finding
                            context = "General"
                            if detail_col:
                                try:
                                    res = str(df.at[idx, detail_col])
                                    if res and res.lower() != 'nan':
                                        context = res.strip()
                                except: pass
                            
                            entries_to_check.append({
                                "text": v,
                                "context": context,
                                "col": str(col) # NEW: Capture Column Name
                            })
            
            if not entries_to_check: continue

            # Query DB
            texts = [e['text'] for e in entries_to_check]
            embeddings = model.encode(texts).tolist()
            
            # Construct Query Arguments
            # If checking self, we need more results to skip the "Same File" match
            query_n_results = 10 if args.check_self else 1
            
            query_args = {
                "query_embeddings": embeddings,
                "n_results": query_n_results
            }
            
            if not args.check_self:
                query_args["where"] = {"staff": {"$ne": staff_name}}
            
            results = collection.query(**query_args)
            
            for i, res_ids in enumerate(results['ids']):
                # Find best valid match in candidates
                best_match = None
                
                for k in range(len(res_ids)):
                    m_dist = results['distances'][i][k]
                    m_meta = results['metadatas'][i][k]
                    m_text = results['documents'][i][k]
                    
                    # Filter: Ignore matches from the exact same sheet/context (Self-Current)
                    # We compare sheet names carefully
                    if args.check_self:
                        if m_meta['staff'] == staff_name and m_meta['sheet'] == sheet.name:
                            continue
                            
                    if m_dist < 0.35:
                        best_match = {
                            "dist": m_dist,
                            "meta": m_meta,
                            "text": m_text
                        }
                        break # Found valid top match
                
                if best_match:
                    distance = best_match['dist']
                    match_meta = best_match['meta']
                    match_text = best_match['text']
                    curr_item = entries_to_check[i]

                    # CLASSIFY TYPE
                    match_type = "PEER"
                    if match_meta['staff'] == staff_name:
                        match_type = "SELF"

                    gemini_verdict = "N/A"
                    if has_gemini:
                        print("    [AI] Verifying match with Gemini...")
                        gemini_verdict = verify_with_gemini(curr_item['text'], match_text)
                    
                    matches_found.append({
                        "Suspect": staff_name,
                        "Suspect_Context": curr_item['context'], 
                        "Suspect_Col": curr_item.get('col', 'Unknown'), # NEW
                        "Source_Staff": match_meta['staff'],
                        "Source_Sheet": match_meta['sheet'],
                        "Source_Col": match_meta.get('column', 'Unknown'), # NEW: From DB
                        "Source_File": match_meta.get('source_file', 'Unknown'),
                        "Match_Type": match_type,
                        "Distance": distance,
                        "Suspect_Text": curr_item['text'],
                        "Source_Text": match_text,
                        "AI_Verdict": gemini_verdict
                    })
                    print(f"  [!] MATCH FOUND ({distance:.3f}) [{match_type}] with {match_meta['staff']} ({match_meta['sheet']})")

        except Exception as e:
            print(f"  [!] Error: {e}")

    # Report
    if matches_found:
        print("\n" + "="*30)
        print("    SUSPICIOUS FINDINGS")
        print("="*30)
        matches_found.sort(key=lambda x: x['Distance'])
        
        # CSV Output
        csv_file = f"Result/ai_audit_{args.sheet}_{timestamp}.csv"
        pd.DataFrame(matches_found).to_csv(csv_file, index=False)
        print(f"\nSaved CSV report to {csv_file}")
        
        # HTML Output
        generate_html_report(matches_found, args.sheet)
        
    else:
        print("\nNo semantic anomalies found.")

if __name__ == "__main__":
    main()
