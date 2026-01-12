import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import streamlit.components.v1 as components

# Add the 'code' directory to path so we can import generate_report
# We assume the script is running from the root of the repo
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))
from generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator, get_available_dates, BASE_DIR

# --- Page Config ---
st.set_page_config(
    page_title="Daily Promotion Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- App Title ---
st.title("🚀 Daily Promotion: Interactive Dashboard")
st.markdown("""
This dashboard allows you to compare product prices and promotions across different dates. 
It replaces the Google Colab notebook and securely accesses your private data.
""")

# --- Sidebar: Date Selection ---
st.sidebar.header("📅 Report Settings")

available_dates = get_available_dates(BASE_DIR)

if not available_dates:
    st.error(f"❌ No data folders found in `{BASE_DIR}`. Please ensure your scrapers have run.")
else:
    # 1. Select Dates
    st.sidebar.subheader("Select Comparison Dates")
    
    # Sort dates for UI (Newest first)
    ui_dates = sorted(available_dates, reverse=True)
    
    new_date = st.sidebar.selectbox(
        "Current Date (New)", 
        ui_dates, 
        index=0,
        help="The most recent date for comparison."
    )
    
    # Default previous date is the one before the new_date in the sorted list
    try:
        current_idx = ui_dates.index(new_date)
        default_prev_idx = min(current_idx + 1, len(ui_dates) - 1)
    except:
        default_prev_idx = 0

    old_date = st.sidebar.selectbox(
        "Previous Date (Old)", 
        ui_dates, 
        index=default_prev_idx,
        help="The earlier date to compare against."
    )

    st.sidebar.divider()

    # 2. Advanced Options
    include_all = st.sidebar.checkbox("Include Unchanged Products", value=True)
    
    # 3. Action Button
    if st.sidebar.button("✨ Generate Interactive Report", use_container_width=True):
        if new_date == old_date:
            st.warning("⚠️ Please select two different dates for comparison.")
        else:
            with st.status(f"Comparing `{old_date}` ➔ `{new_date}`...", expanded=True) as status:
                st.write("📥 Loading data from CSVs...")
                df = DataLoader.load_all_data(dates=[old_date, new_date], base_dir=BASE_DIR)
                
                if df.empty:
                    st.error("❌ No data found for the selected dates.")
                    status.update(label="Report Generation Failed", state="error")
                else:
                    st.write(f"📊 Processing {len(df)} records...")
                    
                    # Run Price Matrix
                    price_gen = PriceMatrixGenerator(df, skip_csv=True)
                    price_gen.run()
                    
                    # Run Promo Diff and Output to a specific file
                    report_filename = f"report_{old_date}_vs_{new_date}.html"
                    promo_gen = PromoDiffGenerator(
                        df, 
                        price_gen, 
                        output_file=report_filename, 
                        skip_csv=True, 
                        include_all=include_all
                    )
                    promo_gen.run()
                    
                    st.write("✅ Report generated successfully.")
                    status.update(label="Report Ready", state="complete", expanded=False)
                    
                    # --- Display Results ---
                    st.divider()
                    st.subheader(f"📊 Comparison: {old_date} vs {new_date}")
                    
                    # Get stats if possible (or just show the HTML)
                    # For now, we embed the HTML
                    if os.path.exists(report_filename):
                        with open(report_filename, "r", encoding="utf-8") as f:
                            html_content = f.read()
                        
                        # Embed the interactive report
                        components.html(html_content, height=1200, scrolling=True)
                        
                        # Provide download button
                        st.download_button(
                            label="📥 Download HTML Report",
                            data=html_content,
                            file_name=f"promotion_report_{new_date}.html",
                            mime="text/html"
                        )
                    else:
                        st.error("Failed to render HTML report.")

# --- Footer ---
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Version 1.0")
