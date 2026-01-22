import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import HtmlResponse
import json
from datetime import datetime
import pytz
import os
import logging

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
TARGET_BRAND = "Apple"
BRAND_CONFIGS = {
    "Apple": {
        "iPhone": {"c": 42, "m": 80},
        "MacBook": {"c": 44, "m": 203},
        "iPad": {"c": 522, "m": 1028},
        "Watch": {"c": 7077, "m": 17188},
    }
}
API_URL = "https://www.thegioididong.com/Category/FilterProductBox"

def get_vietnam_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d')

class AppleDeepSpider(scrapy.Spider):
    name = "apple_deep_spider"
    
    custom_settings = {
        'USER_AGENT': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        'LOG_LEVEL': 'INFO',
        'CONCURRENT_REQUESTS': 10, # Reduced concurrency
        'DOWNLOAD_DELAY': 0.5, # Increased delay to minimize errors
        'FEEDS': {
            f"content/{get_vietnam_time()}/4-scrapy-{TARGET_BRAND.lower()}-{get_vietnam_time()}.csv": {
                'format': 'csv',
                'encoding': 'utf8',
                'overwrite': True,
                'fields': ["Product_ID", "SKU", "Product_Name", "Brand", "Category", 
                           "Color", "Specs", "Variants",
                           "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", 
                           "Discount_Percent", "Installment", "Rating", "Vote_Count",
                           "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Image_URL", 
                           "Label_Online", "Internal_Pro_ID", "Internal_S_Code", 
                           "Internal_Maingroup", "Internal_Subgroup", 
                           "Internal_Type", "Internal_Vehicle", "Internal_OrderType",
                           "screenshot_name"]
            }
        }
    }

    def start_requests(self):
        config = BRAND_CONFIGS.get(TARGET_BRAND)
        if not config:
            logging.error(f"Brand {TARGET_BRAND} not configured.")
            return

        # Explicit headers often needed for AJAX
        headers = {
            "User-Agent": self.custom_settings['USER_AGENT'],
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.thegioididong.com",
            "Referer": "https://www.thegioididong.com"
        }

        for category, params in config.items():

            # Initial Request for Page 0
            payload = {
                "c": str(params['c']),
                "m": str(params['m']),
                "o": "13",
                "pi": "0",
                "IsParentCate": "False",
                "IsShowCompare": "True",
                "prevent": "true"
            }
            yield scrapy.FormRequest(
                url=API_URL,
                formdata=payload,
                headers=headers, # IMPT
                callback=self.parse_list_api,
                meta={
                    'category': category, 
                    'params': params, 
                    'page_idx': 0
                }
            )

    def parse_list_api(self, response):
        try:
            # Explicitly decode JSON
            data = json.loads(response.text)
            # API key might vary or be case sensitive
            html = data.get('listproducts') or data.get('lstProducts') or ''
            
            logging.info(f"API Response Keys: {data.keys()}")
            
            if not html:
                logging.warning(f"Response has no 'listproducts'. Full response: {str(data)[:200]}...")
                
        except Exception as e:
            logging.error(f"Failed to parse API JSON: {e}")
            logging.error(f"Raw Text Preview: {response.text[:200]}")
            return

        if not html:
            logging.info(f"Category {response.meta['category']} finished.")
            return

        # Parse partial HTML
        # Scrapy Selector can parse HTML string directly
        sel = scrapy.Selector(text=html)
        products = sel.css('li.item')
        
        if not products:
            return

        logging.info(f"Processing Page {response.meta['page_idx']} - Found {len(products)} items.")

        # Iterate products
        for p in products:
            # EXTRACT BASIC METADATA (Same as api.py)
            main_link = p.css('a.main-contain')
            if not main_link: continue
            
            # Base info
            raw_id = p.attrib.get('data-id')
            raw_name = main_link.attrib.get('data-name')
            brand = main_link.attrib.get('data-brand')
            
            # Internal fields
            internal_data = {
                "Internal_Pro_ID": main_link.attrib.get('data-pro', ""),
                "Internal_S_Code": main_link.attrib.get('data-s', ""),
                "Internal_Maingroup": p.attrib.get('data-maingroup', ""),
                "Internal_Subgroup": p.attrib.get('data-subgroup', ""),
                "Internal_Type": p.attrib.get('data-type', ""),
                "Internal_Vehicle": p.attrib.get('data-vehicle', ""),
                "Internal_OrderType": p.attrib.get('data-ordertypeid', ""),
            }


            
            # Extra fields
            utility = p.css('.utility')
            specs = utility.xpath('string()').get().strip().replace('\n', ', ') if utility else ""
            
            img_el = p.css('.item-img img')
            img_url = img_el.attrib.get('data-src') or img_el.attrib.get('src') if img_el else ""
            
            rating = ""
            rating_el = p.css('.vote-txt b::text').get()
            if rating_el: rating = rating_el.strip()
            
            vote_count = p.css('.vote-txt::text').get() or ""
            vote_count = vote_count.strip()
            
            installment = p.css('.lb-tragop::text').get() or ""
            label_online = p.css('.item-txt-online::text').get() or ""
            
            discount = ""
            disc_txt = p.css('.box-p::text').get()
            if disc_txt and '%' in disc_txt: discount = disc_txt.strip()

            # Capacity Variants
            variants_els = p.css('.merge__item')
            variants_str = ", ".join([v.xpath('string()').get().strip() for v in variants_els])
            
            # Pricing (Base)
            price_el = p.css('.price::text').get()
            raw_price = ''.join(filter(str.isdigit, price_el)) if price_el else "0"
            promo_price = int(raw_price) if raw_price else 0
            
            old_price_el = p.css('.price-old::text').get()
            raw_old = ''.join(filter(str.isdigit, old_price_el)) if old_price_el else "0"
            listed_price = int(raw_old) if raw_old else 0
            
            if promo_price == 0 and listed_price > 0: promo_price = listed_price
            if listed_price == 0 and promo_price > 0: listed_price = promo_price

            # ---------------------------------------------------------
            # PROCESS CAPACITIES & REQUEST DETAIL
            # ---------------------------------------------------------
            
            # Helper logic to yield Request
            def request_detail(v_element, is_main):
                # 1. Determine Identity
                if is_main:
                    final_name = raw_name
                    cap_id = raw_id
                    cap_price = promo_price
                    stock = "Yes"
                    
                    link_suffix = main_link.attrib.get('href', '')
                    full_link = f"https://www.thegioididong.com{link_suffix}" if link_suffix.startswith('/') else link_suffix
                else:
                    v_text = v_element.xpath('string()').get().strip()
                    # Clean Name
                    base_clean = raw_name
                    for m in variants_els:
                        m_txt = m.xpath('string()').get().strip()
                        if m_txt in base_clean:
                            base_clean = base_clean.replace(m_txt, "").strip()
                    base_clean = " ".join(base_clean.split())
                    final_name = f"{base_clean} {v_text}"
                    
                    cap_id = v_element.attrib.get('data-id')
                    cap_price = 0 # Inactive in list
                    stock = "Check Link"
                    
                    suffix = v_element.attrib.get('data-url', '')
                    


                    if len(suffix) > 2:
                        full_link = f"https://www.thegioididong.com{suffix}" if suffix.startswith('/') else suffix
                    else:
                        full_link = f"https://www.thegioididong.com{main_link.attrib.get('href', '')}"

                logging.info(f"Yielding Detail Request: {full_link}")

                # 2. Yield Request to Detail Page
                # We pass all the metadata we already scraped to the callback
                meta_data = {
                    "Product_ID": cap_id,
                    "Product_Name": final_name,
                    "Brand": main_link.attrib.get('data-brand'),
                    "Category": response.meta['category'],
                    'Specs': specs,
                    'Variants': variants_str,
                    'Ton_Kho': stock,
                    'Gia_Niem_Yet_Base': listed_price, # Pass base listed price
                    'Gia_Khuyen_Mai_Base': cap_price,
                    "Discount_Percent": discount,
                    "Installment": installment,
                    "Rating": rating,
                    "Vote_Count": vote_count,
                    "Date": get_vietnam_time(),
                    "Khuyen_Mai": "",
                    "Thanh_Toan": "",
                    "Link": full_link,
                    "Image_URL": img_url,
                    "Label_Online": label_online,
                    "screenshot_name": "Deep_Crawl_Scrapy",
                    # Internal
                    **internal_data
                }
                
                yield scrapy.Request(
                    url=full_link,
                    callback=self.parse_detail,
                    meta={'item_data': meta_data},
                    dont_filter=True # CRITICAL: Same URL used for multiple variants
                )

            if not variants_els:
                yield from request_detail(p, True)
            else:
                for v in variants_els:
                    v_id = v.attrib.get('data-id')
                    is_main_flag = (v_id == raw_id)
                    yield from request_detail(v, is_main_flag)

        # Pagination
        if len(products) > 0:
            next_page = response.meta['page_idx'] + 1
            payload = {
                "c": str(response.meta['params']['c']),
                "m": str(response.meta['params']['m']),
                "o": "13",
                "pi": str(next_page),
                "IsParentCate": "False",
                "IsShowCompare": "True",
                "prevent": "true"
            }
            yield scrapy.FormRequest(
                url=API_URL,
                formdata=payload,
                callback=self.parse_list_api,
                meta={
                    'category': response.meta['category'],
                    'params': response.meta['params'],
                    'page_idx': next_page
                }
            )

    def parse_detail(self, response):
        item_base = response.meta['item_data']
        
        # -------------------------------------------------------------
        # CAPACITY CHECK - Solve issues where variant URL is generic
        # -------------------------------------------------------------
        cap_buttons = response.css('.box03.group.desk .item')
        if cap_buttons:
            current_active_cap = cap_buttons.css('.act::text').get()
            if current_active_cap:
                current_active_cap = current_active_cap.strip()
                
                # Check if current Active matches our intended item
                if current_active_cap not in item_base['Product_Name']:
                    # We usually want "256GB" to MATCH "iPhone 17 ... 256GB"
                    # If mismatch (e.g. Active="256GB", Name="... 2TB"), REDIRECT.
                    
                    found_redirect = False
                    for btn in cap_buttons:
                        b_text = btn.xpath('string()').get().strip()
                        b_href = btn.attrib.get('href')
                        
                        if b_text in item_base['Product_Name'] and b_href:
                            new_link = f"https://www.thegioididong.com{b_href}" if b_href.startswith('/') else b_href
                            # logging.info(f"Redirecting {item_base['Product_Name']} to {new_link}")
                            
                            yield scrapy.Request(
                                url=new_link,
                                callback=self.parse_detail,
                                meta={'item_data': item_base},
                                dont_filter=True
                            )
                            found_redirect = True
                            break
                    
                    if found_redirect:
                        return # Stop processing this wrong page
        
        # 1. Extract Price for CURRENT Page (Active Color)
        current_price = 0
        price_txt = response.css('.bs_price strong::text').get() or response.css('.box-price-present::text').get()
        if price_txt:
            digits = ''.join(filter(str.isdigit, price_txt))
            if digits: current_price = int(digits)
            
        # 2. Identify Colors
        color_box = response.css('.box03.color')
        
        # If no color box, yield single item (Active)
        if not color_box:
            final_item = item_base.copy()
            final_item['Color'] = "Standard"
            final_item['SKU'] = response.css('.box03__item.act::attr(data-code)').get() or item_base.get('SKU', "")
            final_item['Gia_Khuyen_Mai'] = current_price if current_price > 0 else item_base['Gia_Khuyen_Mai_Base']
            final_item['Gia_Niem_Yet'] = item_base['Gia_Niem_Yet_Base']
            final_item['Ton_Kho'] = "Yes" if current_price > 0 else "Check Link"
            yield final_item
            return

        # 3. Process Colors
        items = color_box.css('.item')
        processed_colors = set()
        
        for item in items:
            color_name = item.xpath('string()').get().strip()
            sku = item.attrib.get('data-code', '')
            is_active = 'act' in item.attrib.get('class', '').split()
            
            href = item.attrib.get('href', '')
            specific_link = f"https://www.thegioididong.com{href}" if href.startswith('/') else href
            
            processed_colors.add(color_name)

            if is_active:
                # Yield Current Active Color
                final_item = item_base.copy()
                final_item['Color'] = color_name
                final_item['SKU'] = sku
                final_item['Link'] = specific_link or item_base['Link']
                final_item['Gia_Khuyen_Mai'] = current_price
                final_item['Gia_Niem_Yet'] = item_base['Gia_Niem_Yet_Base']
                final_item['Ton_Kho'] = "Yes" if current_price > 0 else "Contact"
                yield final_item
            else:
                # YIELD REQUEST for Inactive Color
                # We need to visit this URL to get its price!
                if specific_link and specific_link != item_base['Link']:
                    logging.info(f"  -> Recursing for color: {color_name} ({specific_link})")
                    meta_next = item_base.copy()
                    meta_next['Target_Color'] = color_name # Pass target to confirm
                    
                    yield scrapy.Request(
                        url=specific_link,
                        callback=self.parse_color_variant,
                        meta={'item_data': meta_next},
                        dont_filter=True
                    )

    def parse_color_variant(self, response):
        """
        Callback for specific color pages. 
        Only extracts the Active color (which matches our target).
        """
        item_base = response.meta['item_data']
        target_color = item_base.get('Target_Color')
        
        # Extract Price
        c_price = 0
        price_txt = response.css('.bs_price strong::text').get() or response.css('.box-price-present::text').get()
        if price_txt:
            c_price = int(''.join(filter(str.isdigit, price_txt)))
            
        # Extract Active Color Info
        active_item = response.css('.box03.color .item.act')
        if active_item:
            color_name = active_item.xpath('string()').get().strip()
            sku = active_item.attrib.get('data-code', '')
            
            final_item = item_base.copy()
            final_item['Color'] = color_name
            final_item['SKU'] = sku
            final_item['Link'] = response.url
            final_item['Gia_Khuyen_Mai'] = c_price
            final_item['Gia_Niem_Yet'] = item_base['Gia_Niem_Yet_Base']
            final_item['Ton_Kho'] = "Yes" if c_price > 0 else "Check Link"
            
            # Sanity check: intended color vs crawled active color
            # Just yield whatever is active on this page
            yield final_item

if __name__ == "__main__":
    # Ensure dir
    os.makedirs(f"content/{get_vietnam_time()}", exist_ok=True)
    
    process = CrawlerProcess()
    process.crawl(AppleDeepSpider)
    process.start()
