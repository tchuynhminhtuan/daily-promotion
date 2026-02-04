
import sys
import argparse
import glob
import os
from datetime import datetime

# Adjust path to find src
sys.path.append(os.getcwd())

from src.utils.config import CONTENT_DIR, AI_ENABLED
from src.processing.processor import process_date_data
# from src.analysis.trend import load_historical_data, detect_anomalies, calculate_trend # Unused in main, moved to generator
from src.reporting.generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator, PROMO_DIFF_HTML

def get_available_dates():
    dates = []
    if not CONTENT_DIR.exists(): return []
    for d in os.listdir(CONTENT_DIR):
        if os.path.isdir(CONTENT_DIR / d):
            try:
                datetime.strptime(d, '%Y-%m-%d')
                dates.append(d)
            except:
                continue
    return sorted(dates)

def main(target_date=None, target_dates=None, process_all=False):
    available_dates = get_available_dates()
    
    if not available_dates:
        print("No data found in data/raw/")
        return
        
    dates_to_process = []
    
    if process_all:
        dates_to_process = available_dates
    elif target_dates:
        # Handle list of dates
        valid_dates = [d for d in target_dates if d in available_dates]
        if len(valid_dates) != len(target_dates):
             print(f"⚠️ Some dates not found or invalid: {set(target_dates) - set(valid_dates)}")
        dates_to_process = sorted(valid_dates)
        if not dates_to_process:
             print("No valid dates to process.")
             return
    elif target_date:
        if target_date in available_dates:
            dates_to_process = [target_date]
        else:
            print(f"Date {target_date} not found.")
            return
    else:
        # Default: Latest date
        dates_to_process = [available_dates[-1]]
        
    print(f"🚀 Starting Pipeline for {len(dates_to_process)} dates...")
    
    # 1. Process Data First
    for d in dates_to_process:
        print(f"\n📅 Processing: {d}")
        process_date_data(d)
        
    # 2. Generate Report (Using Standard Logic)
    # Load all data for the processed dates (or latest 2 for comparison if only 1 processed)
    report_dates = dates_to_process
    if len(report_dates) < 2 and len(available_dates) >= 2:
         # If single date processed, try to compare with previous
         idx = available_dates.index(report_dates[0])
         if idx > 0:
             report_dates = [available_dates[idx-1], report_dates[0]]
    
    print(f"\n📊 Generating Report for dates: {report_dates}")
    
    # Use standard generate_report logic
    df_report = DataLoader.load_all_data(dates=report_dates)
    if not df_report.empty:
        price_gen = PriceMatrixGenerator(df_report, skip_csv=True)
        price_gen.run()
        
        # Output to docs/index.html
        promo_gen = PromoDiffGenerator(df_report, price_gen, output_file=PROMO_DIFF_HTML, skip_csv=True, include_all=True)
        promo_gen.run()
    else:
        print("❌ Report generation skipped: No data loaded.")

    print("\n✅ Pipeline Complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily Promotion Pipeline')
    parser.add_argument('date', nargs='*', help='Target date(s) (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Process all dates')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI matching')
    
    args = parser.parse_args()
    
    # Global flag update approach?
    # In config.py: AI_ENABLED = True
    # We need to update it?
    # Better: engine.py imports AI_ENABLED. We can't easily change it globally unless we monkeypatch or usage arg.
    # For now, let's assume config is static or we use env var?
    # Hacky fix for refactor:
    if args.no_ai:
        import src.utils.config
        src.utils.config.AI_ENABLED = False
        print("⚠️ AI Disabled via flag")
        
    if args.all:
        main(process_all=True)
    else:
        # If dates are provided, pass them as a list (even if one)
        # But main expects 'target_date' as single or logic to handle list?
        # Let's adjust main to accept dates_list if needed, or we just patch it here.
        # Current main signature: main(target_date=None, process_all=False)
        # If I pass a LIST to target_date, does it work?
        # main logic:
        # elif target_date:
        #    if target_date in available_dates:
        #        dates_to_process = [target_date]
        
        # I need to update main() to handle a list.
        # Let's verify main() update below.
        
        dates = args.date if args.date else None
        # If single string (old behavior), existing main handles it if I modify main slightly.
        # If list, I need main to handle it.
        
        # Let's call main with specific arg tailored
        main(target_dates=dates)
