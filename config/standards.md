# Standards for Product Catalog & Normalization

This document outlines the rules, conventions, and "gotchas" for maintaining the `product_catalog_golden_v2.yaml` and the normalization logic in `10-Normalize_and_Analyze.py`.

## 1. Category Guardrails (Cross-Category Contamination)

**Problem:** Products with generic names or shared keywords (e.g., "Titan", "Pro", "Series") can be misclassified into the wrong category.
*   *Example:* An "iPad Air Blue" matching "Apple Watch Series 6 Blue".
*   *Example:* "AirPods Pro" matching "iPad Pro" or "iPad Mini (A17 Pro)".

**Rule:** The `match_product` function MUST enforce strict negative checks based on the target category.

| Target Category | Negative Keywords (Rejects Item if Present) | Rationale |
| :--- | :--- | :--- |
| **Watch** | `ipad`, `iphone`, `macbook`, `imac`, `airpods`, `tai nghe`, `mac mini` | Prevents phones/tablets with "Titan" or "Series" from matching watches. |
| **iPad** | `iphone`, `watch`, `macbook`, `imac`, `airpods`, `tai nghe`, `mac mini` | Prevents "AirPods Pro" or "Mac Mini" from matching "iPad Pro/Mini". |
| **iPhone** | `ipad`, `watch`, `macbook`, `imac`, `airpods`, `tai nghe`, `mac mini` | General hygiene. |
| **Audio** | `ipad`, `iphone`, `watch`, `macbook`, `imac`, `mac mini` | Ensures Audio category only contains actual audio devices. |

## 2. Product Differentiation & Splitting

**Problem:** Aggregating distinct variants into a single catalog entry skews price analytics.
*   *Example:* Grouping "Apple Watch SE 3 GPS" (cheaper) and "Apple Watch SE 3 LTE" (expensive) into one `apple_watch_se_3` entry causes the average price to be artificially high for the GPS model.

**Rule:** Split catalog entries when technical specifications significantly affect price (Price Differentiation > 10-15%).

### Apple Watch Splitting
*   **GPS vs. Cellular:** MUST be split.
    *   `apple_watch_se_3_gps`: Keywords `GPS`.
    *   `apple_watch_se_3_lte`: Keywords `Cellular`, `LTE`, `5G`, `eSim`.
*   **Material:** MUST be split (Aluminum vs. Titanium/Steel).
    *   `apple_watch_series_10_aluminum`: Keywords `Nhôm`, `Aluminum`.
    *   `apple_watch_series_10_titanium`: Keywords `Titan`, `Titanium`. (**Note:** Do NOT use generic "Cellular" keywords here if the material is the primary differentiator, as all Titans are Cellular).

### iPad Mini Differentiation
*   **Problem:** Generic names like "iPad mini" or overlapping storage sizes (64GB vs 256GB) cause confusion between generations.
*   **Rule:** Use specific keywords for each generation.
    *   **iPad mini 6:** `iPad mini 6`, `mini 64GB`, `mini 256GB`, `Gen 6`.
    *   **iPad mini 7 (A17 Pro):** `iPad mini 7`, `A17`, `mini 128GB`, `mini 512GB`.
    *   *Avoid:* Generic `128GB` (conflicts with iPad Air). Use `mini 128GB`.

## 3. Storage Display Logic

**Problem:** "Storage" is irrelevant for some categories (Watch, Audio) and looks messy when displayed (e.g., "(unknown_storage)" for AirPods).
**Problem:** Redundant display "iPhone 15 128GB (128GB)".

**Rule:**
1.  **Watch / Audio:** NEVERY display storage capacity. Storage should be hidden in reports.
2.  **Known Storage:** If storage is successfully parsed and part of the normalized product name (e.g., "iPhone 15 128GB"), do NOT append it again in the parenthesis.
3.  **Unknown Storage:** Only display `(unknown_storage)` as a warning for categories where storage MATTERS (iPhone, iPad, Mac).

## 4. Retailer Mapping (Static Map)

**File:** `analysis/reference/retailer_mapping_v1.yaml`
**Rule:**
*   This file is a "hard override". If a product is mapped here, it skips all dynamic matching logic.
*   **Maintenance:** When deleting/renaming a catalog key (e.g., deleting `ipad_mini`), you MUST grep and update this file immediately. Failure to do so leads to crashes or "zombie" mappings.

