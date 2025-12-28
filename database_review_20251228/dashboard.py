
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import os

# Page Config
st.set_page_config(
    page_title="Apple Price Tracker",
    page_icon="🍎",
    layout="wide"
)

DB_FILE = "apple_prices.db"

# --- Database Functions ---
# Removed @st.cache_data to ensure fresh data during debugging
def get_families():
    """Fetch distinct product families."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT DISTINCT family FROM products WHERE family IS NOT NULL ORDER BY family"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['family'].tolist()
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []

def get_models_by_family(family):
    """Fetch models for a given family that have at least one price record."""
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT p.model_key, p.id
        FROM products p
        WHERE p.family = ?
        AND EXISTS (SELECT 1 FROM prices pr WHERE pr.product_id = p.id)
        ORDER BY p.model_key
    """
    df = pd.read_sql_query(query, conn, params=(family,))
    conn.close()
    return df

def get_price_history(product_id):
    """Fetch price history for a specific product."""
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT date, retailer, price, in_stock, url, raw_name
        FROM prices
        WHERE product_id = ? AND price > 0
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=(product_id,))
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# --- UI Layout ---

# Title
st.title("🍎 Apple Price Tracker")
st.markdown(f"Track historical prices across Vietnamese retailers. (DB: `{DB_FILE}`)")

# Check DB
if not os.path.exists(DB_FILE):
    st.error(f"Database not found at {os.path.abspath(DB_FILE)}")
    st.stop()

# Sidebar Filters
st.sidebar.header("Filters")

families = get_families()

if not families:
    st.sidebar.warning("No Families found in DB.")
    st.warning("Database contains no Product Families. Please check `products` table.")
    st.stop()

selected_family = st.sidebar.selectbox("Select Family", families)

if selected_family:
    models_df = get_models_by_family(selected_family)
    model_options = models_df['model_key'].tolist()
    
    # Default to first model
    selected_model_name = st.sidebar.selectbox("Select Model", model_options)
    
    if selected_model_name:
        # Get Product ID
        product_id = models_df[models_df['model_key'] == selected_model_name]['id'].values[0]
        
        # Load Data
        df = get_price_history(product_id)
        
        if df.empty:
            st.warning(f"No price data found for **{selected_model_name}**.")
        else:
            # --- KPIs ---
            latest_date = df['date'].max()
            latest_df = df[df['date'] == latest_date]
            
            if not latest_df.empty:
                min_row = latest_df.loc[latest_df['price'].idxmin()]
                min_price = min_row['price']
                best_retailer = min_row['retailer']
                
                # Format Price
                def fmt_vnd(p): return f"{p:,.0f} ₫".replace(",", ".")

                # Columns for KPIs
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Best Price Today", fmt_vnd(min_price), delta=None)
                with col2:
                    st.metric("Retailer", best_retailer.upper())
                with col3:
                    st.metric("Last Updated", latest_date.strftime("%Y-%m-%d"))
            
            # --- Chart ---
            st.subheader("Price History")
            
            # Line Chart with Altair (for interactivity)
            chart = alt.Chart(df).mark_line(point=True).encode(
                x='date:T',
                y=alt.Y('price:Q', axis=alt.Axis(format=',d', title='Price (VND)')),
                color='retailer:N',
                tooltip=['date', 'retailer', 'price', 'in_stock', 'raw_name']
            ).properties(
                height=400
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            
            # --- Data Table ---
            with st.expander("View Raw Data"):
                st.dataframe(df.sort_values(by=['date', 'price'], ascending=[False, True]))
                
else:
    st.info("Please select a Product Family to start.")

# Footer
st.markdown("---")
st.caption("Data sourced from public retailer websites. Prices are for reference only.")
