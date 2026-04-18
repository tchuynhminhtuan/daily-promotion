import asyncio
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import Page
from pathlib import Path

# Cấu hình hệ thống
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# --- CẤU HÌNH SCREENSHOT (ON/OFF) ---
# True = Bật chụp ảnh | False = Tắt chụp ảnh
ENABLE_SCREENSHOT = True  
# Vị trí khu vực cần chụp ảnh
SCREENSHOT_SELECTOR = "//div[@class='box_main']/div[@class='box_right']"
# ------------------------------------

# Selectors
PRODUCT_NAME_SELECTORS = [".product-name h1", "h1", ".product-name", "title", "[property='og:title']"]
PROMO_SELECTOR = ".promotions, .block__promo"
PRICE_MAIN_SELECTORS = [".box-price-present", ".bs_price strong", ".price-present", ".giamsoc-ol-price", ".center b", ".prods-price li span", ".box-price", "[itemprop='price']", ".price"]
PRICE_SUB_SELECTORS = [".box-price-old", ".bs_price em", ".price-old", ".old-price"]

class MWScraper(BaseScraper):
    def get_filename_prefix(self):
        return "2-mw"

    def get_fieldnames(self):
        fields = ["Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", "Date", "Khuyen_Mai", "Thanh_Toan", "Link"]
        if os.environ.get("SCRAPE_SPECS") == "True":
             fields.append("Tech_Specs")
        fields.append("screenshot_name")
        return fields

    def clean_text_data(self, text):
        """Hàm xử lý khoảng trắng dư thừa đã tối ưu"""
        if not text: return ""
        # Thay thế các ký tự trắng đặc biệt (\xa0...) bằng dấu cách thường
        text = re.sub(r'[\xa0\t\r\f\v]', ' ', str(text))
        # Thu gọn khoảng trắng dư thừa (2 dấu cách trở lên thành 1)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    async def remove_overlays(self, page):
        try:
            await page.evaluate("""() => {
                document.querySelectorAll('.popup-modal, .bg-black, .loading-cover, .loading').forEach(e => e.remove());
            }""")
        except: pass

    async def get_product_name(self, page, url):
        try:
            await page.wait_for_timeout(1000)
            await page.wait_for_selector("h1", timeout=3000)
        except: pass
        name = await self.get_element_text_with_fallbacks(page, PRODUCT_NAME_SELECTORS)
        return name.strip() if name else "Error getting name"

    async def handle_screenshot(self, page, product_name, color):
        """Hàm xử lý chụp ảnh màn hình theo vùng và lưu vào thư mục chỉ định"""
        if not ENABLE_SCREENSHOT:
            return "Disabled"
        
        try:
            # Tạo đường dẫn thư mục: self.output_dir tự động trỏ đến thư mục ngày hiện tại (VD: data/raw/2026-04-17)
            # Giúp thư mục img_mw luôn đồng cấp với file CSV output.
            img_path = os.path.join(self.output_dir, "img_mw")
            os.makedirs(img_path, exist_ok=True)

            # Làm sạch tên file để tránh các ký tự không được hệ điều hành cho phép
            safe_name = re.sub(r'[\\/*?:"<>|]', "", f"{product_name}_{color}")
            filename = f"{safe_name}.png"
            full_path = os.path.join(img_path, filename)

            # Chụp vùng cụ thể
            element = page.locator(SCREENSHOT_SELECTOR).first
            if await element.count() > 0:
                await element.screenshot(path=full_path)
                return filename
            else:
                # Nếu không tìm thấy element đó (ví dụ web đổi giao diện), chụp full page làm backup
                await page.screenshot(path=full_path, full_page=True)
                return f"FULL_{filename}"
                
        except Exception as e:
            print(f"Screenshot Error: {e}")
            return "Error"

    async def scrape_product_data(self, page, url, forced_color=None):
        product_name = await self.get_product_name(page, url)
        product_name = product_name.replace("Điện thoại ", "").replace("Laptop ", "").replace("Máy tính bảng ", "").strip()

        color = forced_color if forced_color else "Default"
        data = {
            "Product_Name": product_name,
            "Color": color,
            "Ton_Kho": "No",
            "Gia_Niem_Yet": 0,
            "Gia_Khuyen_Mai": 0,
            "Date": self.date_str,
            "Khuyen_Mai": "",
            "Thanh_Toan": "",
            "Link": url,
            "screenshot_name": "Skipped"
        }

        # Price Logic
        try:
            shock_price = await self.get_element_text_with_fallbacks(page, PRICE_MAIN_SELECTORS)
            data["Gia_Khuyen_Mai"] = self.extract_price(shock_price)
            old_price = await self.get_element_text_with_fallbacks(page, PRICE_SUB_SELECTORS)
            data["Gia_Niem_Yet"] = self.extract_price(old_price)
            if data["Gia_Khuyen_Mai"] == 0: data["Gia_Khuyen_Mai"] = data["Gia_Niem_Yet"]
            
            # Status Logic
            buy_btn_count = await page.locator("a, button, div").filter(has_text="Mua ngay").count()
            data["Ton_Kho"] = "Yes" if (data["Gia_Khuyen_Mai"] != 0 and buy_btn_count > 0) else "No"
        except: pass

        # Promotions (Cleaned)
        try:
            promo_container = page.locator(PROMO_SELECTOR)
            if await promo_container.count() > 0:
                texts = await promo_container.locator("li, .item, .promo-item").all_text_contents()
                cleaned_promos = [self.clean_text_data(t) for t in texts if t.strip()]
                data["Khuyen_Mai"] = " | ".join(cleaned_promos) if cleaned_promos else self.clean_text_data(await promo_container.text_content())
        except: pass

        # Payment Promo (Cleaned & Updated Selector)
        try:
            tt_selector = "//div[contains(@class, 'campaign') and contains(@class, 'dt')]"
            payment_container = page.locator(tt_selector)
            if await payment_container.count() > 0:
                texts = await payment_container.locator("li, .item").all_text_contents()
                cleaned_payments = [self.clean_text_data(t) for t in texts if t.strip()]
                data["Thanh_Toan"] = " | ".join(cleaned_payments) if cleaned_payments else self.clean_text_data(await payment_container.text_content())
        except: pass

        # --- CHỤP ẢNH MÀN HÌNH ---
        # Hàm này được gọi cho TẤT CẢ sản phẩm (không còn bị bọc trong if data["Ton_Kho"] == "No" nữa)
        data['screenshot_name'] = await self.handle_screenshot(page, product_name, color)
        # -------------------------

        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color} | Price: {data['Gia_Khuyen_Mai']} | Img: {data['screenshot_name']}")

    async def process_color_options(self, page, url):
        try:
            robust_sel = ".box03.color .item, .group-box03 .item, .scrolling_inner .item, .box03__item.item"
            color_btns = page.locator(robust_sel)
            count = await color_btns.count()
            if count == 0:
                await self.scrape_product_data(page, url, forced_color="Default")
                return
            for i in range(count):
                await self.remove_overlays(page)
                btn = page.locator(robust_sel).nth(i)
                color_name = (await btn.text_content()).strip()
                if re.match(r'^\d+\s*(GB|TB)$', color_name, re.IGNORECASE): continue
                is_active = await btn.get_attribute("class")
                if "act" not in is_active and "check" not in is_active:
                    try: await btn.click(force=True, timeout=2000); await page.wait_for_timeout(1000)
                    except: pass
                await self.scrape_product_data(page, url, forced_color=color_name)
        except: await self.scrape_product_data(page, url)

    async def process_storage_options(self, page, url):
        containers = page.locator(".box03, .group.desk, .group-box03")
        count = await containers.count()
        found_storage = False
        for i in range(count):
            cls = await containers.nth(i).get_attribute("class")
            if "color" in cls: continue
            btns = containers.nth(i).locator("a.item, div.item")
            if await btns.count() > 1:
                found_storage = True
                for j in range(await btns.count()):
                    await self.remove_overlays(page)
                    btn = page.locator(".box03, .group.desk, .group-box03").nth(i).locator("a.item, div.item").nth(j)
                    current_url = page.url
                    try:
                        await btn.click(force=True)
                        await page.wait_for_timeout(2000)
                        if page.url != current_url: await self.remove_overlays(page)
                        await self.process_color_options(page, url)
                    except: pass
                return
        if not found_storage: await self.process_color_options(page, url)

    async def scrape(self, page, url):
        await self.remove_overlays(page)
        await self.process_storage_options(page, url)

async def main():
    urls = total_links['mw_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url: urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True": urls = urls[:2]

    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 3))
    scraper = MWScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())