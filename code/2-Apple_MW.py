import csv
import os
import pandas as pd
import re
import time
from datetime import datetime
import urllib.parse
from pathlib import *
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from Daily_Promotion.code.sites import *
import concurrent.futures
import threading

# Global lock for CSV writing
csv_lock = threading.Lock()

def chrome_drive():
    options=Options()

    # Set headless mode to reduce resource usage and avoid detection
    # options.add_argument('--headless')

    options.binary_location='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    s=Service(chrome_2)
    driver=webdriver.Chrome(service = s, options = options)

    # Disable the "Chrome is being controlled by automated test software" notification
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # # Disable the "navigator.webdriver" property
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    # Disable the "Chrome is being controlled by automated test software" banner
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Maximize the window to avoid fingerprinting based on screen resolution
    # options.add_argument("start-maximized")

    # Disabling the Automation Extension can help prevent detection as an automated script and increase the chances of
    # successfully completing your automation tasks.
    options.add_experimental_option('useAutomationExtension', False)

    # This argument tells the browser to ignore any SSL certificate errors that may occur while accessing a website,
    # which is useful when testing on a site with a self-signed or invalid SSL certificate. Without this argument,
    # the browser will display a warning message about the certificate and require manual confirmation to proceed.
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors=yes')

    prefs={
        "disable-transitions": True,
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)

    return driver

import pytz
# Define the Vietnam timezone
local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
# Get the current time in UTC
now_utc = datetime.now(pytz.utc)
# Convert UTC time to local time
now = now_utc.astimezone(local_tz).now().date().strftime('%Y-%m-%d')


