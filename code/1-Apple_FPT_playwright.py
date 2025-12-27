import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
from utils.sites import total_links
import pandas as pd

# Constants
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 8)) # Increased from 4 for local speed

# Optimization Flags
USE_SMART_WAIT = True
SCREENSHOT_STRATEGY = "FIRST_ONLY" 

# Default: Take screenshots = False, Block Images = True
# TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
TAKE_SCREENSHOT = False # User explicitly disabled screenshots
# For local run, we might want to see images, but blocking them is key for speed.
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"

HEADLESS = True  
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors
PRODUCT_NAME_SELECTOR = "//h1[contains(@class, 'text-textOnWhitePrimary')]"
PRICE_MAIN_SELECTOR = "//span[contains(@class, 'text-black-opacity-100 h4-bold')]"
PRICE_SUB_SELECTOR = "//span[contains(@class, 'text-neutral-gray-5 line-through')]"
PROMO_SELECTOR = "//div[contains(@class, 'mt-2 flex flex-col gap-2')]"
THANH_TOAN_SELECTOR = "//div[@class='flex h-max w-full flex-col gap-3 p-4']"
THANH_TOAN_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[2]/div/button"
OTHER_PROMO_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]"
OTHER_PROMO_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]/div/button"

# User defined containers for iteration
STORAGE_OPTIONS_XPATH = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]/div//button"
COLOR_OPTIONS_XPATH = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]/div//button"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"
NOTI_SELECTOR = ".st-stt__noti"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"1-fpt-{date_str}.csv")
    
    # Create img_fpt directory
    img_dir = os.path.join(output_dir, 'img_fpt')
    os.makedirs(img_dir, exist_ok=True)

    # Remove file if it exists to avoid corruption/appending to bad data
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
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

async def click_and_get_text(page, container_selector, button_selector):
    try:
        btn = page.locator(button_selector).first
        if await btn.count() > 0:
            try:
                # Force click to bypass overlays
                await btn.click(force=True, timeout=3000)
                if not USE_SMART_WAIT:
                    await page.wait_for_timeout(1000)
                else:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=2000)
                    except: pass
            except Exception as e:
                pass
        
        return await get_text_safe(page, container_selector)
    except Exception:
        return ""

async def remove_overlays(page):
    """Aggressively remove know overlays/backdrops via JS"""
    try:
        await page.evaluate("""() => {
            document.querySelectorAll('.Backdrop_backdrop__A7yIC').forEach(el => el.remove());
            document.querySelectorAll('.bg-black-opacity-70').forEach(el => el.remove());
            // Also dismiss potential popup buttons if simple
            const deSau = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Để sau'));
            if (deSau) deSau.click();
        }""")
    except: pass

