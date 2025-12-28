# CellphoneS (CPS) Scraper Optimization Case Study

This directory contains the documentation and artifacts for the optimization of the CellphoneS (CPS) scraper. This optimization specifically addressed the challenge of "Hybrid Navigation" where the site uses full page reloads for storage variants but SPA updates for color variants.

## Contents

*   **[CPS_Optimization_Deep_Dive.md](./CPS_Optimization_Deep_Dive.md)**: Detailed analysis of the hybrid navigation problem (Storage=URL, Color=SPA) and the `CPSInteractor` solution.
*   **[new_cps_scraper.py](./new_cps_scraper.py)**: The optimized source code.
*   **[compare_cps_results.py](./compare_cps_results.py)**: Python script used to verify the improvement.
*   **[new_cps_result_2025-12-24.csv](./new_cps_result_2025-12-24.csv)**: Output from the optimized scraper run.
*   **[old_cps_result_2025-12-23.csv](./old_cps_result_2025-12-23.csv)**: Output from the original scraper (baseline).

## Summary of Results

*   **Coverage**: Unique links discovered increased by **52%** (188 -> 287).
*   **Volume**: Total data rows increased by **40%** (528 -> 742+).
*   **Quality**: Correctly captures all valid combinations of storage and color.

## Gap Filling & Variant Discovery (Added 2025-12-24)

Optimization revealed that the `sites.py` input list was missing many storage variants (e.g., listing iPhone 13 128GB but missing 256GB). The `6-Apple_CPS_playwright.py` scraper now includes an optional **Gap Filling** mode to discover these.

### Artifacts
*   **[discover_cps_variants.py](./discover_cps_variants.py)**: A standalone, high-speed script to scan all URLs in `sites.py` and identify any linked storage variants that are MISSING from the input list.
*   **[discovered_cps_variants.txt](./discovered_cps_variants.txt)**: The result of a scan run on Dec 24, 2025. It contains **124 URLs** that were missing from `sites.py`.

### How to Use
1.  **Discovery Scan**: Run `python3 docs/cps_optimization_case_study/discover_cps_variants.py` to generate a list of missing links.
2.  **Integration**: Add the contents of `discovered_cps_variants.txt` to `utils/sites.py` to enable fast, parallel scraping of these items in future runs.
3.  **Gap Filling Mode**: Alternatively, run the main scraper with `ENABLE_GAP_FILLING=True` to discover them on the fly (slower).
