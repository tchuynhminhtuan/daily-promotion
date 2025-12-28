import asyncio
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import Page
from utils.sites import total_links
from utils.base_scraper import BaseScraper

class DDVScraper(BaseScraper):
    # Selectors
    PRODUCT_NAME_SELECTORS = ["h1", "title", "[property='og:title']"]
    PRICE_MAIN_SELECTORS = [
        ":is(p, div, span)[class*='text-24'][class*='font-bold']",
        "[itemprop='price']",
        ".price",
        ".current-price"
    ]
    PRICE_SUB_SELECTORS = [
        ".line-through"
    ]

    def get_filename_prefix(self):
        return "5-ddv"

    def get_fieldnames(self):
        return [
            "Product_Name", "Color", "Ton_Kho", "Store_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ]

    async def handle_popup(self, page):
        try:
            close_btns = page.locator("button[aria-label='Close'], .close-popup, .popup-close, .ant-modal-close")
            if await close_btns.count() > 0:
                for i in range(await close_btns.count()):
                    if await close_btns.nth(i).is_visible():
                        await close_btns.nth(i).click()
        except: pass

    async def extract_stock_status(self, page):
        ton_kho = "Yes"
        try:
            oos_text_loc = page.locator("text=SẮP VỀ HÀNG")
            if await oos_text_loc.count() > 0 and await oos_text_loc.first.is_visible():
                return "No"
            
            btn_loc = page.locator("button.ant-btn-primary").first
            if await btn_loc.count() > 0:
                btn_text = await btn_loc.inner_text()
                if "ĐĂNG KÝ" in btn_text.upper() or "THÔNG TIN" in btn_text.upper():
                    return "No"
        except: pass
        return ton_kho

    async def scrape_variant(self, page, url, variant_color="Unknown", screenshot=False):
        # 1. Product Name
        product_name = await self.get_element_text_with_fallbacks(page, self.PRODUCT_NAME_SELECTORS)
        if not product_name: product_name = "Unknown"

        # 2. Prices
        gia_khuyen_mai = 0
        gia_niem_yet = 0

        gkm_str = await self.get_element_text_with_fallbacks(page, self.PRICE_MAIN_SELECTORS)
        gia_khuyen_mai = self.extract_price(gkm_str)

        gny_str = await self.get_element_text_with_fallbacks(page, self.PRICE_SUB_SELECTORS)
        gia_niem_yet = self.extract_price(gny_str)
        
        # JSON-LD Fallback
        if gia_khuyen_mai == 0:
            try:
                json_ld = await page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const script of scripts) {
                        try {
                            const data = JSON.parse(script.innerText);
                            const product = data['@type'] === 'Product' ? data : 
                                          (data['@graph'] ? data['@graph'].find(g => g['@type'] === 'Product') : null);
                            
                            if (product && product.offers) {
                                const offer = Array.isArray(product.offers) ? product.offers[0] : product.offers;
                                return offer.price || offer.highPrice || offer.lowPrice;
                            }
                        } catch(e){}
                    }
                    return null;
                }""")
                if json_ld:
                    gia_khuyen_mai = int(float(str(json_ld)))
            except: pass

        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai

        # 3. Stock
        ton_kho = await self.extract_stock_status(page)

        # 3.1 Store Count
        store_count = "0"
        try:
             count_loc = page.locator("//div[@class='py-2']/p/span")
             if await count_loc.count() > 0:
                 count_text = await count_loc.inner_text()
                 if count_text:
                     store_count = re.sub(r'[^\d]', '', count_text)
        except: pass

        # 4. Promotions
        try:
            view_more_btn = page.locator("//button[contains(@class, 'w-full')]/p[contains(text(),'Xem thêm')] | //button[contains(@class, 'w-full')]/p[contains(text(),'Xem tất cả')]").first
            if await view_more_btn.count() == 0:
                 view_more_btn = page.locator("//button[contains(@class, 'w-full')]/p").first
            
            if await view_more_btn.count() > 0 and await view_more_btn.is_visible():
                await view_more_btn.click(force=True)
                await page.wait_for_timeout(500)
        except: pass

        khuyen_mai = ""
        try:
             km_loc = page.locator("div.border.rounded-lg.overflow-hidden.w-full").first
             if await km_loc.count() > 0:
                 khuyen_mai = await km_loc.inner_text()
                 khuyen_mai = khuyen_mai.strip()
        except: pass

        thanh_toan = "" 
        try:
            tt_loc = page.locator("//div[@class='flex w-full flex-col items-start justify-start bg-white p-2']")
            count = await tt_loc.count()
            tt_texts = []
            for i in range(count):
                if await tt_loc.nth(i).is_visible():
                     text = await tt_loc.nth(i).inner_text()
                     if text:
                         tt_texts.append(text.strip())
            
            if tt_texts:
                thanh_toan = "\n".join(tt_texts)
        except: pass 

        # 5. Screenshot
        screenshot_name = ""
        if screenshot and self.take_screenshot:
            try:
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)[:30]
                safe_color = re.sub(r'[^\w\-\.]', '_', variant_color)[:10]
                fname = f"{safe_name}_{safe_color}_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=os.path.join(self.img_dir, fname), full_page=True)
                screenshot_name = fname
            except: pass
            
        # 6. Save
        data = {
            "Product_Name": product_name,
            "Color": variant_color,
            "Ton_Kho": ton_kho,
            "Store_Count": store_count, 
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": self.date_str,
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Other_promotion": "",
            "Link": url,
            "screenshot_name": screenshot_name
        }
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {variant_color} | Stock: {ton_kho} | Price: {gia_khuyen_mai}")

    async def scrape(self, page, url):
        # We strictly process the URL provided. No recursive loops for variants unless site structure demands it.
        # Original code had recursive storage discovery but it was disabled by default/structure.
        # Here we just process colors on current page.

        await self.handle_popup(page)
        
        candidates = page.locator("div.cursor-pointer.rounded")
        count = await candidates.count()
        
        valid_colors = []
        for i in range(count):
            try:
                el = candidates.nth(i)
                if not await el.is_visible(): continue
                
                classes = await el.get_attribute("class") or ""
                if "border" not in classes: continue

                text = await el.text_content()
                clean_text = text.strip()
                
                if not clean_text: continue
                
                if "GB" in clean_text.upper() or "TB" in clean_text.upper(): continue
                if "MUA" in clean_text.upper() or "ĐĂNG KÝ" in clean_text.upper(): continue
                if "TRẢ GÓP" in clean_text.upper(): continue

                valid_colors.append((clean_text, i))
            except: continue
            
        unique_colors = {}
        for txt, idx in valid_colors:
            if txt not in unique_colors:
                unique_colors[txt] = idx
                
        if not unique_colors:
            await self.scrape_variant(page, url, variant_color="Default")
            return

        for color_text, idx in unique_colors.items():
            try:
                el = page.locator("div.cursor-pointer.rounded").nth(idx)
                
                await el.scroll_into_view_if_needed()
                await el.click(force=True)
                await page.wait_for_timeout(300)
                
                color_name = color_text.split('\n')[0].strip()
                color_name = color_name.replace("Màu", "").strip()

                await self.scrape_variant(page, url, variant_color=color_name, screenshot=True)
                
            except Exception as e:
                print(f"Error processing color {color_text}: {e}")

async def main():
    urls = total_links['ddv_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        urls = urls[:4]
    
    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
    scraper = DDVScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start
    print(f"Total execution time: {duration}")
