# Daily Promotion Tracker 🍎

This project tracks daily prices and promotions for Apple products across major Vietnamese retailers (FPT Shop, Mobile World, Viettel Store, HoangHa Mobile, Di Dong Viet, CellphoneS).

## 📂 Project Structure

The project follows a standard Python project layout:

*   **`config/`**: Configuration files.
    *   `product_catalog.yaml`: The "Golden Record" catalog used for normalization.
    *   `retailer_mapping.yaml`: Mappings key for standardizing retailer product names.
    *   `standards.md`: Documentation of catalog standards.
*   **`src/`**: Source code.
    *   **`crawlers/`**: Playwright scripts for scraping data (e.g., `1-Apple_FPT_playwright.py`).
    *   **`processing/`**: Data normalization and processing logic (`normalize.py`).
    *   **`reporting/`**: Report generation scripts (`generate_report.py`).
*   **`data/`**: Data storage.
    *   **`raw/`**: Raw CSV files scraped from retailers, organized by date (YYYY-MM-DD).
    *   **`normalized/`**: Processed and normalized data ready for analysis.
*   **`docs/`**: Output for GitHub Pages.
    *   `index.html`: The latest generated report.
    *   `insights/`: Daily markdown insights.
    *   `DESIGN.md`: System architecture and design principles.
*   **`legacy/`**: Archived code and data from previous versions.

## 🚀 How to Run

### 1. Analysis Pipeline (Normalization + Reporting)

To process raw data and generate reports:

```bash
# Step 1: Normalize Raw Data (e.g., for today)
python src/processing/normalize.py

# Optional: Normalize specific date
python src/processing/normalize.py 2026-02-01

# Step 2: Generate HTML Report
python src/reporting/generate_report.py
```

### 2. Crawlers (Scraping Data)

To run a specific crawler:

```bash
# Example: Scrape FPT Shop
python src/crawlers/1-Apple_FPT_playwright.py

# Example: Scrape CellphoneS
python src/crawlers/6-Apple_CPS_playwright.py
```

*Note: Crawlers output data to `data/raw/YYYY-MM-DD/`.*

## 🛠️ Setup

Ensure you have Python 3.8+ and dependencies installed:

```bash
pip install -r requirements.txt
playwright install
```

## 📝 Catalog Maintenance

*   Update `config/product_catalog.yaml` to add new authorized products.
*   Update `config/retailer_mapping.yaml` to fix persistent matching errors.
