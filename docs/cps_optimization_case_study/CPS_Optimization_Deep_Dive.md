# CellphoneS (CPS) Scraper Optimization Deep Dive

## The Problem
The CellphoneS website (CPS) presents a unique "Hybrid Navigation" challenge for scrapers:
1.  **Split State Management**:
    *   **Storage Variants** (e.g., 128GB vs 256GB) trigger a **Full Page URL Change** (e.g., `iphone-16.html` -> `iphone-16-256gb.html`).
    *   **Color Variants** (e.g., Black vs White) use **SPA (Single Page Application)** logic, updating the DOM and query parameters without a full reload.
2.  **Navigation Context Loss**: The original scraper treated links naively. Navigating to a storage variant would change the page context, breaking any loops that were iterating through options on the previous page.
3.  **Incomplete Data**: As a result, the scraper missed many storage configurations and/or color options, leading to low row counts (approx. 528 rows).

## Technical Analysis
*   **Storage**: Links are `<a>` tags with `href` pointing to new slugs.
*   **Color**: Clickable elements that trigger JavaScript updates (often updating a `product_id` or similar query param).
*   **Stock Status**: The "Buy" button text changes dynamically based on selection ("MUA NGAY" vs "ĐĂNG KÝ").

## Solution Implemented

### 1. `CPSInteractor` Class
Encapsulated all page interactions (`extract_data`, `process_colors`) into a class to manage state cleanly.

### 2. Two-Stage "Discover First" Strategy
To handle the full page navigation without losing context, the `process_url` function was redesigned:
*   **Discovery Phase**: Before any navigation, the scraper scans the initial page for *all* storage variant URLs (`a.item-linked`) and collects them into a list.
*   **Iteration Phase**: It then iterates through this list, creating a fresh `CPSInteractor` for each URL (or navigating the page to it). This decouples discovery from processing.

### 3. SPA Color Handling
Inside each storage variant page, the scraper:
*   Finds all color buttons (`.button__change-color`).
*   Clicks each one and waits for the SPA update.
*   Extracts data for that specific variant state.

## Results Comparison

| Metric | Old Scraper | New Scraper | Improvement |
| :--- | :--- | :--- | :--- |
| **Unique Links** | 188 | **287** | **+52%** |
| **Total Rows** | 528 | **742+** | **+40%** |
| **Logic** | Single-pass | **Multi-pass Hybrid** | Full coverage of Storage x Color matrix |

## Key Code Artifacts
*   `new_cps_scraper.py`: Optimized code handling hybrid navigation.
*   `compare_cps_results.py`: Verification script.
