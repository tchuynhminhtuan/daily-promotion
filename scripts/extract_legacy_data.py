
import os
import zipfile
import glob
from pathlib import Path

SOURCE_DIR = Path("Market Promotion")
TARGET_DIR = Path("data/raw_legacy")

def extract_all():
    if not SOURCE_DIR.exists():
        print(f"❌ Source directory {SOURCE_DIR} not found.")
        return

    os.makedirs(TARGET_DIR, exist_ok=True)
    
    zip_files = glob.glob(str(SOURCE_DIR / "**/*.zip"), recursive=True)
    print(f"📦 Found {len(zip_files)} zip archives.")
    
    count = 0
    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Filter only CSVs to save space/time
                csv_members = [f for f in zip_ref.namelist() if f.lower().endswith('.csv') and not f.startswith('__MACOSX')]
                
                for member in csv_members:
                    # Flatten structure: save as date_filename.csv to avoid collisions
                    # Extract date from zip filename if possible
                    zip_name = Path(zip_path).stem
                    original_name = Path(member).name
                    
                    new_name = f"{zip_name}_{original_name}"
                    target_path = TARGET_DIR / new_name
                    
                    with zip_ref.open(member) as source, open(target_path, "wb") as target:
                        target.write(source.read())
                    count += 1
                    
        except Exception as e:
            print(f"⚠️ Failed to extract {zip_path}: {e}")

    print(f"✅ Extracted {count} CSV files to {TARGET_DIR}")

if __name__ == "__main__":
    extract_all()
