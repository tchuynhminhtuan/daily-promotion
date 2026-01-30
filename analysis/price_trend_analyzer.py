"""
Price Trend Analyzer
Analyzes historical price data from daily-promotion scraping results.
Uses product_catalog.yaml for canonicalization.
"""

import os
import sys
import yaml
import pandas as pd
import glob
import re
from collections import defaultdict
from datetime import datetime

# --- Config ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(SCRIPT_DIR, "reference", "product_catalog.yaml")
CONTENT_DIR = os.path.join(PROJECT_ROOT, "content")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# --- Catalog Loading ---
PRODUCT_CATALOG = {}
VARIANT_INDEX = {}  # normalized_variant_name -> canonical_key

def normalize_name(name) -> str:
    """Remove noise to improve matching."""
    if not name or not isinstance(name, str):
        return ""
    result = name.lower()
    for char in ["(", ")", "/", ",", "-", "|", "[", "]", "'"]:
        result = result.replace(char, " ")
    
    # Remove common filler words
    remove_words = [
        "chính hãng", "vn/a", "vn a", "apple", "mới", "new", "giá rẻ",
        "trả góp 0%", "giảm", "triệu", "tặng", "bảo hành"
    ]
    for w in remove_words:
        result = result.replace(w, " ")
    
    # Collapse spaces
    result = " ".join(result.split())
    return result.strip()

def load_catalog():
    """Load YAML and build reverse index."""
    global PRODUCT_CATALOG, VARIANT_INDEX
    
    if not os.path.exists(CATALOG_PATH):
        print(f"⚠️ Catalog not found: {CATALOG_PATH}")
        return
    
    print(f"📖 Loading catalog: {os.path.basename(CATALOG_PATH)}")
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        PRODUCT_CATALOG = yaml.safe_load(f)
    
    for key, data in PRODUCT_CATALOG.items():
        # Index the canonical key itself
        VARIANT_INDEX[normalize_name(data.get("name", key))] = key
        # Index all variants
        for v in data.get("variants", []):
            VARIANT_INDEX[normalize_name(v)] = key
    
    print(f"   ✅ Indexed {len(VARIANT_INDEX)} variants for {len(PRODUCT_CATALOG)} products.")

def get_canonical_key(raw_name: str) -> str:
    """Return canonical key if found in catalog, else None."""
    return VARIANT_INDEX.get(normalize_name(raw_name))

def get_product_info(canonical_key: str) -> dict:
    """Return category and canonical name from catalog."""
    data = PRODUCT_CATALOG.get(canonical_key, {})
    return {
        "canonical_name": data.get("name", canonical_key),
        "category": data.get("category", "unknown")
    }

# --- Color Normalization ---
COLOR_MAP = {
    # Vietnamese to English Standard
    "trắng": "White",
    "đen": "Black",
    "xám": "Gray",
    "bạc": "Silver",
    "vàng": "Gold",
    "hồng": "Pink",
    "tím": "Purple",
    "xanh dương": "Blue",
    "xanh lá": "Green",
    "xanh": "Blue",  # Fallback for generic "Xanh"
    "đỏ": "Red",
    "cam": "Orange",
    # Apple Titanium colors
    "titan đen": "Black Titanium",
    "titan tự nhiên": "Natural Titanium",
    "titan trắng": "White Titanium",
    "titan xanh": "Blue Titanium",
    "titan sa mạc": "Desert Titanium",
    "natural titanium": "Natural Titanium",
    "black titanium": "Black Titanium",
    "white titanium": "White Titanium",
    "desert titanium": "Desert Titanium",
    "blue titanium": "Blue Titanium",
    # Apple Watch specific
    "ánh sao": "Starlight",
    "starlight": "Starlight",
    "midnight": "Midnight",
    "nửa đêm": "Midnight",
    # iPhone 15/16 specific
    "ultramarine": "Ultramarine",
    "teal": "Teal",
}

def normalize_color(raw_color) -> str:
    """Map raw color to standard English."""
    if not raw_color or not isinstance(raw_color, str):
        return "Unknown"
    
    color_lower = raw_color.strip().lower()
    return COLOR_MAP.get(color_lower, raw_color.title())

