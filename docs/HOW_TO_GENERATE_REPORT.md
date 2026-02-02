# 📊 Report Generation Pipeline

## Quick Start
```bash
python3 src/processing/normalize.py && python3 src/reporting/generate_report.py
```

---

## Pipeline Overview

```
Raw CSV (6 retailers)
        ↓
   normalize.py ← retailer_mapping.yaml + product_catalog.yaml + Qwen AI
        ↓
   clean_data.csv
        ↓
   generate_report.py
        ↓
   docs/index.html
```

---

## Step 1: Normalize Data

**Script:** `src/processing/normalize.py`

| Input | Output |
|-------|--------|
| `data/raw/YYYY-MM-DD/*.csv` | `catalog/output/clean_data_YYYY-MM-DD.csv` |

**Dependencies:**
| File | Mô tả |
|------|-------|
| `catalog/retailer_mapping.yaml` | Mapping thủ công (Product Name → Key) |
| `catalog/product_catalog.yaml` | Catalog sản phẩm (Key → Info) |
| `experiments/fine_tuning/adapters/` | Qwen 2.5-0.5B model (fallback) |

---

## Step 2: Generate Report

**Script:** `src/reporting/generate_report.py`

| Input | Output |
|-------|--------|
| `catalog/output/clean_data_*.csv` | `docs/index.html` |
| | `docs/insights/YYYY-MM-DD_insights_v2.md` |

---

## Helper Scripts

| Script | Mô tả | Lệnh |
|--------|-------|------|
| `scripts/analyze_mapping.py` | Kiểm tra % coverage | `python3 scripts/analyze_mapping.py` |
| `scripts/extract_ai_matches.py` | Trích xuất AI matches | `python3 scripts/extract_ai_matches.py` |
| `scripts/merge_mappings.py` | Merge AI → mapping | `python3 scripts/merge_mappings.py` |

---

## Troubleshooting

### Qwen chạy chậm?
- Kiểm tra coverage: `python3 scripts/analyze_mapping.py`
- Nếu coverage < 90%, cần bổ sung `retailer_mapping.yaml`

### Error: "float has no len()"
- CSV có cell rỗng/NaN trong cột Product_Name
- Tạm thời skip, không ảnh hưởng report

---

*Last updated: 2026-02-02*
