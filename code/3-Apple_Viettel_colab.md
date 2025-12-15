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
# @markdown Sau đó bấm nút **Play**.

import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page

# --- Cấu hình Input ---
ds_link = "https://viettelstore.vn/dien-thoai/iphone-14-128gb-pid293821.html https://viettelstore.vn/dien-thoai/iphone-16e-pid347205.html https://viettelstore.vn/dien-thoai/iphone-16e-256gb-pid347207.html , https://viettelstore.vn/dien-thoai/iphone-13-128gb-pid288660.html  , " #@param {type:"string"}

# ==============================================================================
# XỬ LÝ DỮ LIỆU
# ==============================================================================

# Tách link từ input form
raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
vt_urls = [link.strip() for link in raw_links if link.strip()]

if not vt_urls:
    print("⚠️ LƯU Ý: Bạn chưa nhập link nào cả. Hãy dán link vào ô 'ds_link' ở trên.")
else:
    print(f"📋 Đã nhận {len(vt_urls)} link cần xử lý.")

# --- Cấu hình Crawler ---
MAX_CONCURRENT_TABS = 3
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Các thành phần web ---
PRODUCT_NAME_SELECTOR = "h1.name-product"
PRICE_MAIN_SELECTOR = ".price-product .new-price"
PRICE_SUB_SELECTOR = ".price-product .old-price"
PROMO_SELECTOR = ".box-promotion ol li"
COLOR_OPTIONS_SELECTOR = "ul.option-color-product li"
STOCK_INDICATOR_SELECTOR = "#btn-buy-now"
PAYMENT_PROMO_SELECTOR = ".payment-promo .description"

def setup_csv(date_str):
    # Tạo file kết quả csv
    file_path = f"viettel-{date_str}.csv"
    
    # Tạo thư mục chứa ảnh
    img_dir = 'img_viettel'
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
            print(f"🔄 Đang xử lý: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # Xử lý Cookie Challenge nếu có
            content = await page.content()
            if "document.cookie" in content and "D1N" in content:
                print("⚠️ Phát hiện chặn bảo mật, đang đợi tải lại...")
                await page.wait_for_timeout(5000)
            
            # Duyệt qua các màu
            color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count > 0:
                # print(f"Tìm thấy {count} lựa chọn màu.")
                for i in range(count):
                    color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
                    btn = color_btns.nth(i)
                    
                    if await btn.is_visible():
                        color_name = await btn.inner_text()
                        if not color_name:
                            label = btn.locator("label")
                            if await label.count() > 0:
                                color_name = await label.get_attribute("title")
                        
                        is_disabled = False
                        click_target = btn.locator("label")
                        if await click_target.count() > 0:
                            if await click_target.get_attribute("disabled"):
                                is_disabled = True
                            style = await click_target.get_attribute("style")
                            if style and "pointer-events: none" in style:
                                is_disabled = True
                            class_attr = await click_target.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                is_disabled = True
                        else:
                            if await btn.get_attribute("disabled"):
                                is_disabled = True
                            class_attr = await btn.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                is_disabled = True

                        # print(f"Click vào màu [{i}]: {color_name} (Hết hàng: {is_disabled})", flush=True)
                        
                        await page.evaluate("document.getElementById('overlay3') && document.getElementById('overlay3').remove()")
                        
                        if await click_target.count() > 0:
                             await click_target.click(force=True)
                        else:
                             await btn.click(force=True)
                             
                        await page.wait_for_timeout(2000)
                        await scrape_product_data(page, url, csv_path, color_name, is_disabled)
            else:
                print("ℹ️ Không tìm thấy lựa chọn màu. Lấy dữ liệu trang hiện tại.")
                await scrape_product_data(page, url, csv_path, "Unknown", False)

        except Exception as e:
            print(f"❌ Lỗi khi xử lý {url}: {e}")
        finally:
            await page.close()

async def scrape_product_data(page, url, csv_path, color_name, is_disabled_option):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
         product_name = await page.title()

    ton_kho = "No"
    if is_disabled_option:
        ton_kho = "No"
    else:
        try:
            content = await page.content()
            if "MUA NGAY" in content:
                ton_kho = "Yes"
        except:
            pass

    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    if not gia_khuyen_mai_raw:
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
    
    def clean_price(p):
        if not p: return 0
        return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    promos = []
    promo_elements = page.locator(PROMO_SELECTOR)
    count = await promo_elements.count()
    for i in range(count):
        text = await promo_elements.nth(i).inner_text()
        if text.strip():
            cleaned_text = re.sub(r'\n+', '\n', text.strip())
            promos.append(cleaned_text)
    khuyen_mai = "\n".join(promos)

    payment_promos = []
    payment_elements = page.locator(PAYMENT_PROMO_SELECTOR)
    p_count = await payment_elements.count()
    for i in range(p_count):
        text = await payment_elements.nth(i).text_content()
        if text and text.strip():
            cleaned_text = re.sub(r'\n+', '\n', text.strip())
            payment_promos.append(cleaned_text)
    thanh_toan = "\n".join(payment_promos)

    screenshot_name = ""
    try:
        img_dir = 'img_viettel'
        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        safe_color = re.sub(r'[^\w\-\.]', '_', str(color_name)).strip('. ')
        timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_product_name}_{safe_color}_{timestamp}.png"
        full_path = os.path.join(img_dir, filename)
        
        await page.screenshot(path=full_path, full_page=True)
        screenshot_name = filename
    except Exception as e:
        print(f"⚠️ Chụp ảnh màn hình thất bại: {e}")

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
    print(f"✅ Đã lưu: {product_name} | {color_name} | {gia_khuyen_mai}")

async def main():
    if not vt_urls:
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
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in vt_urls]
        await asyncio.gather(*tasks)
        
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_viettel")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_viettel.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

# Chạy chương trình
if vt_urls:
    await main()
