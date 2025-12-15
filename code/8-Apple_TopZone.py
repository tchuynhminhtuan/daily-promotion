import csv
import os
import os.path
import pandas as pd
import re
from datetime import datetime
from selenium import webdriver
from Daily_Promotion.code.sites import *
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
import time
import pytz


# Define the Vietnam timezone
local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
# Get the current time in UTC
now_utc = datetime.now(pytz.utc)
# Convert UTC time to local time
now = now_utc.astimezone(local_tz).now().date().strftime('%Y-%m-%d')


def chrome_drive():
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    options = Options()

    # Set headless mode to reduce resource usage and avoid detection
    options.add_argument('--headless')

    options.binary_location='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

    s = Service(chrome_8)
    driver = webdriver.Chrome(service=s, options=options)

    # options.add_argument("--incognito")
    options.add_argument("--guest")

    # # Disable browser extensions
    options.add_argument("--disable-extensions")

    # create a UserAgent object
    # user_agent = UserAgent()

    # get a random user agent string
    # random_ua = user_agent.random

    # set the user agent in Chrome options
    # options.add_argument(f'user-agent={random_ua}')

    # Disable the "Chrome is being controlled by automated test software" notification
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # # Disable the "navigator.webdriver" property
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    # Disable the "Chrome is being controlled by automated test software" banner
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Maximize the window to avoid fingerprinting based on screen resolution
    options.add_argument("start-maximized")

    # Disabling the Automation Extension can help prevent detection as an automated script and increase the chances of
    # successfully completing your automation tasks.
    options.add_experimental_option('useAutomationExtension', False)

    # This argument tells the browser to ignore any SSL certificate errors that may occur while accessing a website,
    # which is useful when testing on a site with a self-signed or invalid SSL certificate. Without this argument,
    # the browser will display a warning message about the certificate and require manual confirmation to proceed.
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors=yes')

    # wait for the page to be fully loaded before proceeding
    options.page_load_strategy = 'normal'  # 'none', 'eager', or 'normal'

    prefs = {
        "disable-transitions": True,
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)

    return driver