async def handle_popup(page):
    await remove_overlays(page)

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://fptshop.com.vn/",
            },
            ignore_https_errors=True
        )
        
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        try:
            print(f"Processing: {url}")
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"⚠️ Navigation failed: {url} - {e}")
                return

            await handle_popup(page)

            # Ensure Name is visible before doing anything
            try:
                await page.locator(PRODUCT_NAME_SELECTOR).wait_for(state="visible", timeout=10000)
            except:
                print(f"⚠️ H1 not found within 10s: {url}")

            # 1. Dynamic Option Container Identification
            # Strategy: Try multiple selectors. prefer the one that finds > 1 container (Storage + Color).
            candidate_xpaths = [
                "//div[contains(@class, 'flex flex-col gap-1.5')]/span/following-sibling::div",    # New Structure (Containers/Rows)
                "//div[contains(@class, 'flex flex-col gap-1.5')]/div/div",                       # Fallback Generic (Might be buttons? careful)
                "//div[contains(@class, 'flex flex-wrap gap-2')]"                                 # Old Structure
            ]
            
            all_containers = None
            total_count = 0
            best_xpath = candidate_xpaths[1] # Default to old
            
            for xpath in candidate_xpaths:
                ct = page.locator(xpath)
                c = await ct.count()
                if c >= 2:
                    # Ideal case: Found multiple options
                    all_containers = ct
                    total_count = c
                    best_xpath = xpath
                    print(f"  -> Used Selector: {xpath} (Count: {c})")
                    break
                elif c == 1 and total_count == 0:
                     # Keep as fallback if nothing better found
                     all_containers = ct
                     total_count = c
                     best_xpath = xpath
            
            if total_count == 0 and candidate_xpaths:
                 # Default to first if absolutely nothing found (will likely fail downstream but prevents crash here)
                 best_xpath = candidate_xpaths[0]
                 all_containers = page.locator(best_xpath)
            
            if total_count > 0:
                 print(f"  -> Identified {total_count} option containers.")
            
            # Filter out "Review" containers (containing "Hài lòng")
            valid_indices = []
            for i in range(total_count):
                txt = await all_containers.nth(i).text_content()
                if "Hài lòng" not in txt and "Thích" not in txt:
                    valid_indices.append(i)
            
            container_count = len(valid_indices)
            
            # Identify Indices by Label if possible
            # Wrapper is the "Buttons Container". Label is preceding-sibling span.
            # However, for old selector, label logic might differ.
            # We try to guess based on label text.
            
            # Default "Standard" map
            storage_idx = 0 if container_count >= 1 else -1
            color_idx = -1 if container_count < 2 else container_count - 1
            
            # Smarter Mapping
            detected_storage = -1
            detected_color = -1
            
            for i in range(container_count):
                # Use valid_indices to map back to nth(i)
                real_idx = valid_indices[i] 
                
                try:
                    # HEURISTIC 1: Check Button Text
                    try:
                        first_btn_text = await all_containers.nth(real_idx).locator("button").first.text_content()
                        first_btn_text = first_btn_text.lower() if first_btn_text else ""
                        
                        if any(x in first_btn_text for x in ["gb", "tb", "ssd"]):
                             if detected_storage == -1: detected_storage = real_idx
                    except: pass
                    
                    # HEURISTIC 2: Check Label (Robust)
                    try:
                        # Attempt to find preceding sibling 'span' via XPath relative to the container
                        label_handle = await all_containers.nth(real_idx).locator("xpath=preceding-sibling::span").first
                        if await label_handle.count() > 0:
                            label_txt = (await label_handle.text_content()).lower().strip()
                            print(f"    Container {real_idx} Label: {label_txt}")
                            
                            # Storage / Primary Variant (Triggers Navigation)
                            if any(x in label_txt for x in ["dung lượng", "ssd", "kích thước màn hình", "kích cỡ dây", "cấu hình"]):
                                if detected_storage == -1: detected_storage = real_idx
                            elif "viền" in label_txt or "case" in label_txt:
                                # "Màu viền" seems to be primary variant for watches (triggers nav)
                                if detected_storage == -1: detected_storage = real_idx
                            
                            # Color / Secondary Variant
                            elif any(x in label_txt for x in ["màu", "color"]):
                                if detected_color == -1: detected_color = real_idx
                    except:
                        pass
                except Exception as e:
                    print(f"    Error checking container {real_idx}: {e}")
            

            # Apply Logic
            if detected_storage != -1:
                storage_idx = detected_storage
            
            if detected_color != -1:
                color_idx = detected_color
            
            # Conflict resolution: If same index detected for both (rare), prefer Storage logic if it causes navigation
            if storage_idx == color_idx and storage_idx != -1:
                # If we have another container, assign color to it?
                # Assume standard behavior: Primary is Storage loop.
                color_idx = -1 
                
            print(f"  -> Decided Indices: Storage={storage_idx}, Color={color_idx}")

            if container_count == 1 and storage_idx == -1 and color_idx == -1:
                real_idx = valid_indices[0]
                try:
                    first_text = await all_containers.nth(real_idx).locator("button").first.text_content()
                    if "GB" in first_text or "TB" in first_text:
                        storage_idx = real_idx
                        color_idx = -1
                    else:
                        storage_idx = -1
                        color_idx = real_idx
                except:
                     color_idx = real_idx 
            
            elif container_count >= 2 and storage_idx == -1 and color_idx == -1:
                # Standard Fallback: First is Storage, Last is Color
                storage_idx = valid_indices[0]
                color_idx = valid_indices[-1]
            
            # --- Storage Loop ---
            if storage_idx >= 0:
                storage_btns = all_containers.nth(storage_idx).locator("button")
                storage_count = await storage_btns.count()
                
                for i in range(storage_count):
                    # Re-locate container and buttons to avoid stale handles
                    all_containers = page.locator(best_xpath)
                    storage_btns = all_containers.nth(storage_idx).locator("button")
                    btn = storage_btns.nth(i)
                    
                    if await btn.is_visible():
                        name = (await btn.text_content()).strip()
                        try:
                            # FORCE CLICK
                            current_url = page.url
                            await btn.click(force=True, timeout=5000)
                            
                            # Check Navigation
                            try:
                                await page.wait_for_timeout(2000)
                                await page.wait_for_load_state("domcontentloaded", timeout=3000)
                            except: pass
                            
                            if page.url != current_url:
                                print(f"  -> Navigated to: {page.url}")
                                await handle_popup(page)
                                await remove_overlays(page)
                            else:
                                pass

                            # Recurse: Colors (Pass index explicitly)
                            await process_color_options_optimized(page, url, csv_path, csv_lock, color_idx=color_idx, container_xpath_arg=best_xpath)

                        except Exception as e:
                            print(f"Error clicking storage {name}: {e}")
            else:
                # No storage loop, just colors
                await process_color_options_optimized(page, url, csv_path, csv_lock, color_idx=color_idx, container_xpath_arg=best_xpath)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def process_color_options_optimized(page, url, csv_path, csv_lock, color_idx=-1, container_xpath_arg=None):
    await remove_overlays(page)
    
    # Use passed xpath or fallback to detection list
    current_container_xpath = container_xpath_arg
    if not current_container_xpath:
        # Fallback detection logic (copied from main)
        candidate_xpaths = [
            "//div[contains(@class, 'flex flex-col gap-1.5')]/span/following-sibling::div", 
            "//div[contains(@class, 'flex flex-col gap-1.5')]/div/div", 
            "//div[contains(@class, 'flex flex-wrap gap-2')]"
        ]
        current_container_xpath = candidate_xpaths[1]
        for xpath in candidate_xpaths:
            if await page.locator(xpath).count() >= 1:
                current_container_xpath = xpath
                break

    if color_idx == -1:
        # Should not happen with new logic, but fallback to "Last Found"?
        count = await page.locator(current_container_xpath).count()
        if count > 0:
            color_idx = count - 1
        else:
            await scrape_product_data(page, url, csv_path, csv_lock)
            return

    container_xpath = current_container_xpath
    # Note: nth(i) is 0-indexed.
    color_container = page.locator(container_xpath).nth(color_idx)
    color_btns = color_container.locator("button")
    
    count = await color_btns.count()
    
    if count > 0:
        for i in range(count):
            await remove_overlays(page)
            
            # Re-locate
            container = page.locator(container_xpath).nth(color_idx)
            btn = container.locator("button").nth(i)
            
            if await btn.is_visible():
                color_name = (await btn.text_content()).strip()
                try:
                    # FORCE CLICK
                    await btn.click(force=True, timeout=5000)
                    
                    await page.wait_for_timeout(500)
                    
                    take_s = (TAKE_SCREENSHOT and (SCREENSHOT_STRATEGY != "FIRST_ONLY" or i == 0))
                    await scrape_product_data(page, url, csv_path, csv_lock, forced_color=color_name, do_screenshot=take_s)
                except Exception as e:
                    print(f"Error clicking color {i}: {e}")
    else:
        await scrape_product_data(page, url, csv_path, csv_lock)

