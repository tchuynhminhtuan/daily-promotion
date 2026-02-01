import os
import sys

# 1. Add 'code' directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(PROJECT_ROOT, "src/reporting"))

# 2. Import the core report generator
import generate_report

import tempfile
import shutil

# 3. CONFIGURE PATHS FOR MARSHALL
MARSHALL_CONTENT = os.path.join(PROJECT_ROOT, "projects/marshall_daily/content")
MARSHALL_HTML = os.path.join(PROJECT_ROOT, "docs/marshall.html")

# Use a temporary directory for intermediate CSVs (Price Matrix / Promo Diff)
temp_dir = tempfile.mkdtemp()

try:
    # Override Module Globals
    generate_report.BASE_DIR = MARSHALL_CONTENT
    generate_report.PROMO_DIFF_HTML = MARSHALL_HTML
    generate_report.OUTPUT_DIR = temp_dir
    generate_report.PRICE_MATRIX_FILE = os.path.join(temp_dir, "price_matrix.csv")
    generate_report.PROMO_DIFF_CSV = os.path.join(temp_dir, "promo_diff_report.csv")

    # 4. RE-CALCULATE DATES FOR MARSHALL DATA
    available = generate_report.get_available_dates(MARSHALL_CONTENT)
    if len(available) >= 2:
        generate_report.DATES = available[-2:]
    elif available:
        generate_report.DATES = available
    else:
        generate_report.DATES = []

    # 5. EXECUTE
    if __name__ == "__main__":
        print(f"🛠️ Marshall Launcher: Overriding BASE_DIR to {MARSHALL_CONTENT}")
        print(f"🛠️ Marshall Launcher: Using temporary output dir {temp_dir}")
        generate_report.main()
finally:
    # Clean up temp directory - we only want the .html report
    shutil.rmtree(temp_dir)
    print(f"🧹 Marshall Launcher: Cleaned up temporary files.")
