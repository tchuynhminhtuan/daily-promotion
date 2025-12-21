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
MAX_CONCURRENT_TABS = 4 # Variable 1: Increase concurrency (Default: 4 -> 8)

# Optimization Flags
# Optimization Flags
USE_SMART_WAIT = True       # Variable 2: Use smart logic to wait for elements instead of hard sleep
SCREENSHOT_STRATEGY = "FIRST_ONLY" # Variable 3: Options: "ALL", "FIRST_ONLY", "NONE"

# Default: Take screenshots = False, Block Images = True
# For GitHub Actions/Proxies: These defaults are now optimized for speed/cost.
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"

HEADLESS = True  # Set to False for debugging
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
# We still need a way to identify the active color for the CSV, but we can rely on the click.
# The previous COLOR_SELECTOR_INDICATOR is still useful for verification or fallback.
COLOR_SELECTOR_INDICATOR = "//span[contains(text(), 'Màu')]/following-sibling::div//button[descendant::span[contains(@class, 'Selection_triangle__csu2Y')]]"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"
NOTI_SELECTOR = ".st-stt__noti"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"1-fpt-{date_str}.csv")
    
    # Create img_fpt directory
    img_dir = os.path.join(output_dir, 'img_fpt')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # Remove file if it exists to avoid corruption/appending to bad data
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            # , "+VNPAY"
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                #  "+VNPAY",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writerow(data)



async def get_text_safe(page, selector, timeout=2000):
    try:
        if await page.locator(selector).count() > 0:
             # Wait for visibility to ensure text is rendered
            if await page.locator(selector).first.is_visible(timeout=timeout):
                return await page.locator(selector).first.inner_text()
        return ""
    except Exception:
        return ""

async def click_and_get_text(page, container_selector, button_selector):
    try:
        # Check if button exists and is visible
        btn = page.locator(button_selector).first
        if await btn.count() > 0 and await btn.is_visible():
            try:
                print(f"Clicking button: {button_selector}")
                await btn.click()
                if not USE_SMART_WAIT:
                    await page.wait_for_timeout(1000) # Wait for expansion
                else:
                     # Smart wait: wait for network idle or a short buffer
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=2000)
                    except: pass
            except Exception as e:
                print(f"Error clicking button {button_selector}: {e}")
        
        # Get text from container
        return await get_text_safe(page, container_selector)
    except Exception:
        return ""

async def wait_for_overlay(page):
    try:
        # Wait for the specific overlay class seen in debug logs
        # The class might be dynamic, but 'bg-black-opacity-70' seems stable for a modal backdrop
        overlay = page.locator(".bg-black-opacity-70")
        if await overlay.count() > 0 and await overlay.is_visible():
            print("Waiting for overlay to disappear...")
            await overlay.wait_for(state="hidden", timeout=10000)
    except Exception as e:
        print(f"Overlay wait warning: {e}")

async def handle_popup(page):
    try:
        # Check for "Để sau" button using a more robust locator
        # Use filter(has_text=...) to match text even if nested
        de_sau_btn = page.locator("button").filter(has_text="Để sau")
        if await de_sau_btn.count() > 0 and await de_sau_btn.is_visible():
            print("Found 'Để sau' popup, clicking...")
            await de_sau_btn.click()
            await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Popup handler warning: {e}")

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        
        # Optimize: Block images to save bandwidth/speed if requested
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())
        
        # Anti-detection script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            if not USE_SMART_WAIT:
                await page.wait_for_timeout(5000) # Wait for dynamic content
            else:
                 # Smart wait for essential elements
                try:
                    await page.wait_for_selector(PRODUCT_NAME_SELECTOR, timeout=5000)
                except:
                    pass
            await handle_popup(page)

            await process_storage_options(page, url, csv_path, csv_lock)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def process_storage_options(page, url, csv_path, csv_lock):
    # Container 1: Usually Storage
    storage_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]"
    
    # Check for links (<a> tags) in Container 1
    storage_links = page.locator(f"{storage_container_xpath}//a")
    link_count = await storage_links.count()

    if link_count > 0:
        print(f"Found {link_count} storage links. Iterating via URL...")
        hrefs = []
        for i in range(link_count):
            href = await storage_links.nth(i).get_attribute("href")
            if href:
                if not href.startswith("http"):
                    href = "https://fptshop.com.vn" + href
                hrefs.append(href)
        
        # Iterate unique URLs
        seen_urls = set()
        for link in hrefs:
            if link in seen_urls: continue
            seen_urls.add(link)
            
            print(f"Navigating to: {link}")
            try:
                await page.goto(link, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                await handle_popup(page)
                # After navigating to a specific storage URL, iterate colors
                await process_color_options(page, link, csv_path, csv_lock)
            except Exception as e:
                print(f"Failed to navigate/scrape {link}: {e}")

    else:
        # Check for Buttons in Container 1
        storage_btns_xpath = f"{storage_container_xpath}/div//button"
        storage_btns = page.locator(storage_btns_xpath)
        count = await storage_btns.count()
        
        if count == 0:
            print("No storage buttons found. Checking for colors directly...")
            await process_color_options(page, url, csv_path, csv_lock)
        else:
            print(f"Found {count} storage buttons.")
            for i in range(count):
                # Re-locate
                storage_btns = page.locator(storage_btns_xpath)
                btn = storage_btns.nth(i)
                
                await wait_for_overlay(page)
                await handle_popup(page)
                
                if await btn.is_visible():
                    txt = await btn.text_content()
                    name = txt.strip()
                    print(f"Clicking Storage [{i}]: {name}", flush=True)
                    try:
                        await btn.evaluate("node => node.click()")
                        await page.wait_for_timeout(2000)
                        await handle_popup(page)
                        
                        # Check if name looks like storage
                        is_storage = "GB" in name or "TB" in name
                        potential_color = None
                        if not is_storage:
                            potential_color = name

                        # After clicking Storage, iterate Colors
                        await process_color_options(page, url, csv_path, csv_lock, parent_color=potential_color)
                    except Exception as e:
                        print(f"Error clicking storage {i}: {e}")

async def process_color_options(page, url, csv_path, csv_lock, parent_color=None):
    # Container 2: Usually Colors
    color_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]"
    color_btns_xpath = f"{color_container_xpath}/div//button"
    
    color_btns = page.locator(color_btns_xpath)
    count = await color_btns.count()
    
    if count > 0:
        print(f"Found {count} color buttons.")
        for i in range(count):
            # Re-locate
            color_btns = page.locator(color_btns_xpath)
            btn = color_btns.nth(i)
            
            await wait_for_overlay(page)
            await handle_popup(page)
            
            if await btn.is_visible():
                txt = await btn.text_content()
                color_name = txt.strip()
                print(f"Clicking Color [{i}]: {color_name}", flush=True)
                try:
                    await btn.evaluate("node => node.click()")
                    await page.wait_for_timeout(2000)
                    await handle_popup(page)
                    
                    take_screenshot = True
                    if not TAKE_SCREENSHOT:
                        take_screenshot = False
                    elif SCREENSHOT_STRATEGY == "FIRST_ONLY" and i > 0:
                        take_screenshot = False
                    elif SCREENSHOT_STRATEGY == "NONE":
                        take_screenshot = False

                    await scrape_product_data(page, url, csv_path, csv_lock, forced_color=color_name, do_screenshot=take_screenshot)
                except Exception as e:
                    print(f"Error clicking color {i}: {e}")
    else:
        # No color buttons found in Container 2.
        # Use parent_color if available (e.g. from Container 1)
        await scrape_product_data(page, url, csv_path, csv_lock, forced_color=parent_color)

