"""
Daily AI Insight Generator
Analyzes today's price data against historical records.
Generates insights: anomalies, best deals, trends (market-wide + per-store).
"""

import os
import sys
import yaml
import pandas as pd
import numpy as np
import glob
from datetime import datetime, timedelta
from scipy import stats

# --- Config ---
# Configuration
BASE_DIR = os.path.join(os.path.dirname(__file__), "../content")
# Save reports to docs/insights so they are published to GitHub Pages
REPORT_DIR = os.path.join(os.path.dirname(__file__), "../docs/insights")
# Ensure directory exists
os.makedirs(REPORT_DIR, exist_ok=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(SCRIPT_DIR, "reference", "product_catalog.yaml")
CONTENT_DIR = os.path.join(PROJECT_ROOT, "content") # This might need to be adjusted based on BASE_DIR if BASE_DIR is meant to replace it. Keeping it for now as per strict instruction.
# REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports") # This is replaced by REPORT_DIR

# Thresholds
ANOMALY_THRESHOLD = 0.10  # 10% deviation = anomaly
TREND_DAYS = 30
AVG_DAYS = 7
MAX_PRICE = 500_000_000  # Filter out parsing errors

# Store name mapping from CSV filename prefix
STORE_MAP = {
    "1-fpt": "FPT Shop",
    "1-shopdunk": "ShopDunk",
    "2-mw": "Mobile World",
    "3-viettel": "Viettel Store",
    "3-cellphones": "CellphoneS",
    "4-hoangha": "HoangHa",
    "5-ddv": "Di Động Việt",
    "5-fpt": "FPT Shop",
    "6-cps": "CellphoneS",
    "6-tgdd": "TGDD",
}

# --- Catalog (reuse from price_trend_analyzer) ---
PRODUCT_CATALOG = {}
VARIANT_INDEX = {}

def normalize_name(name) -> str:
    if not name or not isinstance(name, str):
        return ""
    result = name.lower()
    for char in ["(", ")", "/", ",", "-", "|", "[", "]", "'"]:
        result = result.replace(char, " ")
    remove_words = [
        "chính hãng", "vn/a", "vn a", "apple", "mới", "new", "giá rẻ",
        "trả góp 0%", "giảm", "triệu", "tặng", "bảo hành"
    ]
    for w in remove_words:
        result = result.replace(w, " ")
    result = " ".join(result.split())
    return result.strip()

def load_catalog():
    global PRODUCT_CATALOG, VARIANT_INDEX
    if not os.path.exists(CATALOG_PATH):
        print(f"⚠️ Catalog not found: {CATALOG_PATH}")
        return
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        PRODUCT_CATALOG = yaml.safe_load(f)
    for key, data in PRODUCT_CATALOG.items():
        VARIANT_INDEX[normalize_name(data.get("name", key))] = key
        for v in data.get("variants", []):
            VARIANT_INDEX[normalize_name(v)] = key
    print(f"📖 Catalog: {len(PRODUCT_CATALOG)} products, {len(VARIANT_INDEX)} variants")

def get_canonical_key(raw_name):
    return VARIANT_INDEX.get(normalize_name(raw_name))

def get_canonical_name(key):
    return PRODUCT_CATALOG.get(key, {}).get("name", key)

# --- Color Normalizer ---
COLOR_MAP = {
    "trắng": "White", "đen": "Black", "xám": "Gray", "bạc": "Silver",
    "vàng": "Gold", "hồng": "Pink", "tím": "Purple", "xanh dương": "Blue",
    "xanh lá": "Green", "xanh": "Blue", "đỏ": "Red", "cam": "Orange",
    "titan đen": "Black Titanium", "titan tự nhiên": "Natural Titanium",
    "titan trắng": "White Titanium", "titan xanh": "Blue Titanium",
    "titan sa mạc": "Desert Titanium", "ánh sao": "Starlight",
    "nửa đêm": "Midnight", "ultramarine": "Ultramarine", "teal": "Teal",
}

def normalize_color(raw_color) -> str:
    if not raw_color or not isinstance(raw_color, str):
        return "Unknown"
    color_lower = raw_color.strip().lower()
    return COLOR_MAP.get(color_lower, raw_color.title())

# --- Data Loading ---
def load_all_data() -> pd.DataFrame:
    """Load all CSVs with store identification."""
    all_files = glob.glob(os.path.join(CONTENT_DIR, "*", "*.csv"))
    if not all_files:
        return pd.DataFrame()
    
    frames = []
    for f in all_files:
        try:
            df = pd.read_csv(f, sep=";", on_bad_lines="skip", encoding="utf-8")
            # Extract store from filename
            basename = os.path.basename(f)
            for prefix, store in STORE_MAP.items():
                if basename.startswith(prefix):
                    df["Store"] = store
                    break
            else:
                df["Store"] = "Unknown"
            frames.append(df)
        except Exception:
            pass
    
    if not frames:
        return pd.DataFrame()
    
    combined = pd.concat(frames, ignore_index=True)
    
    # Clean up
    combined["Gia_Khuyen_Mai"] = pd.to_numeric(combined["Gia_Khuyen_Mai"], errors="coerce").fillna(0)
    
    # Filter 1: Valid Price
    combined = combined[(combined["Gia_Khuyen_Mai"] > 0) & (combined["Gia_Khuyen_Mai"] < MAX_PRICE)]
    
    # Filter 2: In Stock Only (Ton_Kho contains 'Yes' or 'Co')
    if "Ton_Kho" in combined.columns:
        # Normalize to string and lower case
        combined = combined[combined["Ton_Kho"].astype(str).str.lower().str.contains("yes|có|co", na=False)]
    
    combined["canonical_key"] = combined["Product_Name"].apply(get_canonical_key)
    combined["color_normalized"] = combined["Color"].apply(normalize_color)
    combined = combined[combined["canonical_key"].notna()].copy()
    combined["canonical_name"] = combined["canonical_key"].apply(get_canonical_name)
    
    print(f"📊 Loaded {len(combined)} valid rows from {len(all_files)} files")
    return combined

# --- Analysis Functions ---
def calculate_moving_average(df, group_cols, days=7):
    """Calculate N-day moving average for each group."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    
    result = df.groupby(group_cols + ["Date"]).agg(
        avg_price=("Gia_Khuyen_Mai", "mean")
    ).reset_index()
    
    result = result.sort_values(group_cols + ["Date"])
    result[f"ma_{days}d"] = result.groupby(group_cols)["avg_price"].transform(
        lambda x: x.rolling(days, min_periods=1).mean()
    )
    return result

def detect_anomalies(df, target_date, group_cols, label=""):
    """Detect price anomalies vs moving average."""
    target_dt = pd.to_datetime(target_date)
    
    ma_df = calculate_moving_average(df, group_cols, AVG_DAYS)
    
    # Get yesterday's MA as baseline
    yesterday = target_dt - timedelta(days=1)
    baseline = ma_df[ma_df["Date"] == yesterday][group_cols + [f"ma_{AVG_DAYS}d"]].copy()
    baseline.columns = group_cols + ["baseline_ma"]
    
    # Get today's prices
    today_df = df[pd.to_datetime(df["Date"]) == target_dt].copy()
    today_agg = today_df.groupby(group_cols).agg(
        today_price=("Gia_Khuyen_Mai", "mean"),
        today_count=("Gia_Khuyen_Mai", "count")
    ).reset_index()
    
    # Merge and calculate deviation
    merged = today_agg.merge(baseline, on=group_cols, how="left")
    merged = merged.dropna(subset=["baseline_ma"])
    merged["deviation"] = (merged["today_price"] - merged["baseline_ma"]) / merged["baseline_ma"]
    
    # Filter anomalies
    anomalies = merged[abs(merged["deviation"]) > ANOMALY_THRESHOLD].copy()
    anomalies["type"] = anomalies["deviation"].apply(lambda x: "📉 GIẢM" if x < 0 else "📈 TĂNG")
    anomalies["deviation_pct"] = (anomalies["deviation"] * 100).round(1)
    
    return anomalies.sort_values("deviation")

def detect_best_price_ever(df, target_date):
    """Find products at their historical low price."""
    target_dt = pd.to_datetime(target_date)
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Historical min per product-color
    historical = df[df["Date"] < target_dt].groupby(
        ["canonical_name", "color_normalized"]
    ).agg(historical_min=("Gia_Khuyen_Mai", "min")).reset_index()
    
    # Today's prices
    today = df[df["Date"] == target_dt].groupby(
        ["canonical_name", "color_normalized"]
    ).agg(today_price=("Gia_Khuyen_Mai", "min")).reset_index()
    
    merged = today.merge(historical, on=["canonical_name", "color_normalized"], how="left")
    merged = merged.dropna()
    
    # Find best prices
    best = merged[merged["today_price"] <= merged["historical_min"]].copy()
    best["savings"] = merged["historical_min"] - merged["today_price"]
    
    return best.sort_values("savings", ascending=False)

def calculate_trend(df, group_cols, days=30):
    """Calculate trend using linear regression."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    
    cutoff = df["Date"].max() - timedelta(days=days)
    recent = df[df["Date"] >= cutoff]
    
    daily = recent.groupby(group_cols + ["Date"]).agg(
        price=("Gia_Khuyen_Mai", "mean")
    ).reset_index()
    
    results = []
    for name, group in daily.groupby(group_cols):
        if len(group) < 5:  # Need at least 5 data points
            continue
        
        group = group.sort_values("Date")
        x = np.arange(len(group))
        y = group["price"].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Calculate % change over period
        pct_change = (slope * len(group)) / y.mean() * 100
        
        if pct_change < -5:
            trend = "🔻 Giảm"
        elif pct_change > 5:
            trend = "🔺 Tăng"
        else:
            trend = "➡️ Ổn định"
        
        row = {col: val for col, val in zip(group_cols, name if isinstance(name, tuple) else [name])}
        row.update({
            "trend": trend,
            "pct_change": round(pct_change, 1),
            "r_squared": round(r_value**2, 2),
            "first_price": y[0],
            "last_price": y[-1]
        })
        results.append(row)
    
    return pd.DataFrame(results)

# --- Report Generation ---
def generate_report(target_date, df):
    """Generate markdown report for the target date."""
    target_dt = pd.to_datetime(target_date)
    date_str = target_dt.strftime("%Y-%m-%d")
    
    report_lines = [
        f"# 📊 Daily Price Insights - {date_str}",
        f"",
        f"*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
    ]
    
    # --- Section 1: Best Deals ---
    report_lines.append("## 💰 BEST PRICE EVER (Giá thấp nhất lịch sử)")
    best_prices = detect_best_price_ever(df, target_date)
    if len(best_prices) > 0:
        for _, row in best_prices.head(10).iterrows():
            report_lines.append(
                f"- **{row['canonical_name']}** ({row['color_normalized']}): "
                f"**{row['today_price']:,.0f}đ** ← Giá thấp nhất từ trước tới nay!"
            )
    else:
        report_lines.append("_Không có sản phẩm nào đạt giá thấp nhất lịch sử hôm nay._")
    report_lines.append("")
    
    # --- Section 2: Market-wide Anomalies ---
    report_lines.append("## ⚠️ ANOMALIES - THỊ TRƯỜNG (vs 7-day avg)")
    market_anomalies = detect_anomalies(
        df, target_date, 
        ["canonical_name", "color_normalized"],
        label="market"
    )
    if len(market_anomalies) > 0:
        for _, row in market_anomalies.head(10).iterrows():
            report_lines.append(
                f"- {row['type']} **{row['canonical_name']}** ({row['color_normalized']}): "
                f"{row['deviation_pct']:+.1f}% → {row['today_price']:,.0f}đ"
            )
    else:
        report_lines.append("_Không phát hiện biến động bất thường._")
    report_lines.append("")
    
    # --- Section 3: Per-Store Anomalies ---
    report_lines.append("## 🏪 ANOMALIES - TỪNG CHUỖI (vs 7-day avg)")
    store_anomalies = detect_anomalies(
        df, target_date,
        ["Store", "canonical_name", "color_normalized"],
        label="store"
    )
    if len(store_anomalies) > 0:
        for _, row in store_anomalies.head(15).iterrows():
            report_lines.append(
                f"- {row['type']} [{row['Store']}] **{row['canonical_name']}** ({row['color_normalized']}): "
                f"{row['deviation_pct']:+.1f}%"
            )
    else:
        report_lines.append("_Không phát hiện biến động bất thường._")
    report_lines.append("")
    
    # --- Section 4: Market Trends ---
    report_lines.append("## 📈 XU HƯỚNG 30 NGÀY - THỊ TRƯỜNG")
    market_trends = calculate_trend(df, ["canonical_name", "color_normalized"], TREND_DAYS)
    if len(market_trends) > 0:
        # Show top movers
        big_movers = market_trends[abs(market_trends["pct_change"]) > 5].sort_values("pct_change")
        for _, row in big_movers.head(10).iterrows():
            report_lines.append(
                f"- {row['trend']} **{row['canonical_name']}** ({row['color_normalized']}): "
                f"{row['pct_change']:+.1f}% ({row['first_price']:,.0f}đ → {row['last_price']:,.0f}đ)"
            )
    else:
        report_lines.append("_Chưa đủ dữ liệu để phân tích xu hướng._")
    report_lines.append("")
    
    # --- Section 5: Per-Store Trends ---
    report_lines.append("## 🏪 XU HƯỚNG 30 NGÀY - TỪNG CHUỖI")
    store_trends = calculate_trend(df, ["Store", "canonical_name", "color_normalized"], TREND_DAYS)
    if len(store_trends) > 0:
        big_store_movers = store_trends[abs(store_trends["pct_change"]) > 10].sort_values("pct_change")
        for _, row in big_store_movers.head(15).iterrows():
            report_lines.append(
                f"- {row['trend']} [{row['Store']}] **{row['canonical_name']}** ({row['color_normalized']}): "
                f"{row['pct_change']:+.1f}%"
            )
    else:
        report_lines.append("_Chưa đủ dữ liệu để phân tích xu hướng._")
    report_lines.append("")
    
    # --- Footer ---
    report_lines.append("---")
    report_lines.append(f"*Data sources: {df['Store'].nunique()} stores, {len(df)} price records*")
    
    return "\n".join(report_lines)

# --- Main ---
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date YYYY-MM-DD", default=None)
    args = parser.parse_args()
    
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # Default to latest date in data
    load_catalog()
    df = load_all_data()
    
    if df.empty:
        print("❌ No data to analyze.")
        return
    
    if args.date:
        target_date = args.date
    else:
        target_date = pd.to_datetime(df["Date"]).max().strftime("%Y-%m-%d")
    
    print(f"🎯 Analyzing date: {target_date}")
    
    # Generate report
    report = generate_report(target_date, df)
    
    # Save
    output_file = os.path.join(REPORT_DIR, f"{target_date}_insights.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ Report saved: {output_file}")
    print("\n" + "="*60)
    print(report[:2000] + "...\n[truncated]" if len(report) > 2000 else report)

if __name__ == "__main__":
    main()
