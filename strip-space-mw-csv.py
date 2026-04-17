import pandas as pd
import re

def clean_excessive_whitespace(text):
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    # 1. Thay thế các ký tự khoảng trắng lạ (\xa0, \t...) bằng dấu cách thường
    text = re.sub(r'[\xa0\t\r\f\v]', ' ', text)
    
    # 2. Coi các khoảng trống lớn (>= 5 dấu cách) là dấu hiệu xuống dòng
    text = re.sub(r' {5,}', '\n', text)
    
    # 3. Thay thế các khoảng trắng dư thừa nhỏ (2-4 dấu cách) bằng 1 dấu cách
    text = re.sub(r' {2,4}', ' ', text)
    
    # 4. Tách thành các dòng để xử lý logic "số thứ tự"
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    final_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Nếu dòng hiện tại là số thứ tự (ví dụ: "1", "2") hoặc rất ngắn
        # thì nối nó với dòng nội dung kế tiếp
        is_index = line.isdigit() or (len(line) <= 3 and any(c.isdigit() for c in line))
        
        if is_index and i + 1 < len(lines):
            final_lines.append(f"{line} {lines[i+1]}")
            i += 2
        else:
            final_lines.append(line)
            i += 1
            
    return '\n'.join(final_lines)

mw_file = '/Users/brucehuynh/GitHub/daily-promotion/data/raw/2026-04-17/2-mw-2026-04-17.csv'

# Áp dụng cho file CSV của bạn
df = pd.read_csv(mw_file, sep=';')

# Tự động quét và xử lý tất cả các cột chứa văn bản
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].apply(clean_excessive_whitespace)

# Lưu file kết quả
df.to_csv(f'{mw_file.replace(".csv","")}_clean.csv', index=False, sep=';', encoding='utf-8-sig')