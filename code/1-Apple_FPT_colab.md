# @title 1. Cài đặt môi trường (Chạy 1 lần đầu)
# @markdown Bấm nút **Play** (hình tam giác) bên trái để cài đặt.
# @markdown *Chờ khoảng 1-2 phút cho đến khi hiện thông báo "Cài đặt hoàn tất!".*

!pip install playwright
!playwright install chromium
!playwright install-deps
from IPython.display import clear_output
clear_output()
print("✅ Cài đặt hoàn tất! Bạn có thể chuyển sang Bước 2.")


# @title 2. Nhập link và Chạy Tool
# @markdown Dán danh sách link sản phẩm vào ô bên dưới (mỗi link cách nhau bằng dấu phẩy hoặc xuống dòng).
# @markdown Sau đó bấm nút **Play** (hình tam giác).

import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
import pandas as pd
from playwright.async_api import async_playwright, Page

# --- Cấu hình Input ---
ds_link = "https://fptshop.com.vn/dien-thoai/iphone-15-pro-max, https://fptshop.com.vn/dien-thoai/iphone-15" #@param {type:"string"}

# ==============================================================================
# XỬ LÝ DỮ LIỆU
# ==============================================================================

# Tách link từ input form
raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
fpt_urls = [link.strip() for link in raw_links if link.strip()]

if not fpt_urls:
    print("⚠️ LƯU Ý: Bạn chưa nhập link nào cả. Hãy dán link vào ô 'ds_link' ở trên.")
else:
    print(f"📋 Đã nhận {len(fpt_urls)} link cần xử lý.")

# --- Cấu hình Crawler ---
MAX_CONCURRENT_TABS = 3
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Cấu hình VNPAY ---
oc_vnpay_dict = {
    'HH': {0: 'HH', 1: 'HH', 2: 'HH'}, 'Range_Low_HH': {0: 3000000, 1: 20000000, 2: 0},
    'Range_High_HH': {0: 20000000, 1: 200000000, 2: 0}, 'VNPay_Amount_HH': {0: 150000, 1: 150000, 2: 0},
    'Percentage_HH': {0: '1%', 1: '1%', 2: '0'}, 'Date_HH': {0: '2023-8-31', 1: '2023-8-31', 2: '0'},
    'CPS': {0: 'CPS', 1: 'CPS', 2: '0'}, 'Range_Low_CPS': {0: 5000000, 1: 10000000, 2: 17000000},
    'Range_High_CPS': {0: 10000000, 1: 16999999, 2: 200000000},
    'VNPay_Amount_CPS': {0: 100000, 1: 200000, 2: 300000},
    'Date_CPS': {0: '2023-3-31', 1: '2023-3-31', 2: '2023-3-31'}, 'DDV': {0: 'DDV', 1: '0', 2: '0'},
    'VNPay_Percent_DDV': {0: '0,03', 1: '0', 2: '0'}, 'VNPay_Amount_DDV': {0: 300000, 1: 0, 2: 0},
    'Date_DDV': {0: '2022-07-30', 1: '0', 2: '0'}, 'FPT': {0: 'FPT', 1: 'FPT', 2: 'FPT'},
    'Range_Low_FPT': {0: 5000000, 1: 10000000, 2: 30000000},
    'Range_High_FPT': {0: 10000000, 1: 30000000, 2: 200000000},
    'VNPay_Amount_FPT': {0: 50000, 1: 100000, 2: 300000},
    'Date_FPT': {0: '2024-8-31', 1: '2024-8-31', 2: '2024-8-31'}, 'MW': {0: 'MW', 1: 'MW', 2: 'MW'},
    'Range_Low_MW': {0: 4000000, 1: 9000000, 2: 17000000},
    'Range_High_MW': {0: 9000000, 1: 17000000, 2: 200000000},
    'VNPay_Amount_MW': {0: 50000, 1: 100000, 2: 200000},
    'Date_MW': {0: '2024-8-31', 1: '2024-8-31', 2: '2024-8-31'}
}

