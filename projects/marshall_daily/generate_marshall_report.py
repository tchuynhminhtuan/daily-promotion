import os
import sys

# 1. Add 'code' directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(PROJECT_ROOT, "code"))

# 2. Import the core report generator
import generate_report

# 3. CONFIGURE PATHS FOR MARSHALL
# We override these globals in the module so main() uses them
MARSHALL_CONTENT = os.path.join(PROJECT_ROOT, "projects/marshall_daily/content")
MARSHALL_HTML = os.path.join(PROJECT_ROOT, "docs/marshall.html")

# Override Module Globals
generate_report.BASE_DIR = MARSHALL_CONTENT
generate_report.PROMO_DIFF_HTML = MARSHALL_HTML
generate_report.OUTPUT_DIR = os.path.join(MARSHALL_CONTENT, "analysis_result")
generate_report.PRICE_MATRIX_FILE = os.path.join(generate_report.OUTPUT_DIR, "price_matrix.csv")
generate_report.PROMO_DIFF_CSV = os.path.join(generate_report.OUTPUT_DIR, "promo_diff_report.csv")

# 4. RE-CALCULATE DATES FOR MARSHALL DATA
# (Since it was already calculated for the real 'content' folder on import)
available = generate_report.get_available_dates(MARSHALL_CONTENT)
if len(available) >= 2:
    generate_report.DATES = available[-2:]
elif available:
    generate_report.DATES = available
else:
    generate_report.DATES = [] # Or fallback

# 5. EXECUTE
if __name__ == "__main__":
    print(f"🛠️ Marshall Launcher: Overriding BASE_DIR to {MARSHALL_CONTENT}")
    print(f"🛠️ Marshall Launcher: Overriding OUTPUT to {MARSHALL_HTML}")
    generate_report.main()
