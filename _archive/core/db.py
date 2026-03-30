import os
import glob
import chromadb
import pandas as pd
from numbers_parser import Document
from sentence_transformers import SentenceTransformer
from pyvi import ViTokenizer
import shutil

# --- CONFIG ---
from audit_system import config as conf
BASE_DIR = conf.BASE_DIR
DB_PATH = ".chroma_db"
COLLECTION_NAME = "audit_reports"
# Using a lightweight multilingual model good for semantic similarity
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2" 
MIN_TEXT_LENGTH = 50 # Ignore short phrases

def get_text_from_report(file_path):
    """
    Extracts text blocks from an Insight Report.
    Returns list of dicts: {'text': str, 'context': str, 'sheet': str}
    """
    print(f"  -> Parsing: {os.path.basename(file_path)}")
    try:
        doc = Document(file_path)
        all_text = []
        
        for sheet in doc.sheets:
            # We want to capture historical data, so we scan all sheets that look like weeks
            # e.g. "W10Q1FY26", "W9...", NOT "Performance"
            if "W" not in sheet.name.upper() or "PERF" in sheet.name.upper():
                continue
                
            for table in sheet.tables:
                rows = table.rows(values_only=True)
                if not rows: continue
                df = pd.DataFrame(rows[1:], columns=rows[0])
                
                # Identify "Detail" column
                detail_col = next((c for c in df.columns if "detail" in str(c).lower()), None)
                if detail_col:
                    df[detail_col] = df[detail_col].ffill()
                
                # Identify valid content columns (Not Category/Detail)
                valid_cols = [c for c in df.columns 
                             if not any(x in str(c).lower() for x in ["category", "categogy", "detail"])]
                
                for col in valid_cols:
                    for idx, val in df[col].items():
                        val_str = str(val).strip()
                        if len(val_str) > MIN_TEXT_LENGTH and val_str.lower() not in ["nan", "none"]:
                            context = "General"
                            if detail_col:
                                try:
                                    res = str(df.at[idx, detail_col])
                                    if res and res.lower() != 'nan':
                                        context = res.strip()
                                except: pass
                            
                            # Clean text with PyVi (Tokenizer) roughly if needed
                            # For semantic search, raw text is usually fine, 
                            # but tokenizing can help some models. 
                            # We keep it raw for the Embedding model to handle context.
                            
                            all_text.append({
                                "text": val_str,
                                "context": context,
                                "col": str(col), # NEW: Capture Column Name
                                "sheet": sheet.name
                            })
        return all_text
    except Exception as e:
        print(f"    [!] Error reading file: {e}")
        return []

def main():
    print("="*60)
    print("      BUILDING VECTOR DATABASE FOR AUDIT SYSTEM      ")
    print("="*60)
    
    # 1. Initialize ChromaDB
    print(f"Initializing ChromaDB at '{DB_PATH}'...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # Reset collection if exists (Full Rebuild)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("  - Cleared existing collection.")
    except:
        pass
        
    collection = client.create_collection(name=COLLECTION_NAME)
    
    # 2. Load Embedding Model
    print(f"Loading AI Model '{MODEL_NAME}'... (This may take a moment)")
    model = SentenceTransformer(MODEL_NAME)
    
    # 3. Scan for Reports
    workspaces = glob.glob(os.path.join(BASE_DIR, "* - CS Work Space")) or glob.glob(os.path.join(BASE_DIR, "* - CS"))
    print(f"Found {len(workspaces)} staff workspaces.")
    
    total_docs = 0
    
    ids = []
    documents = []
    metadatas = []
    embeddings = [] # We can let Chroma compute, or we compute. 
                    # Computing manually allows batching control.
    
    for ws in workspaces:
        folder_name = os.path.basename(ws)
        staff_name = folder_name.replace(" - CS Work Space", "").replace(" - CS", "").strip()
        
        print(f"\nProcessing Staff: {staff_name}")
        report_files = glob.glob(os.path.join(ws, "*Insight*.numbers"))
        
        for rf in report_files:
            items = get_text_from_report(rf)
            
            if not items: continue
            
            # Prepare batch
            texts = [item['text'] for item in items]
            
            # Compute Embeddings (Heavy Operation)
            # print(f"    - Embedding {len(texts)} sentences...")
            embs = model.encode(texts).tolist()
            
            for i, item in enumerate(items):
                # Unique ID: Staff_Sheet_Index
                doc_id = f"{staff_name}_{item['sheet']}_{i}_{os.path.basename(rf)}"
                
                ids.append(doc_id)
                documents.append(item['text'])
                embeddings.append(embs[i])
                metadatas.append({
                    "staff": staff_name,
                    "sheet": item['sheet'],
                    "context": item['context'],
                    "column": item['col'], # NEW: Store Column Name
                    "source_file": os.path.basename(rf)
                })
                
                total_docs += 1
                
    # 4. Save to DB
    if ids:
        print(f"\nSaving {len(ids)} vectors to database...")
        # Upsert in batches of 5000 to avoid limits
        batch_size = 5000
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            print(f"  - Writing batch {i} to {end}...")
            collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
        print("\nSUCCESS! Database built.")
        print(f"Total Vectors: {collection.count()}")
    else:
        print("\nNo data found to index.")

if __name__ == "__main__":
    main()