class MW:

    def process_single_link(self, link: str, vnpay_flag = False):
        print(f"Processing: {link}")
        driver = None
        try:
            driver = chrome_drive()
            wait = WebDriverWait(driver, 20)
            actions = ActionChains(driver)

            # Define the base path to Google Drive folder
            # Use path relative to the script location to be safe
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.join(script_dir, '')
            
            if not os.path.exists(base_path):
                os.makedirs(base_path)
            output_dir=os.path.join(base_path, f"{now}")
            output_img=os.path.join(output_dir, 'img_mw')

            def record(data_list):
                output_dir=os.path.join(base_path, f"{now}")

                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                file_path=os.path.join(output_dir, f"2-mw-{now}.csv")

                with csv_lock:
                    with open(file_path, "a") as file:
                        writer=csv.DictWriter(file,
                                                fieldnames=["Product_Name", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                                                            "Chien_Gia", '+VNPAY', "Store_Chien", "Date",
                                                    "Khuyen_Mai", "Uu_Dai_Them", "Link", 'screenshot_name'], delimiter = ";")
                        # Check if file is empty to write header
                        if os.stat(file_path).st_size == 0:
                            writer.writeheader()
                        for row in data_list:
                            writer.writerow(row)

            def screen_shot(product_name):
                if not os.path.exists(output_img):
                    os.makedirs(output_img)
                product_name_new=re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
                driver.fullscreen_window()
                driver.set_window_size(1920, 2080)
                driver.get_screenshot_as_png()
                product_name_new=f"{output_img}/{product_name_new}_{now_utc.astimezone(local_tz)}.png"
                driver.save_screenshot(product_name_new)
                return product_name_new.replace(f"{output_img}/", "")

            # Selector strategies
            SHOCK_PRICE_SELECTORS = [
                (By.CSS_SELECTOR, ".bs_price strong"),
                (By.XPATH, ".//div[@class='bc_title']/div/strong"),
                (By.CSS_SELECTOR, ".oo-left strong")
            ]
            
            SHOCK_PRICE_OLD_SELECTORS = [
                 (By.CSS_SELECTOR, ".bs_price em"),
                 (By.XPATH, ".//div[@class='bc_title']/div/em"),
                 (By.CSS_SELECTOR, ".oo-left em")
            ]

            REGULAR_PRICE_SELECTORS = [
                (By.CLASS_NAME, "giamsoc-ol-price"),
                (By.CLASS_NAME, "box-price-present"),
                (By.CSS_SELECTOR, ".center b"),
                (By.XPATH, "//ul[@class='prods-price']/li//span") # New selector from research
            ]
            
            OLD_PRICE_SELECTORS = [
                (By.CLASS_NAME, "box-price-old"),
                (By.CLASS_NAME, "box-price-present"), # Fallback if old price not found
                (By.CSS_SELECTOR, ".center b"),
                (By.XPATH, "//ul[@class='prods-price']/li//del") # New selector from research
            ]

            PRODUCT_NAME_SELECTORS = [
                (By.TAG_NAME, "h1"),
                (By.XPATH, "//ul[@class='breadcrumb']/li[last()]") # Fallback from research
            ]

            def find_element_safe(selectors):
                for by, value in selectors:
                    try:
                        element = driver.find_element(by, value)
                        return element
                    except NoSuchElementException:
                        continue
                return None

            def check_shock_price():
                # Check for special case where price is so low that no other promotion is applied
                element = find_element_safe(SHOCK_PRICE_SELECTORS)
                if element:
                    gia_soc = element.text.replace(" *", "")
                    gia_khuyen_mai = gia_soc + "soc"
                    
                    # Try to find corresponding old price
                    old_element = find_element_safe(SHOCK_PRICE_OLD_SELECTORS)
                    if old_element:
                        gia_niem_yet = old_element.text.replace(" *", "")
                    else:
                        gia_niem_yet = "0" # Or handle as needed
                        
                    return gia_khuyen_mai, gia_niem_yet
                return None

            def check_cash_discount(gia_khuyen_mai_raw):
                try:
                    driver.find_element(By.CLASS_NAME, "label-radio")
                except NoSuchElementException:
                    try:
                        promo_element=driver.find_element(By.CLASS_NAME, "promo")
                    except NoSuchElementException:
                        return gia_khuyen_mai_raw
                    else:
                        option_km_thems=promo_element.text
                        for option in option_km_thems.split("\n"):
                            if ("triệu" in option.lower()):
                                km_them_raw=option[(option.index("ngay") + 5): (option.index(" triệu"))].strip()
                                if ('.' not in km_them_raw) and (',' not in km_them_raw):
                                    km_them=km_them_raw + "000000"
                                    gia_khuyen_mai_new=int(
                                        gia_khuyen_mai_raw.replace("đ", "").replace(".", "").replace("₫", "")) - int(
                                        km_them)
                                    return gia_khuyen_mai_new
                                else:
                                    km_them=km_them_raw.replace('.', '').replace(',', '') + "00000"
                                    gia_khuyen_mai_new=int(
                                        gia_khuyen_mai_raw.replace("đ", "").replace(".", "").replace("₫", "")) - int(
                                        km_them)
                                    return gia_khuyen_mai_new
                            else:
                                gia_khuyen_mai_new=int(
                                    gia_khuyen_mai_raw.replace("đ", "").replace(".", "").replace("₫", ""))
                                return gia_khuyen_mai_new
                else:
                    option_km_them=driver.find_elements(By.CLASS_NAME, "label-radio")
                    for i in option_km_them:
                        pattern=r"(?=.*giảm)(?=.*đ)(?!.*ava)(?!.*xanh)"
                        match=re.search(pattern, i.text, re.IGNORECASE)
                        if match:
                            try:
                                km_them=int(
                                    driver.find_element(By.CLASS_NAME, "label-radio").text.replace("Giảm giá ", "")
                                    .replace("đ", "").replace("*", "").replace(".", "").replace(",", ""))
                            except ValueError:
                                km_them=0
                            gia_khuyen_mai_new=int(gia_khuyen_mai_raw.replace("đ", "").replace(".", "").replace("₫", "")) \
                                               - int(km_them)
                            return gia_khuyen_mai_new
                        else:
                            gia_khuyen_mai_new=gia_khuyen_mai_raw
                            return gia_khuyen_mai_new

            def check_price():
                def vnpay_mw(km, khuyen_mai):
                    promotion_details=khuyen_mai.lower()
                    try:
                        km=km.replace(".", "").replace(",", "").replace("đ", "").replace("₫", "")
                    except ValueError:
                        km=0
                    except AttributeError:
                        pass

                    if ("qrcode" in promotion_details) or ("vnpay" in promotion_details):
                        for promotion in promotion_details.split("\n"):
                            if ("qrcode" in promotion) or ("vnpay" in promotion):
                                if "%" in promotion:
                                    try:
                                        percent_discount=int(promotion[(promotion.index("%") - 2):promotion.index("%")])
                                    except ValueError:
                                        percent_discount=100

                                    try:
                                        max_raw_discount=promotion[(promotion.index("thêm") + 5):]
                                    except ValueError:
                                        try:
                                            max_raw_discount=promotion[(promotion.index("đa") + 3):]
                                        except ValueError:
                                            max_raw_discount=""

                                    try:
                                        max_discount=int(
                                            (max_raw_discount[:max_raw_discount.index("đ")]).replace(".", "").
                                            replace("₫", "").replace("đ", "").replace("k", "000"))
                                    except ValueError:
                                        max_discount=0

                                else:
                                    try:
                                        max_raw_discount=promotion[(promotion.index("đến") + 3):]
                                    except ValueError:
                                        max_raw_discount=promotion[(promotion.index("đa") + 3):]
                                    if "đơn hàng từ" not in promotion:
                                        max_discount=int(
                                            max_raw_discount[:max_raw_discount.index("đ")].replace(".", "").replace(",",
                                                                                                                    ""))
                                    elif "đơn hàng từ" in promotion:
                                        condition=int(promotion[(promotion.index("đơn hàng từ") + 12):(
                                            promotion.index("triệu"))]) * 1000000
                                        if int(km.replace("soc", "")) >= condition:
                                            max_discount=int(
                                                max_raw_discount[:max_raw_discount.index("k")].replace(".", "").replace(",",
                                                                                                                        "")) * 1000
                                        else:
                                            max_discount=0

                                    percent_discount=100

                        total_discount_1=int(km.replace("soc", "")) * ((100 - percent_discount) / 100)
                        total_discount_2=int(km.replace("soc", "")) - max_discount
                        total_discount=max(total_discount_1, total_discount_2)
                    else:
                        total_discount=km
                    return total_discount

                def vnpay_mw_table(km, oc_vnpay_dict: dict, now: str):
                    pattern=r'[₫,\.đ]|soc'
                    if isinstance(km, str):
                        try:
                            km=int(re.sub(pattern, '', km))
                        except ValueError:
                            return km

                    if isinstance(km, float):
                        km=int(km)

                    oc_vnpay_df=pd.DataFrame.from_dict(oc_vnpay_dict)
                    current_date=pd.to_datetime(now).date()
                    valid_date=pd.to_datetime(oc_vnpay_df.iloc[0]['Date_MW']).date()

                    if current_date <= valid_date:
                        try:
                            for _, row in oc_vnpay_df.iterrows():
                                low_range=int(row['Range_Low_MW'])
                                high_range=int(row['Range_High_MW'])

                                if low_range <= km < high_range:
                                    discount_amount=int(row['VNPay_Amount_MW'])
                                    return km - discount_amount
                        except ValueError:
                            return 0
                        return km

                def check_ton_kho():
                    try:
                        special_note=driver.find_element(By.CLASS_NAME, "productstatus")
                    except NoSuchElementException:
                        try:
                            driver.find_element(By.CLASS_NAME, "buttonsub")
                        except NoSuchElementException:
                            ton_kho="Yes"
                        else:
                            ton_kho="No"
                    else:
                        if ("ngừng" or "tạm" or 'sắp') in special_note.text.lower():
                            ton_kho="not trading"
                        else:
                            ton_kho="No"
                    return ton_kho

                ton_kho = check_ton_kho()

                try:
                    green_price_box=driver.find_element(By.XPATH, "//div[@class='box-price green jsClick']")
                    actions.click(green_price_box).perform()
                    time.sleep(1.5)
                    is_green_price_box_present=True
                except NoSuchElementException:
                    is_green_price_box_present=False
                    pass

                soup=BeautifulSoup(driver.page_source, 'html.parser')
                
                # Use selector list for product name
                name_element = find_element_safe(PRODUCT_NAME_SELECTORS)
                if name_element:
                    product_name = name_element.text.strip().replace("Mini", "mini")
                    to_remove_in_name=["Điện thoại ", "Máy tính bảng ", "Laptop Apple ", "Tai nghe chụp tai Bluetooth ",
                                       "Tai nghe Bluetooth ", "Thiết bị định vị thông minh "]
                    for item in to_remove_in_name:
                        if item in product_name:
                            product_name=product_name.replace(item, "")
                else:
                    product_name=f"Please double check the link: {link}"
                print(product_name)

                try:
                    khuyen_mai=driver.find_element(By.CLASS_NAME, "pr-item").text.replace("Xem chi tiết",
                                                                                          ",").strip().replace("\n\n\n",
                                                                                                               "\n")
                except NoSuchElementException:
                    khuyen_mai=""

                thanh_toan_raw=soup.find_all("div", class_ = "campaign")
                if len(thanh_toan_raw) == 0:
                    thanh_toan_detail=""
                else:
                    thanh_toan_detail=thanh_toan_raw[0].get_text().strip().replace("\n\n\n", "\n").replace("\n?", "")
                try:
                    uu_dai_them=soup.find_all('div', class_ = "promoadd")[0].get_text().strip().replace("\n\n\n", "\n")
                except IndexError:
                    uu_dai_them=""

                khuyen_mai=khuyen_mai + "\n" + thanh_toan_detail

                shock = check_shock_price()
                if shock:
                    gia_khuyen_mai, gia_niem_yet=shock
                    price_fighting=0
                    store_fighting=""
                else:
                    # Check regular price using selector list
                    element = find_element_safe(REGULAR_PRICE_SELECTORS)
                    
                    if element:
                        # Handle special logic for box-price-present which might appear twice
                        if element.get_attribute("class") == "box-price-present":
                             elements = driver.find_elements(By.CLASS_NAME, "box-price-present")
                             if len(elements) == 2:
                                 # Take the second one if there are two
                                 element = elements[1]
                        
                        gia_khuyen_mai_raw = element.text.replace("Giá dự kiến: ", "").replace("Giá bán:", "").replace("*", "").strip()
                        gia_khuyen_mai = check_cash_discount(gia_khuyen_mai_raw)
                    else:
                        # Fallback to checking product status
                        try:
                            special_note=driver.find_element(By.CLASS_NAME, "productstatus")
                            if ("ngừng" or "tạm" or 'sắp') in special_note.text.lower():
                                gia_khuyen_mai="not trading"
                            else:
                                gia_khuyen_mai= 'not trading'
                        except NoSuchElementException:
                            gia_khuyen_mai=0

                    # Check old price
                    old_element = find_element_safe(OLD_PRICE_SELECTORS)
                    if old_element:
                         gia_niem_yet = old_element.text.replace("Giá dự kiến: ", "").replace("Giá bán:", "").strip()
                    else:
                         # Fallback logic
                         try:
                            special_note=driver.find_element(By.CLASS_NAME, "productstatus")
                            if ("ngừng" or "tạm" or 'sắp') in special_note.text.lower():
                                gia_niem_yet="not trading"
                            else:
                                gia_niem_yet= 'not trading'
                         except NoSuchElementException:
                             gia_niem_yet=0

                    if is_green_price_box_present == True:
                        price_fighting_raw=driver.find_elements(By.CLASS_NAME, "box-price-present")[0].text.replace(
                            "Giá dự kiến: ", "").replace("*", "")
                        price_fighting=check_cash_discount(price_fighting_raw)
                        try:
                            store_fighting=soup.find("div", class_ = "fstore expand").get_text()
                        except AttributeError:
                            store_fighting="No detail about stores where store_fighting is applied"
                    else:
                        price_fighting=0
                        store_fighting=""


                if vnpay_flag == True:
                    if price_fighting !=0:
                        price_to_calculate_vnpay = price_fighting
                    else:
                        price_to_calculate_vnpay = gia_khuyen_mai
                    gia_khuyen_mai_vnpay = vnpay_mw_table(price_to_calculate_vnpay, oc_vnpay_dict, now)

                    screenshot_name = screen_shot(product_name)

                    new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                              "Gia_Khuyen_Mai": gia_khuyen_mai, "Chien_Gia": price_fighting, '+VNPAY': gia_khuyen_mai_vnpay,
                              "Store_Chien": store_fighting,
                              "Date": now,
                              "Khuyen_Mai": khuyen_mai, "Uu_Dai_Them": uu_dai_them, "Link": link,
                              'screenshot_name': screenshot_name
                              }
                    return new_data
                else:
                    if price_fighting !=0:
                        price_to_calculate_vnpay = price_fighting
                    else:
                        price_to_calculate_vnpay = gia_khuyen_mai
                    gia_khuyen_mai_vnpay = vnpay_mw(price_to_calculate_vnpay, khuyen_mai)

                    screenshot_name = screen_shot(product_name)

                    new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                              "Gia_Khuyen_Mai": gia_khuyen_mai, "Chien_Gia": price_fighting, '+VNPAY': gia_khuyen_mai_vnpay, "Store_Chien": store_fighting,
                              "Date": now,
                              "Khuyen_Mai": khuyen_mai, "Uu_Dai_Them": uu_dai_them, "Link": link,
                              'screenshot_name': screenshot_name
                              }
                    return new_data

            driver.get(link)
            time.sleep(7)
            data = check_price()
            if data:
                record([data])
            
        except TimeoutException:
            print(f"Timeout for link: {link}")
        except WebDriverException as e:
            print(f"WebDriverException for link: {link}: {e}")
        except Exception as e:
            print(f"Error processing link {link}: {e}")
        finally:
            if driver:
                driver.quit()

if __name__ == "__main__":
    user_links = total_links['mw_urls']
    # Use ThreadPoolExecutor to run in parallel
    # Adjust max_workers based on system capabilities
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(MW().process_single_link, link, vnpay_flag=True) for link in user_links]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred: {e}")