class TZ:
    def tz(self, link_check: list, restart_link: str, vnpay_flag=False):

        driver=chrome_drive()

        wait=WebDriverWait(driver, 20)

        # Define the base path
        base_path='../content'
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        output_dir=os.path.join(base_path, f"{now}")
        output_img=os.path.join(output_dir, 'img_tz')

        def record():
            output_dir=os.path.join(base_path, f"{now}")

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_path=os.path.join(output_dir, f"8-topzone-{now}.csv")

            with open(file_path, "a") as file:
                writer=csv.DictWriter(file,
                                      fieldnames = ["Product_Name", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                                                    "+VNPAY", "Date",
                                                    "Khuyen_Mai", "vnpay", "Link", "screenshot_name"], delimiter = ";")
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
            # Scroll up by 100 pixels
            driver.execute_script("window.scrollBy(0, -100);")
            driver.get_screenshot_as_png()
            product_name_new=f"{output_img}/{product_name_new}_{now_utc.astimezone(local_tz)}.png"
            driver.save_screenshot(product_name_new)
            return product_name_new.replace(f"{output_img}/", "")

        def check_cash_discount(gia_khuyen_mai_raw):

            # 2 Check xem có khuyến mại bằng tiền mặt giảm trực tiếp không
            try:
                # This is when a direct discount is applied
                driver.find_element(By.CLASS_NAME, "choose")
            except NoSuchElementException:
                gia_khuyen_mai_new=gia_khuyen_mai_raw
                return gia_khuyen_mai_new
            else:
                option_km_them=driver.find_elements(By.CLASS_NAME, "choose")
                for i in option_km_them:
                    # if ("đ" in i.text.lower()) and ("ava" not in i.text.lower()) and ("xanh" not in i.text.lower()):
                    if ("đ" in i.text.lower()) and ("ava" not in i.text.lower()) and (
                            "xanh" not in i.text.lower()) and ("giảm" in i.text.lower()):
                        # i.click()
                        # time.sleep(1)
                        try:
                            km_them=int(
                                driver.find_element(By.CLASS_NAME, "choose").text.replace("Giảm giá ", "")
                                .replace("đ", "").replace("*", "").replace(".", "").replace(",", "").replace('₫', ''))
                            print(f"km_them: {km_them}")
                        except ValueError:
                            # This happends only when there is no cash discount, but the channel
                            # offers promotion in kind instead
                            km_them=0
                            print(f"km_them: {km_them}")
                        gia_khuyen_mai_new=int(gia_khuyen_mai_raw.replace("đ", "").replace(".", "").replace("₫", "")) \
                                           - int(km_them)

                        print(f"mai: {gia_khuyen_mai_new}")
                        return gia_khuyen_mai_new
                    else:
                        gia_khuyen_mai_new=gia_khuyen_mai_raw
                        return gia_khuyen_mai_new
            # finally:
            #     return gia_khuyen_mai_new

        def check_shock_price():
            # Check for special case where price is so low that no other promotion is applied
            try:
                # gia_soc = driver.find_element(By.CSS_SELECTOR, ".bs_title strong").text.replace(" *", "")
                # From Feb 18th, 2023
                gia_soc=driver.find_element(By.CSS_SELECTOR, ".bs_price strong").text.replace(" *", "")
            except NoSuchElementException:
                try:
                    # This class started on August 19th, 2022
                    gia_soc=driver.find_element(By.CSS_SELECTOR, ".oo-left strong").text.replace(" *", "")
                except NoSuchElementException:
                    return None
                else:
                    gia_khuyen_mai=gia_soc + "soc"
                    gia_niem_yet=driver.find_element(By.CSS_SELECTOR, ".oo-left em").text.replace(" *", "")
                    # print(gia_khuyen_mai)
                    # print(gia_niem_yet)
                    return gia_khuyen_mai, gia_niem_yet
            else:
                # return gia_soc + "soc"
                gia_khuyen_mai=gia_soc + "soc"
                gia_niem_yet=driver.find_element(By.CSS_SELECTOR, ".bs_price em").text.replace(" *", "")
                # print(gia_khuyen_mai)
                # print(gia_niem_yet)
                return gia_khuyen_mai, gia_niem_yet

        def check_price():
            # wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h1")))
            try:
                driver.find_element(By.TAG_NAME, "h1")

            except NoSuchElementException:
                product_name=f"Please double check the link: {link}"
                print(product_name)
                ton_kho="No"
                gia_niem_yet=0
                gia_khuyen_mai=0
                khuyen_mai=""
                vnpay="0"
                gia_khuyen_mai_vnpay=0
                new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                          "Gia_Khuyen_Mai": gia_khuyen_mai, "+VNPAY": gia_khuyen_mai_vnpay, "Date": now,
                          "Khuyen_Mai": khuyen_mai, "vnpay": vnpay,
                          "Link": link}
                data_list.append(new_data)

            else:
                # # From Dec 1st, 2023, click to color button to know what is the best price
                # color_options = driver.find_elements(By.XPATH, "(//div[@class='color-sp']/ul/li)")
                # num_color_options = len(color_options)
                # for num in reversed(range(num_color_options)):
                #     driver.execute_script("arguments[0].click();", color_options[num])
                #     time.sleep(2)
                #     color_options = driver.find_elements(By.XPATH, "(//div[@class='color-sp']/ul/li)")

                # If the product has the class="capacity", use this capacity to add to product name
                try:
                    driver.find_element(By.CLASS_NAME, "capacity")

                except NoSuchElementException:
                    product_name=link[link.rindex("/") + 1:].replace("-", " ").replace("iphone", "iPhone").replace(
                        "pro",
                        "Pro").replace(
                        "gb", "GB").replace("tb", "TB").replace("max", "Max").replace("macbook", "MacBook").replace(
                        "ipad",
                        "iPad").replace(
                        "apple", "Apple").replace("watch", "Watch")
                else:
                    capacities=driver.find_elements(By.CSS_SELECTOR, ".capacity ul > li")
                    capacity_text=str
                    for capacity in capacities:
                        if capacity.get_attribute("class") == "active":
                            capacity_text=capacity.text
                        else:
                            pass
                    try:
                        product_name=driver.find_element(By.TAG_NAME, "h1").text.replace(" Mới",
                                                                                         "") + " " + capacity_text
                    except TypeError:
                        product_name=link[link.rindex("/") + 1:]
                print(product_name)

                try:
                    driver.find_element(By.CLASS_NAME, "btn-buy")
                except NoSuchElementException:
                    ton_kho="No"
                else:
                    ton_kho="Yes"
                print(ton_kho)

                try:
                    driver.find_element(By.CSS_SELECTOR, ".price")
                except NoSuchElementException:
                    try:
                        driver.find_element(By.CSS_SELECTOR, ".bs_price")
                    except NoSuchElementException:
                        ton_kho="No"
                        gia_niem_yet="not trading"
                        gia_khuyen_mai="not trading"
                        khuyen_mai="not trading"
                        vnpay="0"
                        gia_khuyen_mai_vnpay=0
                        new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                                  "Gia_Khuyen_Mai": gia_khuyen_mai, "+VNPAY": gia_khuyen_mai_vnpay, "Date": now,
                                  "Khuyen_Mai": khuyen_mai, "vnpay": vnpay,
                                  "Link": link}
                        data_list.append(new_data)
                    else:
                        # Apply from June 27th, 2023
                        shock=check_shock_price()
                        if shock:
                            gia_khuyen_mai, gia_niem_yet=shock
                            vnpay=0
                else:
                    gia_raw=driver.find_element(By.CSS_SELECTOR, ".price").text
                    # print(gia_raw)
                    if gia_raw.count("₫") == 2:
                        gia_niem_yet=gia_raw[
                                     (gia_raw.index("₫") + 2):(gia_raw.index("₫", gia_raw.index("₫") + 2) + 1)].replace(
                            "*", "")
                        gia_khuyen_mai_raw=gia_raw[:(gia_raw.index("₫") + 1)].replace("*", "")
                        gia_khuyen_mai=check_cash_discount(gia_khuyen_mai_raw)
                    else:
                        try:
                            gia_khuyen_mai_raw=driver.find_element(By.CLASS_NAME, "giamsoc-ol-price").text.replace("*",
                                                                                                                   "")
                            gia_khuyen_mai=check_cash_discount(gia_khuyen_mai_raw)
                            gia_niem_yet=driver.find_element(By.CSS_SELECTOR, ".price").text.replace("*", "")
                        except NoSuchElementException:
                            gia_niem_yet=driver.find_element(By.CSS_SELECTOR, ".price").text.replace("*", "")
                            gia_khuyen_mai_raw=gia_niem_yet
                            gia_khuyen_mai=check_cash_discount(gia_khuyen_mai_raw)
                    print(f"gia_niem_yet : {gia_niem_yet}")
                    print(f"gia_khuyen_mai: {gia_khuyen_mai}")

                    # From early June 2022, Topzone has dedicated line for VNPAYQR already, these line to record VNPAYQR
                    try:
                        driver.find_element(By.ID, "vnpayqr")
                    except NoSuchElementException:
                        vnpay="0"
                    else:
                        payment_raws=driver.find_elements(By.CLASS_NAME, "campaign-option")
                        for payment in payment_raws:
                            if "vnpayqr" in payment.get_attribute("data-campaignname").lower():
                                # vnpay = payment.find_element(By.TAG_NAME, "b b").text.replace(".", "").replace("₫", "")
                                vnpay=payment.find_element(By.XPATH,
                                                           "//figure[@class='vnpayqr']/following-sibling::b/b").text.replace(
                                    ".", "").replace("₫", "")
                                print(f"vnpay {vnpay}")
                            else:
                                pass

                # Promotion in text
                try:
                    driver.find_element(By.ID, "promotion-detail")
                except NoSuchElementException:
                    khuyen_mai=""
                else:
                    khuyen_mai=driver.find_element(By.ID, "promotion-detail").text

                def vnpay_tz(km):
                    # Check if VNPAYQR is already recorded in Topzone dataframe
                    try:
                        if int(vnpay) > 0:
                            # Calculate the total discount amount
                            return int(km) - vnpay
                    except ValueError:
                        return km

                    # If VNPAY is not recorded, check if it's in the promotion note
                    if isinstance(km, str):
                        km=re.sub(r'[₫,.đ]', '', km)

                    try:
                        km=int(km)
                    except ValueError:
                        # if it is string type, return
                        return km

                    if isinstance(khuyen_mai, str):
                        promotion_note=khuyen_mai.lower()
                        if "vnpay" in promotion_note:
                            promotions=promotion_note.split("\n")
                            for promotion in promotions:
                                if "vnpay" in promotion:
                                    if "%" in promotion:
                                        percent_discount=int(promotion.split("%")[0][-2:])
                                        max_discount=int(re.sub(r'[₫,.đ]', '', promotion.split("đa")[1]))
                                    else:
                                        max_discount=int(re.sub(r'[₫,.đ]', '', promotion.split("đến")[1]))
                                        percent_discount=100

                                    # Calculate the total discount amount
                                    total_discount=km * ((100 - percent_discount) / 100)
                                    return min(total_discount, max_discount)
                    return km

                def vnpay_mw_table(km, oc_vnpay_dict: dict, now: str):

                    pattern=r'[₫,\.đ]|soc'  # Define a regex pattern to match '₫', ',', and 'soc'
                    # Use regex to replace the specified pattern if km is a string
                    if isinstance(km, str):
                        km=int(re.sub(pattern, '', km))

                    # many time, the final price board has .0 at the end, so I need to take this step
                    if isinstance(km, float):
                        km=int(km)

                    # Create DataFrame of VNPAY discount from dictionary
                    oc_vnpay_df=pd.DataFrame.from_dict(oc_vnpay_dict)

                    # Check if the current date is within the valid range
                    current_date=pd.to_datetime(now).date()
                    valid_date=pd.to_datetime(oc_vnpay_df.iloc[0]['Date_MW']).date()

                    if current_date <= valid_date:
                        try:
                            for _, row in oc_vnpay_df.iterrows():
                                low_range=int(row['Range_Low_MW'])
                                high_range=int(row['Range_High_MW'])

                                # Check if km is within the range
                                if low_range <= km < high_range:
                                    # Calculate the amount of VNPAY discount
                                    discount_amount=int(row['VNPay_Amount_MW'])
                                    return km - discount_amount
                        except ValueError:
                            # Handle the case where km is just a text
                            return 0
                        return km

                if vnpay_flag == True:
                    gia_khuyen_mai_vnpay=vnpay_mw_table(gia_khuyen_mai, oc_vnpay_dict, now)
                else:
                    gia_khuyen_mai_vnpay=vnpay_tz(gia_khuyen_mai)

                screenshot_name=screen_shot(product_name)

                new_data={"Product_Name": product_name, "Ton_Kho": ton_kho,
                          "Gia_Niem_Yet": gia_niem_yet.replace("Giá dự kiến:", ""),
                          "Gia_Khuyen_Mai": gia_khuyen_mai, "+VNPAY": gia_khuyen_mai_vnpay, "Date": now,
                          "Khuyen_Mai": khuyen_mai, "vnpay": vnpay, "Link": link, 'screenshot_name': screenshot_name}
                data_list.append(new_data)

        self.link_check=link_check
        self.restart_link=restart_link

        for link in self.link_check[self.link_check.index(self.restart_link):]:
            print(link)
            data_list=[]
            try:
                driver.get(link)
                time.sleep(5)
                check_price()
                record()
            except (TimeoutException, WebDriverException):
                print(datetime.now())
                print(f"Start again from link: {link}")
                self.restart_link=link
                self.tz(self.restart_link)

        driver.quit()


link = 'https://www.topzone.vn/mac/apple-macbook-air-m2-2023'
index = total_links['tz_urls'].index(link)
user_links = total_links['tz_urls']
TZ().tz(user_links, user_links[index], vnpay_flag=False)
