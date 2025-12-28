# DDV Scraper Optimization Case Study

This directory contains the documentation and artifacts for the optimization of the Di Dong Viet (DDV) scraper, performed to tackle issues with dynamic content (SPA) and variant discovery.

## Contents

*   **[DDV_Optimization_Deep_Dive.md](./DDV_Optimization_Deep_Dive.md)**: A detailed explanation of the problems encountered, the technical solutions implemented (Interactor pattern, hybrid navigation), and the verification results.
*   **[new_ddv_scraper.py](./new_ddv_scraper.py)**: The optimized source code using the `DDVInteractor` class.
*   **[compare_ddv_results.py](./compare_ddv_results.py)**: The Python script used to verify the improvements by comparing old and new CSV outputs.
*   **[new_ddv_result_2025-12-23.csv](./new_ddv_result_2025-12-23.csv)**: Sample output data from the optimized scraper.
*   **[old_ddv_result_2025-12-23.csv](./old_ddv_result_2025-12-23.csv)**: Sample output data from the original scraper (for baseline comparison).

## Summary of Results

Optimization led to a **14% increase in rows** and significantly improved data quality by correctly identifying specific color names instead of "Default" and capturing all storage variants.
