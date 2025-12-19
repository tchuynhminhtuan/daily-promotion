from numbers_parser import Document
import pandas as pd
import os

# File path
# Resolve path relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'wk.numbers')

def extract_data(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    print(f"Loading '{file_path}'...")
    try:
        doc = Document(file_path)
    except Exception as e:
        print(f"Error loading document: {e}")
        return

    sheets = doc.sheets
    print(f"Found {len(sheets)} sheets.")

    for sheet in sheets:
        print(f"\n--- Sheet: {sheet.name} ---")
        tables = sheet.tables
        print(f"Found {len(tables)} tables.")
        
        for table in tables:
            print(f"Table: {table.name}")
            data = table.rows(values_only=True)
            if not data:
                print("  (Empty table)")
                continue
            
            # Create DataFrame
            # Assuming first row is header
            df = pd.DataFrame(data[1:], columns=data[0])
            print(f"  Shape: {df.shape}")
            print("  First 5 rows:")
            print(df.head())
            print("-" * 30)

            # Optional: Save to CSV for easier inspection if needed
            # csv_name = f"{sheet.name}_{table.name}.csv".replace(" ", "_").replace("/", "-")
            # df.to_csv(csv_name, index=False)
            # print(f"  Saved to {csv_name}")

if __name__ == "__main__":
    extract_data(file_path)
