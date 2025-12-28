# Database Work Review - 2025-12-28
This folder contains all the scripts, diagnostics, and data files related to the database expansion, ML normalization, and price audits performed today. The root project has been tidied up by moving these temporary/diagnostic files here.

### 🧠 Core ML & Normalization
- **[normalize_ml.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/normalize_ml.py)**: The latest normalization engine using ML (TF-IDF/Cosine Similarity) and Spec Expansion.
- **[audit_full_dictionary.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/audit_full_dictionary.py)**: Audit script that identified and fixed the iPhone 16/12 mis-mappings.
- **[normalize_data.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/normalize_data.py)**: Original rule-based normalization (kept for reference).

### 🛠️ Database & Spec Management
- **[apple_products_db.json](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/apple_products_db.json)**: The expanded reference database.
- **[scrape_apple_specs.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/scrape_apple_specs.py)**: Script used to scrape official Apple tech specs.
- **[add_future_products.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/add_future_products.py)**: Injector for iPhone 16/17 and other future models.
- **[update_db.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/update_db.py)**: SQLite management tool.

### 🔍 Diagnostics & Debugging (Tidied Up)
- **debug_*.py**: Scripts for tracing specific matching failures (ANC, blocking, keys, etc.).
- **[analyze_specs_granularity.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/analyze_specs_granularity.py)**: Analysis of spec token frequency.
- **[sanity_check_mappings.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/sanity_check_mappings.py)**: Final verification of mapping counts.

### 📊 Data Exports
- **[mappings_candidate.json](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/mappings_candidate.json)**: The final, high-fidelity mapping file.
- **tableau_*.csv**: Large data exports generated for Tableau visualization.

### 📖 Report
- **[summary_walkthrough.md](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/summary_walkthrough.md)**: Final report of all accomplishments today.
- **[patch_families.py](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/patch_families.py)**: Script to fix family/category labels in the DB.

### Databases & Logs:
- **[apple_prices.db](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/apple_prices.db)**: SQLite database containing historical price data.
- **[apple_products_db.json](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/apple_products_db.json)**: The expanded reference database of official Apple products.
- **[scraper_log.txt](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/database_review_20251228/scraper_log.txt)**: Log file containing debug info from the scraper and normalization runs.


### 📂 Permanent Archive (code/archive)
- **Legacy Tools**: All scraper comparison scripts and the `Daily Scraper Auto.app` have been moved to [code/archive/](file:///Users/brucehuynh/Documents/Code_Projects/Daily_Promotion/code/archive/) for long-term storage.
