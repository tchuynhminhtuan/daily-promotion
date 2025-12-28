import asyncio
import os
import sys
import re
import json
from datetime import datetime
import pytz
from playwright.async_api import Page
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# Constants
# Optimization Flags
USE_SMART_WAIT = True
SCREENSHOT_STRATEGY = "FIRST_ONLY" 

# Selectors
PRODUCT_NAME_SELECTORS = [
    "//h1[contains(@class, 'text-textOnWhitePrimary')]",
    "h1",
    "title",
    "[property='og:title']"
]
PRICE_MAIN_SELECTORS = [
    "//div[@id='price-product']//span[contains(@class, 'h4-bold')]",
    "//span[contains(@class, 'text-black-opacity-100 h4-bold')]",
    "[itemprop='price']",
    ".price",
    ".current-price"
]
PRICE_SUB_SELECTORS = [
    "//div[@id='price-product']//span[contains(@class, 'line-through')]",
    "//span[contains(@class, 'text-neutral-gray-5 line-through')]"
]
PROMO_SELECTOR = "//div[contains(@class, 'mt-2 flex flex-col gap-2')]"
THANH_TOAN_SELECTOR = "//div[@class='flex h-max w-full flex-col gap-3 p-4']"
THANH_TOAN_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[2]/div/button"
OTHER_PROMO_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]"
OTHER_PROMO_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]/div/button"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"