# --- Selectors ---
PRODUCT_NAME_SELECTOR = "//h1[contains(@class, 'text-textOnWhitePrimary')]"
PRICE_MAIN_SELECTOR = "//span[contains(@class, 'text-black-opacity-100 h4-bold')]"
PRICE_SUB_SELECTOR = "//span[contains(@class, 'text-neutral-gray-5 line-through')]"
PROMO_SELECTOR = "//div[contains(@class, 'mt-2 flex flex-col gap-2')]"
THANH_TOAN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[2]"
THANH_TOAN_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[2]/div/button"
OTHER_PROMO_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]"
OTHER_PROMO_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]/div/button"
COLOR_SELECTOR_INDICATOR = "//span[contains(text(), 'Màu')]/following-sibling::div//button[descendant::span[contains(@class, 'Selection_triangle__csu2Y')]]"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"

def setup_csv(date_str):
    # Tạo file kết quả csv
    file_path = f"fpt-{date_str}.csv"
    
    # Tạo thư mục chứa ảnh
    img_dir = 'img_fpt'
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writerow(data)

def vnpay_fpt(km_FPT, thanh_toan, now_utc, local_tz):
    oc_vnpay_df = pd.DataFrame.from_dict(oc_vnpay_dict)
    current_date = now_utc.astimezone(local_tz).now().date()
    
    try:
        date_fpt = datetime.strptime(oc_vnpay_df.iloc[0].Date_FPT, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return km_FPT

    try:
        if isinstance(km_FPT, str):
            km_FPT_int = int(re.sub(r"[₫,\.đ]", "", km_FPT))
        else:
            km_FPT_int = int(km_FPT)
    except ValueError:
        return km_FPT

    if current_date <= date_fpt:
        try:
            for _, row in oc_vnpay_df.iterrows():
                low_range = int(row.Range_Low_FPT)
                high_range = int(row.Range_High_FPT)
                if low_range <= km_FPT_int < high_range:
                    max_fpt = int(row.VNPay_Amount_FPT)
                    return km_FPT_int - max_fpt
            return km_FPT_int
        except ValueError:
            return km_FPT_int
    else:
        try:
            if "VNPAY-QR" in thanh_toan:
                max_fpt = 0
                percent_fpt = 100
                for line in thanh_toan.split("\n\n"):
                    if "VNPAY-QR" in line and "đ" in line:
                        try:
                            percent_fpt = int(line.split("%")[0][-2:])
                        except ValueError:
                            percent_fpt = 100

                        try:
                            max_fpt = int(line.split("đ")[0].split()[-1].replace(".", ""))
                        except ValueError:
                            pass

                discounted_price = km_FPT_int * ((100 - percent_fpt) / 100)
                reduced_price = km_FPT_int - max_fpt
                return min(discounted_price, reduced_price)
            else:
                return km_FPT_int
        except (ValueError, AttributeError):
            return km_FPT_int

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
        # Check if button exists and is visible
        btn = page.locator(button_selector).first
        if await btn.count() > 0 and await btn.is_visible():
            try:
                await btn.click()
                await page.wait_for_timeout(1000) # Wait for expansion
            except Exception as e:
                pass
        
        # Get text from container
        return await get_text_safe(page, container_selector)
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
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: 'granted' }) :
                    originalQuery(parameters)
            );
        """)

        try:
            print(f"🔄 Đang xử lý: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # Helper to wait for overlay
            async def wait_for_overlay(page):
                try:
                    overlay = page.locator(".bg-black-opacity-70")
                    if await overlay.count() > 0 and await overlay.is_visible():
                        # print("Waiting for overlay to disappear...")
                        await overlay.wait_for(state="hidden", timeout=10000)
                except Exception as e:
                    pass

            async def handle_popup(page):
                try:
                    de_sau_btn = page.locator("button").filter(has_text="Để sau")
                    if await de_sau_btn.count() > 0 and await de_sau_btn.is_visible():
                        # print("Found 'Để sau' popup, clicking...")
                        await de_sau_btn.click()
                        await page.wait_for_timeout(3000)
                except Exception as e:
                    pass

            # Container for storage options
            storage_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]"
            
            # Check for links (<a> tags)
            storage_links = page.locator(f"{storage_container_xpath}//a")
            link_count = await storage_links.count()

            await handle_popup(page)

            if link_count > 0:
                print(f"Tìm thấy {link_count} phiên bản bộ nhớ (links).")
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
                    
                    # print(f"Navigating to: {link}")
                    try:
                        await page.goto(link, timeout=60000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)
                        await handle_popup(page)
                        await scrape_product_data(page, link, csv_path)
                    except Exception as e:
                        print(f"Lỗi khi xử lý link con {link}: {e}")

            else:
                # Fallback to Buttons
                storage_btns_xpath = f"{storage_container_xpath}/div//button"
                storage_btns = page.locator(storage_btns_xpath)
                count = await storage_btns.count()
                
                if count == 0:
                    # print("No storage buttons found either. Scraping current page.")
                    await handle_popup(page)
                    await scrape_product_data(page, url, csv_path)
                else:
                    print(f"Tìm thấy {count} phiên bản bộ nhớ (buttons).")
                    for i in range(count):
                        storage_btns = page.locator(storage_btns_xpath)
                        btn = storage_btns.nth(i)
                        
                        await wait_for_overlay(page)
                        await handle_popup(page)
                        
                        if await btn.is_visible():
                            txt = await btn.text_content()
                            # print(f"Clicking Storage [{i}]: {txt.strip()}", flush=True)
                            await btn.evaluate("node => node.click()")
                            await page.wait_for_timeout(2000)
                            await handle_popup(page)
                            await scrape_product_data(page, url, csv_path)

        except Exception as e:
            print(f"❌ Lỗi khi xử lý {url}: {e}")
        finally:
            await page.close()

async def scrape_product_data(page, url, csv_path):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
        try:
             product_name = await page.locator(".st-name").text_content()
        except:
             product_name = f"Error getting name"
    
    product_name = product_name.strip().replace("Mini", "mini").replace("Wi-Fi", "WiFi")
    for item in ["Tai nghe ", "Thiết bị định vị thông minh ", "Bộ chuyển đổi "]:
        product_name = product_name.replace(item, "")

    ton_kho = "No"
    try:
        buy_btn_text = await get_text_safe(page, BUY_BUTTON_SELECTOR)
        if "mua" in buy_btn_text.lower():
            ton_kho = "Yes"
    except:
        pass

    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    gia_niem_yet_raw = await get_text_safe(page, PRICE_SUB_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    def clean_price(p):
        if not p: return 0
        return p.replace("đ", "").replace("₫", "").replace(".", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    color = "Unknown"
    try:
        active_color_btn = page.locator(COLOR_SELECTOR_INDICATOR).first
        if await active_color_btn.count() > 0:
             color = await active_color_btn.text_content()
    except Exception as e:
        pass
    color = color.strip()

    khuyen_mai = await get_text_safe(page, PROMO_SELECTOR)
    khuyen_mai = khuyen_mai.replace("Xem chi tiết", "\n").strip()

    other_promo = await click_and_get_text(page, OTHER_PROMO_SELECTOR, OTHER_PROMO_BTN_SELECTOR)
    other_promo = other_promo.replace("Xem chi tiết", "\n").strip()

    # Screenshot
    screenshot_name = ""
    try:
        img_dir = 'img_fpt'
        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_product_name}_{timestamp}.png"
        full_path = os.path.join(img_dir, filename)
        
        await page.screenshot(path=full_path, full_page=True)
        screenshot_name = filename
    except Exception as e:
        print(f"⚠️ Chụp ảnh màn hình thất bại: {e}")
    
    thanh_toan = await click_and_get_text(page, THANH_TOAN_SELECTOR, THANH_TOAN_BTN_SELECTOR)
    thanh_toan = thanh_toan.replace("Xem chi tiết", "\n").strip()

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
    
    write_to_csv(csv_path, data)
    print(f"✅ Đã lưu: {product_name} | {color} | {gia_khuyen_mai}")

async def main():
    if not fpt_urls:
        return

    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(date_str)
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in fpt_urls]
        await asyncio.gather(*tasks)
        
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_fpt")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_fpt.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

# Chạy chương trình
if fpt_urls:
    await main()