# --- Data Loading ---
def load_all_data() -> pd.DataFrame:
    """Load all CSVs from content/* directories."""
    all_files = glob.glob(os.path.join(CONTENT_DIR, "*", "*.csv"))
    if not all_files:
        print(f"❌ No CSV files found in {CONTENT_DIR}")
        return pd.DataFrame()
    
    print(f"📂 Found {len(all_files)} CSV files.")
    
    frames = []
    for f in all_files:
        try:
            df = pd.read_csv(f, sep=";", on_bad_lines="skip", encoding="utf-8")
            frames.append(df)
        except Exception as e:
            print(f"   ⚠️ Error reading {os.path.basename(f)}: {e}")
    
    if not frames:
        return pd.DataFrame()
    
    combined = pd.concat(frames, ignore_index=True)
    print(f"📊 Loaded {len(combined)} total rows.")
    return combined

# --- Analysis ---
def analyze_trends(df: pd.DataFrame):
    """
    Analyze price trends by (Canonical_Key, Color).
    Returns a DataFrame with trend summary.
    """
    if df.empty:
        return pd.DataFrame()
    
    # Ensure numeric price column
    df["Gia_Khuyen_Mai"] = pd.to_numeric(df["Gia_Khuyen_Mai"], errors="coerce").fillna(0)
    
    # Filter: Price > 0 AND < 500,000,000 (500 million VND max for Apple products)
    df = df[(df["Gia_Khuyen_Mai"] > 0) & (df["Gia_Khuyen_Mai"] < 500_000_000)].copy()
    
    # Normalize columns
    df["canonical_key"] = df["Product_Name"].apply(get_canonical_key)
    df["color_normalized"] = df["Color"].apply(normalize_color)
    
    # Filter known products only
    df_known = df[df["canonical_key"].notna()].copy()
    df_unknown = df[df["canonical_key"].isna()]
    
    print(f"   ✅ Matched: {len(df_known)} rows, Unmatched: {len(df_unknown)} rows")
    
    if not df_known.empty:
        # Add canonical name for readability
        df_known["canonical_name"] = df_known["canonical_key"].apply(
            lambda k: get_product_info(k)["canonical_name"]
        )
        df_known["category"] = df_known["canonical_key"].apply(
            lambda k: get_product_info(k)["category"]
        )
    
    # Group by (Product, Color, Date)
    grouped = df_known.groupby(
        ["canonical_name", "color_normalized", "Date"]
    ).agg(
        min_price=("Gia_Khuyen_Mai", "min"),
        max_price=("Gia_Khuyen_Mai", "max"),
        avg_price=("Gia_Khuyen_Mai", "mean"),
        count=("Gia_Khuyen_Mai", "count")
    ).reset_index()
    
    # Overall trend per (Product, Color)
    trend = grouped.groupby(["canonical_name", "color_normalized"]).agg(
        overall_min=("min_price", "min"),
        overall_max=("max_price", "max"),
        overall_avg=("avg_price", "mean"),
        data_points=("count", "sum"),
        first_date=("Date", "min"),
        last_date=("Date", "max")
    ).reset_index()
    
    trend["price_range"] = trend["overall_max"] - trend["overall_min"]
    trend["volatility_pct"] = (trend["price_range"] / trend["overall_avg"] * 100).round(2)
    
    # Sort by highest volatility
    trend = trend.sort_values("volatility_pct", ascending=False)
    
    return trend

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Load Catalog
    load_catalog()
    
    # 2. Load Data
    df = load_all_data()
    if df.empty:
        print("❌ No data to analyze.")
        return
    
    # 3. Analyze
    print("\n🔍 Analyzing price trends...")
    trends = analyze_trends(df)
    
    if trends.empty:
        print("⚠️ No trend data generated.")
        return
    
    # 4. Output
    output_file = os.path.join(OUTPUT_DIR, "price_trends_by_color.csv")
    trends.to_csv(output_file, index=False)
    print(f"\n✅ Saved: {output_file}")
    
    # 5. Summary
    print("\n📈 TOP 10 MOST VOLATILE PRODUCTS (by Color):")
    print("-" * 80)
    for _, row in trends.head(10).iterrows():
        print(f"  {row['canonical_name']} | {row['color_normalized']} | "
              f"Range: {row['price_range']:,.0f}đ | Volatility: {row['volatility_pct']:.1f}%")
    print("-" * 80)
    
    print("\n🎯 ANALYSIS COMPLETE!")

if __name__ == "__main__":
    main()
