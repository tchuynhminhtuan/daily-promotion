import yaml
import sys

FILE = "catalog/product_catalog.yaml"

def analyze_catalog():
    with open(FILE, "r") as f:
        data = yaml.safe_load(f)
        
    audit_results = []
    
    for key, info in data.items():
        category = info.get("category")
        if category not in ["iPad", "Watch"]: continue
        
        issues = []
        conn = info.get("connectivity") or []
        sizes = info.get("sizes") or []
        
        # Check Connectivity Mixing
        if len(conn) > 1:
            issues.append(f"Mixed Connectivity: {conn}")
            
        # Check Size Mixing
        if len(sizes) > 1:
            issues.append(f"Mixed Sizes: {sizes}")
            
        if issues:
            audit_results.append({
                "key": key,
                "name": info.get("name"),
                "category": category,
                "issues": issues
            })
            
    # Report
    print(f"audit_results found: {len(audit_results)}")
    for item in audit_results:
        print(f"[{item['category']}] {item['key']} ({item['name']})")
        for issue in item['issues']:
            print(f"   - {issue}")
            
if __name__ == "__main__":
    analyze_catalog()