async def get_product_name(page, url):
    """Robust name retrieval with fallbacks."""
    name = "Error getting name: " + url
    
    # 1. Try Primary Selector
    try:
        if await page.locator(PRODUCT_NAME_SELECTOR).count() > 0:
            name = (await page.locator(PRODUCT_NAME_SELECTOR).first.text_content()).strip()
            if name: return name
    except: pass
    
    # 2. Try Generic H1
    try:
        if await page.locator("h1").count() > 0:
            name = (await page.locator("h1").first.text_content()).strip()
            if name: return name
    except: pass
    
    # 3. Try Page Title (Most robust fallback)
    try:
        title = await page.title()
        # Clean title: "iPhone 15 128GB | Fptshop.com.vn" -> "iPhone 15 128GB"
        if title:
             clean_title = title.split("|")[0].split("- Fptshop")[0].strip()
             return clean_title
    except: pass
    
    return name

async def scrape_product_data(page, url, csv_path, csv_lock, forced_color=None, do_screenshot=True):
    # Time setup
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Get Name using robust function
    product_name = await get_product_name(page, url)
    
    product_name = product_name.strip().replace("Mini", "mini").replace("Wi-Fi", "WiFi")
    for item in ["Tai nghe ", "Thiết bị định vị thông minh ", "Bộ chuyển đổi "]:
        product_name = product_name.replace(item, "")

    # Stock
    ton_kho = "No"
    try:
        buy_btn_text = await get_text_safe(page, BUY_BUTTON_SELECTOR)
        if "mua" in buy_btn_text.lower():
            ton_kho = "Yes"
    except: pass

    # Prices
    # Robust Selector Scoping
    gia_khuyen_mai_raw = await get_text_safe(page, "//div[@id='price-product']//span[contains(@class, 'h4-bold')]")
    gia_niem_yet_raw = await get_text_safe(page, "//div[@id='price-product']//span[contains(@class, 'line-through')]")
    
    # Fallback to old global selector if scoped failed (Optional, but safe)
    if not gia_khuyen_mai_raw:
        gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    def clean_price(p):
        if not p: return 0
        return int(re.sub(r'[^\d]', '', p)) if re.search(r'\d', p) else 0

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # JSON-LD Fallback (High Reliability)
    if gia_khuyen_mai == 0:
        try:
            json_ld = await page.evaluate("""() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const script of scripts) {
                    try {
                        const data = JSON.parse(script.innerText);
                        // Handle single product or graph
                        const product = data['@type'] === 'Product' ? data : 
                                      (data['@graph'] ? data['@graph'].find(g => g['@type'] === 'Product') : null);
                        
                        if (product && product.offers) {
                            const offer = Array.isArray(product.offers) ? product.offers[0] : product.offers;
                             // FPT uses 'price' (number or string)
                            return offer.price || offer.highPrice || offer.lowPrice;
                        }
                    } catch(e){}
                }
                return null;
            }""")
            if json_ld:
                gia_khuyen_mai = int(float(str(json_ld)))
        except: pass

    # Ensure Niem Yet is at least equal to Khuyen Mai
    if gia_niem_yet == 0 and gia_khuyen_mai > 0:
         gia_niem_yet = gia_khuyen_mai

    # Color
    color = forced_color if forced_color else "Unknown"
    
    # Promo & Payment
    khuyen_mai = await get_text_safe(page, PROMO_SELECTOR)
    khuyen_mai = khuyen_mai.replace("Xem chi tiết", "\n").strip()

    other_promo = await click_and_get_text(page, OTHER_PROMO_SELECTOR, OTHER_PROMO_BTN_SELECTOR)
    other_promo = other_promo.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    thanh_toan = await click_and_get_text(page, THANH_TOAN_SELECTOR, THANH_TOAN_BTN_SELECTOR)
    thanh_toan = thanh_toan.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    # Screenshot
    screenshot_name = ""
    if do_screenshot and SCREENSHOT_STRATEGY != "NONE":
        try:
            img_dir = os.path.join(os.path.dirname(csv_path), 'img_fpt')
            safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
            timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{safe_product_name}_{timestamp}.png"
            full_path = os.path.join(img_dir, filename)
            
            # Quick screenshot, don't wait too long
            await page.screenshot(path=full_path, full_page=True, timeout=5000)
            screenshot_name = filename
        except:
            screenshot_name = "Failed"
    else:
        screenshot_name = "Skipped"
    
    # Validation: If we scraped a "0" price, it might be loading. Retry once?
    if gia_khuyen_mai == 0 or gia_khuyen_mai == "0":
        await page.wait_for_timeout(1000)
        # simplistic retry
        gia_khuyen_mai = clean_price(await get_text_safe(page, PRICE_MAIN_SELECTOR))

    # Prepare Data
    data = {
        "Product_Name": product_name,
        "Color": color,
        "Ton_Kho": ton_kho,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Other_promotion": other_promo,
        "Link": url,
        "screenshot_name": screenshot_name
    }
    
    await write_to_csv(csv_path, data, csv_lock)
    print(f"Saved: {product_name} - {color} | Price: {gia_khuyen_mai}")