class FPTScraper(BaseScraper):
    def get_filename_prefix(self):
        return "1-fpt"

    def get_fieldnames(self):
        return [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ]

    async def remove_overlays(self, page):
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

    async def handle_popup(self, page):
        await self.remove_overlays(page)

    async def click_and_get_text(self, page, container_selector, button_selector):
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

            return await self.get_text_safe(page, container_selector, timeout=2000)
        except Exception:
            return ""

    async def get_product_name(self, page, url):
        """Robust name retrieval with fallbacks."""
        # 1. Use the new robust selector list
        name = await self.get_element_text_with_fallbacks(page, PRODUCT_NAME_SELECTORS)

        if not name:
            # Last resort fallback: Page Title cleaning
            try:
                title = await page.title()
                if title:
                    return title.split("|")[0].split("- Fptshop")[0].strip()
            except: pass
            return "Error getting name: " + url

        return name

    async def scrape_product_data(self, page, url, forced_color=None, do_screenshot=True):
        # Time setup
        now_utc = datetime.now(pytz.utc)
        date_str = now_utc.astimezone(self.local_tz).strftime('%Y-%m-%d')

        # Get Name
        product_name = await self.get_product_name(page, url)
        
        product_name = product_name.strip().replace("Mini", "mini").replace("Wi-Fi", "WiFi")
        for item in ["Tai nghe ", "Thiết bị định vị thông minh ", "Bộ chuyển đổi "]:
            product_name = product_name.replace(item, "")

        # Stock
        ton_kho = "No"
        try:
            buy_btn_text = await self.get_text_safe(page, BUY_BUTTON_SELECTOR)
            if "mua" in buy_btn_text.lower():
                ton_kho = "Yes"
        except: pass

        # Prices
        gia_khuyen_mai_raw = await self.get_element_text_with_fallbacks(page, PRICE_MAIN_SELECTORS)
        gia_niem_yet_raw = await self.get_element_text_with_fallbacks(page, PRICE_SUB_SELECTORS)

        if not gia_niem_yet_raw and gia_khuyen_mai_raw:
            gia_niem_yet_raw = gia_khuyen_mai_raw

        gia_khuyen_mai = self.extract_price(gia_khuyen_mai_raw)
        gia_niem_yet = self.extract_price(gia_niem_yet_raw)

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

        # Fallback: Extract Color from Name if Unknown (For Single Variant/Hidden Option pages)
        if color == "Unknown" and product_name:
             if " - " in product_name:
                 color = product_name.split(" - ")[-1].strip()
             elif "Nano" in product_name:
                 color = "Nano Texture"
             elif "Apple Watch" in product_name and "Viền" in product_name:
                 match = re.search(r'(Viền.*)', product_name, re.IGNORECASE)
                 if match:
                     color = match.group(1).strip()

        # Promo & Payment
        khuyen_mai = await self.get_text_safe(page, PROMO_SELECTOR)
        khuyen_mai = khuyen_mai.replace("Xem chi tiết", "\n").strip()

        other_promo = await self.click_and_get_text(page, OTHER_PROMO_SELECTOR, OTHER_PROMO_BTN_SELECTOR)
        other_promo = other_promo.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

        thanh_toan = await self.click_and_get_text(page, THANH_TOAN_SELECTOR, THANH_TOAN_BTN_SELECTOR)
        thanh_toan = thanh_toan.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

        # Screenshot
        screenshot_name = ""
        if do_screenshot and SCREENSHOT_STRATEGY != "NONE":
            try:
                safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
                timestamp = datetime.now(self.local_tz).strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{safe_product_name}_{timestamp}.png"
                full_path = os.path.join(self.img_dir, filename)

                await page.screenshot(path=full_path, full_page=True, timeout=5000)
                screenshot_name = filename
            except:
                screenshot_name = "Failed"
        else:
            screenshot_name = "Skipped"

        # Validation: If we scraped a "0" price, it might be loading. Retry once?
        if gia_khuyen_mai == 0:
            await page.wait_for_timeout(1000)
            gia_khuyen_mai = self.extract_price(await self.get_element_text_with_fallbacks(page, PRICE_MAIN_SELECTORS))

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

        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color} | Price: {gia_khuyen_mai}")

    async def process_color_options_optimized(self, page, url, color_idx=-1, container_xpath_arg=None):
        await self.remove_overlays(page)

        current_container_xpath = container_xpath_arg
        if not current_container_xpath:
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
            count = await page.locator(current_container_xpath).count()
            if count > 0:
                color_idx = count - 1
            else:
                await self.scrape_product_data(page, url)
                return

        container_xpath = current_container_xpath
        color_container = page.locator(container_xpath).nth(color_idx)
        color_btns = color_container.locator("button")

        count = await color_btns.count()

        if count > 0:
            for i in range(count):
                await self.remove_overlays(page)
                
                # Re-locate
                container = page.locator(container_xpath).nth(color_idx)
                btn = container.locator("button").nth(i)
                
                if await btn.is_visible():
                    color_name = (await btn.text_content()).strip()
                    try:
                        # FORCE CLICK
                        await btn.click(force=True, timeout=5000)

                        await page.wait_for_timeout(500)

                        take_s = (self.take_screenshot and (SCREENSHOT_STRATEGY != "FIRST_ONLY" or i == 0))
                        await self.scrape_product_data(page, url, forced_color=color_name, do_screenshot=take_s)
                    except Exception as e:
                        print(f"Error clicking color {i}: {e}")
        else:
            await self.scrape_product_data(page, url)

    async def scrape(self, page, url):
        await self.handle_popup(page)

        # Ensure Name is visible before doing anything
        try:
            # Wait for the primary selector
            await page.locator(PRODUCT_NAME_SELECTORS[0]).wait_for(state="visible", timeout=10000)
        except:
            print(f"⚠️ H1 not found within 10s: {url}")

        # 1. Dynamic Option Container Identification
        candidate_xpaths = [
             "//div[contains(@class, 'flex flex-wrap gap-2')]/div",
             "//div[contains(@class, 'pc:flex-row pc:items-center pc:gap-3')]/div/div",
             "//div[contains(@class, 'flex flex-col gap-1.5')]/span/following-sibling::div",
             "//div[contains(@class, 'flex flex-col gap-1.5')]/div/div"
        ]

        all_containers = None
        total_count = 0
        best_xpath = candidate_xpaths[0]

        for xpath in candidate_xpaths:
            ct = page.locator(xpath)
            c = await ct.count()
            if c >= 2 and c <= 5:
                all_containers = ct
                total_count = c
                best_xpath = xpath
                break
            elif c == 1 and total_count == 0:
                 all_containers = ct
                 total_count = c
                 best_xpath = xpath

        if total_count == 0 and candidate_xpaths:
             best_xpath = candidate_xpaths[0]
             all_containers = page.locator(best_xpath)

        # Filter out "Review" containers
        valid_indices = []
        for i in range(total_count):
            txt = await all_containers.nth(i).text_content()
            if "Hài lòng" not in txt and "Thích" not in txt:
                valid_indices.append(i)

        container_count = len(valid_indices)

        # Identify Indices by Label
        storage_idx = 0 if container_count >= 1 else -1
        color_idx = -1 if container_count < 2 else container_count - 1

        detected_storage = -1
        detected_color = -1

        for i in range(container_count):
            real_idx = valid_indices[i]
            try:
                # HEURISTIC 1: Check Button Text
                try:
                    first_btn_text = await all_containers.nth(real_idx).locator("button").first.text_content()
                    first_btn_text = first_btn_text.lower() if first_btn_text else ""
                    if any(x in first_btn_text for x in ["gb", "tb", "ssd"]):
                         if detected_storage == -1: detected_storage = real_idx
                except: pass

                # HEURISTIC 2: Check Label
                try:
                    label_handle = all_containers.nth(real_idx).locator("xpath=preceding-sibling::span").first
                    if await label_handle.count() > 0:
                        label_txt = (await label_handle.text_content()).lower().strip()
                        if any(x in label_txt for x in ["dung lượng", "ssd", "kích thước màn hình", "kích cỡ dây", "cấu hình"]):
                            if detected_storage == -1: detected_storage = real_idx
                        elif "viền" in label_txt or "case" in label_txt:
                            if detected_storage == -1: detected_storage = real_idx
                        elif any(x in label_txt for x in ["màu", "color"]):
                            if detected_color == -1: detected_color = real_idx
                except: pass
            except: pass

        if detected_storage != -1: storage_idx = detected_storage
        if detected_color != -1: color_idx = detected_color

        if color_idx != -1:
            try:
                first_btn = all_containers.nth(color_idx).locator("button").first
                if await first_btn.count() > 0:
                    txt = (await first_btn.text_content() or "").upper()
                    if "GB" in txt or "TB" in txt:
                        color_idx = -1
            except: pass

        if storage_idx == color_idx and storage_idx != -1:
            color_idx = -1
            
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
            storage_idx = valid_indices[0]
            color_idx = valid_indices[-1]

        # --- Storage Loop ---
        if storage_idx >= 0:
            storage_btns = all_containers.nth(storage_idx).locator("button")
            storage_count = await storage_btns.count()
            
            for i in range(storage_count):
                all_containers = page.locator(best_xpath)
                storage_btns = all_containers.nth(storage_idx).locator("button")
                btn = storage_btns.nth(i)

                if await btn.is_visible():
                    try:
                        current_url = page.url
                        await btn.click(force=True, timeout=5000)
                        
                        try:
                            await page.wait_for_timeout(2000)
                            await page.wait_for_load_state("domcontentloaded", timeout=3000)
                        except: pass

                        if page.url != current_url:
                            await self.handle_popup(page)

                        await self.process_color_options_optimized(page, url, color_idx=color_idx, container_xpath_arg=best_xpath)

                    except Exception as e:
                        print(f"Error clicking storage {i}: {e}")
        else:
            await self.process_color_options_optimized(page, url, color_idx=color_idx, container_xpath_arg=best_xpath)

def main():
    urls = total_links['fpt_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        urls = urls[:4]
    
    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 8))
    scraper = FPTScraper(urls=urls, max_concurrent=max_tabs)
    asyncio.run(scraper.run())

if __name__ == "__main__":
    start_time = datetime.now()
    main()
    duration = datetime.now() - start_time
    print(f"Total execution time: {duration}")
