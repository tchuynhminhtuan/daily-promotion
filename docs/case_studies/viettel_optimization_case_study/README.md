# Viettel Optimization Case Study

This directory contains artifacts from the performance optimization of the Viettel Store scraper (`3-Apple_Viettel_playwright.py`).

## Contents
*   `old_viettel_scraper.py`: Original scraper code (pre-optimization).
*   `new_viettel_scraper.py`: Optimized scraper code using `ViettelInteractor` class.
*   `old_viettel_result_2025-12-23.csv`: Data output from old scraper (409 rows).
*   `new_viettel_result_2025-12-23.csv`: Data output from new scraper (1327 rows).
*   `Viettel_Optimization_Deep_Dive.md`: Detailed walkthrough of the changes and root cause analysis.

## Key Results
*   **Data Yield:** Increased from 409 to 1327 rows (+224%).
*   **Issues Resolved:** SPA color selection timeouts, overlay blocking, and CSV parsing errors.