async def main():
    # Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls = total_links['fpt_urls']
    
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        print(f"⚠️ PROCESSING SPECIFIC URL: {specific_url}")
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        print("⚠️ TEST MODE ENABLED: Processing only 4 URLs")
        urls = urls[:4]
    
    print(f"Found {len(urls)} URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        # Proxy Logic (Optional, for completeness)
        proxy_server = os.environ.get("PROXY_SERVER", "").strip()
        launch_options = {
            "headless": HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080",
                 "--ignore-certificate-errors"
            ],
            "ignore_default_args": ["--enable-automation"]
        }
        
        if proxy_server and os.environ.get("ENABLE_PROXY_FPT", "False").lower() == "true":
            # Just minimal proxy format handling
             if not proxy_server.startswith("http"):
                parts = proxy_server.split(':')
                if len(parts) == 4 and "@" not in proxy_server:
                    ip, port, user, pw = parts
                    proxy_server = f"http://{user}:{pw}@{ip}:{port}"
                else:
                    proxy_server = f"http://{proxy_server}"
             print(f"🌐 Using Proxy (FPT): {proxy_server}")
             launch_options["proxy"] = {"server": proxy_server}
        
        browser = await p.chromium.launch(**launch_options)
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    
    duration = datetime.now() - start_time
    seconds = duration.total_seconds()
    print(f"Total execution time: {int(seconds // 3600)} hours {int((seconds % 3600) // 60)} minutes {int(seconds % 60)} seconds")
