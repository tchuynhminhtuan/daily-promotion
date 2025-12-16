import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
from sites import total_links, oc_vnpay_dict

# Constants
MAX_CONCURRENT_TABS = 8
HEADLESS = True  # Set to False for debugging/PoC
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors for Viettel Store
PRODUCT_NAME_SELECTOR = "h1.name-product"
PRICE_MAIN_SELECTOR = ".price-product .new-price"
PRICE_SUB_SELECTOR = ".price-product .old-price" # Assuming this exists if there's an old price
PROMO_SELECTOR = ".box-promotion ol li" # Updated based on debug HTML
COLOR_OPTIONS_SELECTOR = "ul.option-color-product li"
STOCK_INDICATOR_SELECTOR = "#btn-buy-now" # Or check for "MUA NGAY" text
PAYMENT_PROMO_SELECTOR = ".payment-promo .description" # Updated to target description directly

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"3-viettel-{date_str}.csv")
    
    # Create img_viettel directory
    img_dir = os.path.join(output_dir, 'img_viettel')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writerow(data)

async def get_text_safe(page, selector, timeout=2000):
    try:
        if await page.locator(selector).count() > 0:
            if await page.locator(selector).first.is_visible(timeout=timeout):
                return await page.locator(selector).first.inner_text()
        return ""
    except Exception:
        return ""

async def process_url(semaphore, browser, url, csv_path):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        
        # Anti-detection script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000) # Wait for dynamic content

            # Handle Cookie Challenge if present (D1N)
            # Playwright usually handles cookies automatically, but if there's a JS challenge page:
            content = await page.content()
            if "document.cookie" in content and "D1N" in content:
                print("Detected cookie challenge, waiting for reload...")
                await page.wait_for_timeout(5000) # Give it time to reload
            
            # Color Iteration
            # Locate color buttons
            
            # Save content for debugging selectors
            # content = await page.content()
            # with open("viettel_debug.html", "w", encoding="utf-8") as f:
            #     f.write(content)

            color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count > 0:
                print(f"Found {count} color options.")
                for i in range(count):
                    # Re-locate to avoid stale elements
                    color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
                    btn = color_btns.nth(i)
                    
                    if await btn.is_visible():
                        # Try to get color name from text or title attribute
                        color_name = await btn.inner_text()
                        if not color_name:
                            label = btn.locator("label")
                            if await label.count() > 0:
                                color_name = await label.get_attribute("title")
                        
                        # Check if the option is disabled (out of stock)
                        is_disabled = False
                        click_target = btn.locator("label")
                        if await click_target.count() > 0:
                            # Check attributes on label
                            if await click_target.get_attribute("disabled"):
                                is_disabled = True
                            
                            style = await click_target.get_attribute("style")
                            if style and "pointer-events: none" in style:
                                is_disabled = True
                                
                            class_attr = await click_target.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                is_disabled = True
                        else:
                            # Check attributes on li if label not found
                            if await btn.get_attribute("disabled"):
                                is_disabled = True
                            class_attr = await btn.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                is_disabled = True

                        print(f"Clicking Color [{i}]: {color_name} (Disabled: {is_disabled})", flush=True)
                        
                        # Remove overlay if present
                        await page.evaluate("document.getElementById('overlay3') && document.getElementById('overlay3').remove()")
                        
                        # Click logic
                        if await click_target.count() > 0:
                             await click_target.click(force=True)
                        else:
                             await btn.click(force=True)
                             
                        await page.wait_for_timeout(2000) # Wait for price update
                        
                        # If disabled, we might not have successfully switched, or it's just out of stock.
                        # We pass the disabled status to the scrape function.
                        await scrape_product_data(page, url, csv_path, color_name, is_disabled)
            else:
                print("No color options found. Scraping current page.")
                await scrape_product_data(page, url, csv_path, "Unknown", False)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def scrape_product_data(page, url, csv_path, color_name, is_disabled_option):
    # Time setup
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Product Name
    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
         # Fallback
         product_name = await page.title()

    # Stock (Ton_Kho)
    # Priority: 
    # 1. If color option was explicitly disabled -> No
    # 2. If "MUA NGAY" is present -> Yes
    # 3. Else -> No
    ton_kho = "No"
    
    if is_disabled_option:
        ton_kho = "No"
    else:
        try:
            # Check for "MUA NGAY" button text or class
            content = await page.content()
            if "MUA NGAY" in content:
                ton_kho = "Yes"
        except:
            pass

    # Prices
    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    # If price is empty, try to find it in the input value or other attributes if hidden
    if not gia_khuyen_mai_raw:
         # Try JSON-LD extraction as fallback (Playwright can execute JS)
         try:
             json_ld = await page.evaluate("""() => {
                const script = document.querySelector('script[type="application/ld+json"]');
                return script ? JSON.parse(script.innerText) : null;
             }""")
             if json_ld and "offers" in json_ld:
                 gia_khuyen_mai_raw = str(json_ld["offers"].get("Price", ""))
         except:
             pass

    gia_niem_yet_raw = await get_text_safe(page, PRICE_SUB_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    # Clean prices
    def clean_price(p):
        if not p: return 0
        return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # Promo (Khuyen_Mai)
    # Use inner_text to preserve line breaks, but clean up excessive whitespace
    promos = []
    promo_elements = page.locator(PROMO_SELECTOR)
    count = await promo_elements.count()
    for i in range(count):
        text = await promo_elements.nth(i).inner_text()
        if text.strip():
            # Replace multiple newlines with single newline
            cleaned_text = re.sub(r'\n+', '\n', text.strip())
            promos.append(cleaned_text)
    khuyen_mai = "\n".join(promos)

    # Payment Promo (Thanh_Toan)
    payment_promos = []
    payment_elements = page.locator(PAYMENT_PROMO_SELECTOR)
    p_count = await payment_elements.count()
    for i in range(p_count):
        # Use text_content() because elements might be hidden
        text = await payment_elements.nth(i).text_content()
        if text and text.strip():
            cleaned_text = re.sub(r'\n+', '\n', text.strip())
            payment_promos.append(cleaned_text)
    thanh_toan = "\n".join(payment_promos)

    # Screenshot
    screenshot_name = ""
    try:
        img_dir = os.path.join(os.path.dirname(csv_path), 'img_viettel')
        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        safe_color = re.sub(r'[^\w\-\.]', '_', str(color_name)).strip('. ')
        timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_product_name}_{safe_color}_{timestamp}.png"
        full_path = os.path.join(img_dir, filename)
        
        await page.screenshot(path=full_path, full_page=True)
        screenshot_name = filename
    except Exception as e:
        print(f"Screenshot failed: {e}")

    # Prepare Data
    data = {
        "Product_Name": product_name,
        "Color": color_name,
        "Ton_Kho": ton_kho,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Link": url,
        "screenshot_name": screenshot_name
    }
    
    write_to_csv(csv_path, data)
    print(f"Saved: {product_name} - {color_name} - {gia_khuyen_mai}")

async def main():
    # Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(base_path, date_str)
    
    # For PoC, use the single URL we found
    # urls = ["https://viettelstore.vn/dien-thoai/iphone-17-256gb-pid355077.html"]
    urls = total_links['vt_urls']
    print(f"Processing {len(urls)} URL(s) for PoC.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in urls]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
