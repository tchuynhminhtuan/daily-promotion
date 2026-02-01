import pandas as pd

FILE = "content/2025-12-28/1-fpt-2025-12-28.csv"
OUTPUT_FILE = "reverify_urls.txt"

try:
    df = pd.read_csv(FILE, sep=";", encoding="utf-8", on_bad_lines='skip', engine='python')
    
    # Identify bad rows:
    # 1. Color is "Unknown"
    # 2. Color looks like storage (contains "GB" or "TB")
    def is_bad_color(val):
        s = str(val).upper()
        if "UNKNOWN" in s: return True
        if "GB" in s or "TB" in s: return True
        return False
    
    bad_df = df[df["Color"].apply(is_bad_color)]
    
    print(f"Total Rows: {len(df)}")
    print(f"Bad Color Rows: {len(bad_df)}")
    
    with open(OUTPUT_FILE, "w") as f:
        for index, row in bad_df.iterrows():
            link = str(row['Link']).strip()
            name = row['Product_Name']
            color = row['Color']
            print(f"Found Bad Data: {name} | Color: {color} | Link: {link}")
            
            if link and link.lower().startswith("http"):
                f.write(link + "\n")
                
except Exception as e:
    print(f"Error: {e}")
