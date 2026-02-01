# System Design & Architecture 🏗️

> **Purpose**: This document defines the project structure, data flow, and design principles to prevent "drift" and ensure long-term maintainability.

## 1. Core Philosophy 🧠

1.  **Config Driven**: Logic should be controlled by configuration files (`config/`), not hardcoded in scripts.
2.  **Raw Data Immutable**: Content in `data/raw/` is never modified after scraping.
3.  **Separation of Concerns**:
    *   **Crawlers** (`src/crawlers/`) only fetch data.
    *   **Processing** (`src/processing/`) only cleans and normalizes.
    *   **Reporting** (`src/reporting/`) only visualizes.
4.  **Explicit Outputs**: Clear distinction between successful data (`clean_data`) and error logs (`unmatched_err`).

## 2. Directory Structure 📂

```text
Daily Promotion/
├── config/                 # ⚙️ INPUTS (Manual Config)
│   ├── product_catalog.yaml   # The "Golden Record" of truth
│   ├── retailer_mapping.yaml  # Persistent mapping memory
│   └── standards.md           # Naming conventions
│
├── src/                    # 🧠 LOGIC (Code)
│   ├── crawlers/              # Playwright scripts (1 per retailer)
│   ├── processing/            # Normalization logic
│   └── reporting/             # Report generation
│
├── data/                   # 💾 STORAGE
│   ├── raw/                   # 📥 Input from Crawlers (YYYY-MM-DD/*.csv)
│   ├── normalized/            # ✅ Output Clean Data (clean_data_*.csv)
│   └── logs/                  # ❌ Error Logs (unmatched_err_*.csv)
│
└── docs/                   # 📊 VISUALIZATION
    ├── index.html             # Final Report (GitHub Pages)
    └── insights/              # Daily Markdown analysis
```

## 3. Data Flow Pipeline 🔄

### Step 1: Scrape (Input)
*   **Source**: Retailer Websites.
*   **Action**: `src/crawlers/*.py` runs.
*   **Output**: `data/raw/{date}/{retailer}.csv`.

### Step 2: Normalize (Process)
*   **Source**: `data/raw/{date}/*.csv`.
*   **Config**: Uses `product_catalog.yaml` and `retailer_mapping.yaml`.
*   **Action**: `src/processing/normalize.py` runs.
*   **Output**:
    *   ✅ **Clean Data**: `data/normalized/clean_data_{date}.csv`.
    *   ❌ **Errors**: `data/logs/unmatched_err_{date}.csv`.

### Step 3: Report (Visualize)
*   **Source**: `data/normalized/clean_data_{date}.csv`.
*   **Action**: `src/reporting/generate_report.py` runs.
*   **Output**: `docs/index.html`.

## 4. File Naming Conventions 📝

| Type | Pattern | Location | Purpose |
|------|---------|----------|---------|
| **Raw Data** | `{prefix}-{retailer}-{date}.csv` | `data/raw/{date}/` | Original scraped data (DO NOT EDIT). |
| **Clean Data** | `clean_data_{date}.csv` | `data/normalized/` | Normalized, price-checked data for reporting. |
| **Error Log** | `unmatched_err_{date}.csv` | `data/logs/` | Products that failed mapping. Review this weekly. |
| **Catalog** | `product_catalog.yaml` | `config/` | Defines valid product keys and attributes. |
| **Mapping** | `retailer_mapping.yaml` | `config/` | Maps "Retailer Name" → "Product Key". |

## 5. Maintenance Rituals 🛠️

1.  **Weekly**: Check `data/logs/unmatched_err_*.csv`. Update `config/retailer_mapping.yaml` with new mappings.
2.  **Monthly**: Update `config/product_catalog.yaml` with new Apple product launches.
3.  **Ad-hoc**: If checking prices, rely on `docs/index.html` or `data/normalized/clean_data_*.csv`.