async def scrape_product_data(page, url, csv_path, csv_lock, forced_color=None, do_screenshot=True):
    # Time setup
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Product Name
    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
        # Fallback or error handling
        try:
             product_name = await page.locator(".st-name").text_content()
        except:
             product_name = f"Error getting name: {url}"
    
    product_name = product_name.strip().replace("Mini", "mini").replace("Wi-Fi", "WiFi")
    for item in ["Tai nghe ", "Thiết bị định vị thông minh ", "Bộ chuyển đổi "]:
        product_name = product_name.replace(item, "")

    # Stock (Ton_Kho)
    ton_kho = "No"
    try:
        buy_btn_text = await get_text_safe(page, BUY_BUTTON_SELECTOR)
        if "mua" in buy_btn_text.lower():
            ton_kho = "Yes"
    except:
        pass

    # Prices
    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    gia_niem_yet_raw = await get_text_safe(page, PRICE_SUB_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    # Clean prices
    def clean_price(p):
        if not p: return 0
        return p.replace("đ", "").replace("₫", "").replace(".", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # Color
    color = "Unknown"
    if forced_color:
        color = forced_color
    else:
        try:
            # Find the active color button
            # Try COLOR_SELECTOR_INDICATOR first
            active_color_btn = page.locator(COLOR_SELECTOR_INDICATOR).first
            if await active_color_btn.count() > 0:
                 color = await active_color_btn.text_content()
            else:
                # Fallback: Try to find selected button in Container 2
                color_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]"
                # Assuming 'border-primary' or similar marks selected. FPT uses 'border-primary' for selected.
                # But let's rely on the one with 'Selection_triangle' if possible, or just take the first one?
                # No, if we are here, we probably didn't click anything or extraction failed.
                pass
                
        except Exception as e:
            print(f"Color extraction failed: {e}")
    color = color.strip()

    # Promo & Payment
    khuyen_mai = await get_text_safe(page, PROMO_SELECTOR)
    khuyen_mai = khuyen_mai.replace("Xem chi tiết", "\n").strip()

    other_promo = await click_and_get_text(page, OTHER_PROMO_SELECTOR, OTHER_PROMO_BTN_SELECTOR)
    other_promo = other_promo.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    # Screenshot
    screenshot_name = ""
    if do_screenshot and SCREENSHOT_STRATEGY != "NONE":
        try:
            img_dir = os.path.join(os.path.dirname(csv_path), 'img_fpt')
            safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
            timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{safe_product_name}_{timestamp}.png"
            full_path = os.path.join(img_dir, filename)
            
            await page.set_viewport_size({"width": 1920, "height": 2080})
            await page.screenshot(path=full_path, full_page=True)
            screenshot_name = filename
        except Exception as e:
            print(f"Screenshot failed: {e}")
    else:
        screenshot_name = "Skipped"
    
    thanh_toan = await click_and_get_text(page, THANH_TOAN_SELECTOR, THANH_TOAN_BTN_SELECTOR)
    thanh_toan = thanh_toan.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    # Prepare Data
    data = {
        "Product_Name": product_name,
        "Color": color,
        "Ton_Kho": ton_kho,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        # "+VNPAY": gia_khuyen_mai_vnpay,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Other_promotion": other_promo,
        "Link": url,
        "screenshot_name": screenshot_name
    }
    
    await write_to_csv(csv_path, data, csv_lock)
    print(f"Saved: {product_name} - {color}")

async def main():
    # Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls = total_links['fpt_urls']
    print(f"Found {len(urls)} URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    
    duration = datetime.now() - start_time
    seconds = duration.total_seconds()
    print(f"Total execution time: {int(seconds // 3600)} hours {int((seconds % 3600) // 60)} minutes {int(seconds % 60)} seconds")
