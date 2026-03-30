import json
import yaml
import re

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w_]', '', text)
    return text

def main():
    with open('apple_official_catalog.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    catalog = {}
    
    for category, products in data.items():
        for p in products:
            name = p.get('name', 'Unknown')
            # Create a nice key
            key = slugify(name)
            
            # Filter empty lists
            entry = {
                "name": name,
                "category": category,
                "url": p.get('url')
            }
            
            if p.get('colors'):
                entry['colors'] = sorted(p['colors'])
            if p.get('storage'):
                # Sort storage naturally (128GB < 256GB < 1TB)
                def storage_key(s):
                    if 'TB' in s:
                        return float(re.search(r'\d+', s).group()) * 1024
                    match = re.search(r'\d+', s)
                    return float(match.group()) if match else 0
                
                entry['storage'] = sorted(p['storage'], key=storage_key)
            
            if p.get('sizes'):
                entry['sizes'] = sorted(p['sizes'])
                
            catalog[key] = entry

    with open('product_catalog_golden.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(catalog, f, allow_unicode=True, sort_keys=False)
    
    print("Catalog generated: product_catalog_golden.yaml")

if __name__ == "__main__":
    main()
