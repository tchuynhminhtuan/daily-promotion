# DDV Scraper Optimization Deep Dive

## The Problem
The original `5-Apple_DDV_playwright.py` scraper had significant issues with data completeness and accuracy:
1.  **Missing Storage Variants**: It failed to discover different storage configurations (e.g., 128GB vs 256GB) because it relied on simple interactions that didn't account for full URL changes.
2.  **Inaccurate Color Data**: Many products were listed with "Default" color because the selectors were too strict or failed to trigger the color selection logic.
3.  **Low Row Count**: The scraper only captured a subset of the available SKUs (approx. 235 rows vs 268+ expected).

## Technical Analysis
*   **Storage Navigation**: Inspection revealed that switching storage options (e.g., clicking "256GB") on Di Dong Viet triggers a **full page navigation** to a new URL (e.g., from `...128gb.html` to `...256gb.html`). The old scraper did not handle this and only scraped the default loaded option.
*   **Color Selection (SPA)**: Color options are handled via **Single Page Application (SPA)** updates. The URL changes query parameters (or hash), but the page does not reload. The old scraper's selectors for color buttons were brittle (expecting specific classes like `border-red-500` which varied by product).

## Solution Implemented

### 1. Robust `DDVInteractor` Class
Refactored the code into a class-based structure to better manage page state and logic.

### 2. Hybrid Navigation Strategy
*   **Storage Discovery**: The `process_url` function now first scans the page for ALL storage variant links (`a` tags with "GB" or "TB" text). It collects these URLs and navigates to each one sequentially using the *same* page instance.
*   **Color Iteration**: Inside each storage variant page, the `process_colors_grid` function iterates through color options using a relaxed selector (`div.cursor-pointer.rounded`).

### 3. Selector Improvements
*   **Relaxed Color Selector**: Changed from strict class matching to `div.cursor-pointer.rounded` + a Python-side check for "border" in the class string. This catches all color variants regardless of the specific border color class (e.g., `border-gray-200` vs `border-red-500`).
*   **Price Extraction**: Updated to handle multiple price formats and potential "Contact for price" scenarios.

## Results Comparison

| Metric | Old Scraper | New Scraper | Improvement |
| :--- | :--- | :--- | :--- |
| **Total Rows** | 235 | **268** | **+14%** |
| **Unique Variants** | 158 | **165** | **+4%** |
| **Data Quality** | Many "Default" colors | Specific colors (e.g., "Trắng", "Đen") | High |
| **Storage Coverage** | Partial | **Complete** (All GB/TB variants) | 100% |

## Key Code Artifacts
*   `new_ddv_scraper.py`: The optimized `DDVInteractor` implementation.
*   `compare_ddv_results.py`: Script used to verify the improvement.
