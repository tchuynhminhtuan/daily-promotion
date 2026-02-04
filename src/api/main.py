
from fastapi import FastAPI, HTTPException
import sqlite3
import pandas as pd
import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.analysis.predict_price import load_data, get_product_analysis

app = FastAPI(
    title="Daily Promotion API",
    description="API for accessing product price history and AI forecasts",
    version="1.0.0"
)

DB_PATH = "catalog/price_history.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"message": "Welcome to Daily Promotion API. Go to /docs for Swagger UI."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/products")
def list_products(limit: int = 50):
    conn = get_db_connection()
    query = """
    SELECT p.key, p.name, p.brand, COUNT(h.id) as history_count 
    FROM products p 
    JOIN price_history h ON p.id = h.product_id 
    GROUP BY p.key 
    ORDER BY history_count DESC 
    LIMIT ?
    """
    products = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return {"products": [dict(p) for p in products]}

@app.get("/price/{product_key}")
def get_price_forecast(product_key: str):
    """
    Get historic price analysis and buy/wait recommendation for a product.
    """
    try:
        df = load_data(product_key)
        if df is None or df.empty:
             raise HTTPException(status_code=404, detail=f"Product {product_key} not found or no history available")
        
        analysis = get_product_analysis(df, product_key)
        if not analysis:
             raise HTTPException(status_code=404, detail="Insufficient data for analysis")
             
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
