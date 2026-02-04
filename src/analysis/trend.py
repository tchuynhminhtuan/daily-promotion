
import pandas as pd
from datetime import timedelta, datetime
from src.utils.config import CONTENT_DIR, OUTPUT_DIR

def load_historical_data(days=30, verbose=False):
    # Determine date range
    today = datetime.now()
    dates_to_load = []
    for i in range(days + 2): # Load a bit more to be safe
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        # Check if output file exists
        clean_file = OUTPUT_DIR / f"clean_data_{d}.csv"
        if clean_file.exists():
            dates_to_load.append(d)
        
    if verbose: print(f"📊 Loading history from: {len(dates_to_load)} dates found.")
    
    frames = []
    for d in dates_to_load:
        clean_file = OUTPUT_DIR / f"clean_data_{d}.csv"
        try:
            df = pd.read_csv(clean_file)
            df['date'] = d
            frames.append(df)
        except:
            pass
            
    if not frames:
        return pd.DataFrame()
        
    full_df = pd.concat(frames, ignore_index=True)
    full_df['date'] = pd.to_datetime(full_df['date'])
    return full_df

def calculate_changes(df_today, df_history, days_back=7):
    """
    Compare current prices vs prices ~days_back ago.
    """
    if df_history.empty: return pd.DataFrame()
    
    target_date = pd.to_datetime(datetime.now() - timedelta(days=days_back))
    
    # Find closest date in history to target_date
    # Filter history before today
    history_dates = df_history['date'].unique()
    valid_dates = [d for d in history_dates if d <= target_date]
    
    if not valid_dates:
        return pd.DataFrame()
        
    # Get the closest date (max of valid_dates)
    base_date = max(valid_dates)
    
    df_base = df_history[df_history['date'] == base_date].copy()
    
    # Merge Today vs Base
    # Key: product_key + variant_storage + variant_color + retailer ??
    # User report shows "market" trends (across all retailers?) and "retailer" trends.
    # Logic: 
    # Market Trend: Lowest price of product globally? Or avg?
    # Based on report: "Mac mini... -23.1% (date -> date)"
    # It shows [Link] which implies specific retailer item.
    
    # Let's comparison per specific item (Retailer + Product + Variant)
    
    # Columns to join on
    join_cols = ['retailer', 'product_key', 'variant_storage', 'variant_color']
    
    # Prepare Base
    # De-duplicate: take lowest price if duplicates exist for same item?
    df_base_dedup = df_base.sort_values('price').drop_duplicates(subset=join_cols)
    df_today_dedup = df_today.sort_values('price').drop_duplicates(subset=join_cols)
    
    merged = pd.merge(
        df_today_dedup, 
        df_base_dedup, 
        on=join_cols, 
        suffixes=('', '_old'),
        how='inner'
    )
    
    # Calculate Change
    merged['diff_pct'] = ((merged['price'] - merged['price_old']) / merged['price_old']) * 100
    merged['diff_amt'] = merged['price'] - merged['price_old']
    merged['old_date'] = base_date
    
    # Filter for significant drops (e.g. < -5%)
    drops = merged[merged['diff_pct'] <= -5.0].copy()
    
    return drops.sort_values('diff_pct')

def calculate_market_trend(df_today, df_history, days_back=7):
    """
    Compare LOWEST market price for each product/variant.
    """
    if df_history.empty: return pd.DataFrame()
    
    target_date = pd.to_datetime(datetime.now() - timedelta(days=days_back))
    history_dates = df_history['date'].unique()
    valid_dates = [d for d in history_dates if d <= target_date]
    if not valid_dates: return pd.DataFrame()
    base_date = max(valid_dates)
    
    # Global Min Price Aggregation
    group_cols = ['product_key', 'variant_storage', 'variant_color']
    
    # Base
    df_base = df_history[df_history['date'] == base_date]
    min_base = df_base.groupby(group_cols)['price'].min().reset_index()
    
    # Today
    min_today = df_today.groupby(group_cols)['price'].min().reset_index()
    
    merged = pd.merge(min_today, min_base, on=group_cols, suffixes=('', '_old'))
    merged['diff_pct'] = ((merged['price'] - merged['price_old']) / merged['price_old']) * 100
    merged['old_date'] = base_date
    
    # Find the retailer for the current lowest price to show link
    # We need to join back to df_today to get details (Url, Retailer) of the winner
    # Taking the first one that matches the min price
    
    drops = merged[merged['diff_pct'] <= -5.0].copy()
    
    # Enrich with details
    results = []
    for _, row in drops.iterrows():
        # Find item in today's df
        match = df_today[
            (df_today['product_key'] == row['product_key']) &
            (df_today['variant_storage'] == row['variant_storage']) &
            (df_today['variant_color'] == row['variant_color']) &
            (df_today['price'] == row['price'])
        ].iloc[0]
        
        row['retailer'] = match['retailer']
        row['url'] = match['url']
        row['product_name'] = match['product_name']
        results.append(row)
        
    return pd.DataFrame(results)
