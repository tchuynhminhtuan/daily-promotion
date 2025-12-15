import csv
import os
from bs4 import BeautifulSoup
import pandas as pd
import os.path
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from Daily_Promotion.code.sites import *
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


import pytz
# Define the Vietnam timezone
local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
# Get the current time in UTC
now_utc = datetime.now(pytz.utc)
# Convert UTC time to local time
now = now_utc.astimezone(local_tz).now().date().strftime('%Y-%m-%d')

# Chrome
def chrome_drive():
    options = Options()

    # Set headless mode to reduce resource usage and avoid detection
    options.add_argument('--headless')
    options.binary_location='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    s = Service(chrome_3)
    driver = webdriver.Chrome(service=s, options=options)

    # options.add_argument("--incognito")
    # options.add_argument("--guest")

    # # Disable browser extensions
    # options.add_argument("--disable-extensions")

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


class HH:
    def hh(self, link_check: list, restart_link: str):

        driver = chrome_drive()

        # Define the base path to Google Drive folder
        base_path='../content'
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        output_dir=os.path.join(base_path, f"{now}")
        output_img=os.path.join(output_dir, 'img_hh')

        def record():
            output_dir=os.path.join(base_path, f"{now}")

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_path=os.path.join(output_dir, f"3-hh-{now}.csv")

            with open(file_path, "a") as file:
                writer=csv.DictWriter(file,
                                      fieldnames=["Product_Name", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai", "Date",
                                                "Khuyen_Mai", "Link", "screenshot_name"], delimiter=";")
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
            # driver.execute_script("window.scrollBy(0, -100);")
            driver.get_screenshot_as_png()
            product_name_new=f"{output_img}/{product_name_new}_{now_utc.astimezone(local_tz)}.png"
            driver.save_screenshot(product_name_new)
            return product_name_new.replace(f"{output_img}/", "")


        def check_price():

            try:
                popup=WebDriverWait(driver, 6).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@id='popup-modal']/a[2]")))
                driver.execute_script("arguments[0].scrollIntoView(true);", popup)
                driver.execute_script("arguments[0].click();", popup)
                time.sleep(2)
                try:
                    more_offer = WebDriverWait(driver, 6).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@id='close-button-1545222288830']")))
                    driver.execute_script("arguments[0].scrollIntoView(true);", more_offer)
                    driver.execute_script("arguments[0].click();", more_offer)
                    time.sleep(2)
                except TimeoutException:
                    pass
            except TimeoutException:
                pass

            try:
                cover = driver.find_element(By.XPATH, '//a[@class="close-modal icon-minutes"]')
                cover.click()
                time.sleep(1)
            except NoSuchElementException:
                pass

            # soup = BeautifulSoup(driver.page_source, 'html.parser')
            # product_name_raw = soup.find_all("div", class_="top-product")
            # product_name_raw = driver.find_element(By.CLASS_NAME, "top-product")

            # List of words should be removed
            to_remove_in_name = [" Chính hãng VN/A", "chính hãng VN/A", "Điện thoại di động ", "Máy tính bảng Apple ",
                                 " Chính hãng Apple VN", " Chính Hãng Apple VN", "Laptop ",
                                 " Chính hãng Apple Việt Nam", " Chính Hãng Apple Việt Nam", "Đồng hồ thông minh ",
                                 " Chính hãng (VN/A)", " Chính Hãng VN/A", "Tai nghe ", "Phụ kiện ", " Chính hãng",
                                 " Chính Hãng Apple Việt Na", '"-', "''", '"', " -", "(", ")"]

            try:
                product_name_raw = driver.find_element(By.CLASS_NAME, "top-product")
                product_name = product_name_raw.text.replace("Mini", "mini")\
                    .replace(" -", "").replace(
                    "iPhone 13 Pro Max Chính hãng VN/A", "iPhone 13 Pro Max 128GB").replace(
                    "iPhone 13 Pro Chính hãng VN/A", "iPhone 13 Pro 128GB").replace("iPhone 13 Pro Chính hãng VN/A",
                                                                                    "iPhone 13 Pro 128GB").replace(
                    "iPhone 13 Chính hãng VN/A", "iPhone 13 128GB").replace("iPhone 13 Mini Chính hãng VN/A",
                                                                            "iPhone 13 mini 128GB").replace(
                    "Apple iPhone", "iPhone").replace("Mini", "mini").strip()
                # Remove the unwanted words from the product name
                for item in to_remove_in_name:
                    if item in product_name:
                        product_name = product_name.replace(item, "")
                        product_name.strip()
                print(product_name)

                # Gia
                # gia_raw = soup.find_all("p", class_="price current-product-price")
                # gia_raw = driver.find_element(By.XPATH, '//p[@class="price current-product-price"]')
                try:
                    gia_raw = driver.find_element(By.XPATH, "//div[@id='versionOption']/div[@class='item selected']/a")
                    # sometime, this is not a price, but the word "liên hệ"
                    if "h" in gia_raw.text:
                        gia_raw = driver.find_element(By.XPATH, '//p[@class="price current-product-price"]')
                except NoSuchElementException:
                    gia_raw = driver.find_element(By.XPATH, '//p[@class="price current-product-price"]')

                if gia_raw.text != "":
                    try:
                        # gia_niem_yet = gia_raw[0].strike.get_text().strip().replace(",", ".")
                        # gia_khuyen_mai = gia_raw[0].strong.get_text().strip().replace(",", ".")
                        gia_niem_yet = gia_raw.find_element(By.XPATH, "./strike").text.replace("₫", "").replace(".", "").replace(",", "").replace("đ", "")
                        gia_khuyen_mai = gia_raw.find_element(By.XPATH, "./strong").text.replace("₫", "").replace(".", "").replace(",", "").replace("đ", "")
                    # except AttributeError:
                    except NoSuchElementException:
                        gia_niem_yet = gia_raw.find_element(By.XPATH, "./strong").text.replace("₫", "").replace(".", "").replace(",", "").replace("đ", "")
                        gia_khuyen_mai = gia_raw.find_element(By.XPATH, "./strong").text.replace("₫", "").replace(".", "").replace(",", "").replace("đ", "")
                else:
                    gia_niem_yet = f"Please double check online with link: {link}"
                    gia_khuyen_mai = f"Please double check online with link: {link}"

                # Ton kho
                try:
                    # ton_kho_raw = soup.find_all("div", class_="product-action")[0].strong.get_text()
                    ton_kho_raw = driver.find_element(By.XPATH, '(//div[@class="product-action"]/a)[1]/strong').text
                    if "NGAY" in ton_kho_raw:
                        ton_kho = "Yes"
                    else:
                        ton_kho = "No"
                except IndexError:
                # except NoSuchElementException:
                    ton_kho = "not trading"
                    gia_niem_yet = "not trading"
                    gia_khuyen_mai = "not trading"

                # Khuyen mai
                try:
                    # soup.find_all("div", class_="product-promotion")[0].get_text().strip().replace(" - (Xem chi tiết)",
                    #                                                                                "")
                    driver.find_element(By.XPATH, '//div[@class="product-promotion"][1]').text.replace(" - (Xem chi tiết)",
                                                                                                   "")
                except IndexError:
                # except NoSuchElementException:
                    khuyen_mai = f"Please double check online with link: {link}"
                else:
                    # khuyen_mai = soup.find_all("div", class_="product-promotion")[0].get_text().strip().replace(
                    #     " - (Xem chi tiết)", "")
                    khuyen_mai = driver.find_element(By.XPATH, '//div[@class="product-promotion"][1]').text.replace(
                        " - (Xem chi tiết)", "")
                while "    " in khuyen_mai:
                    khuyen_mai.replace("    ", "")

                new_data = {"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                            "Gia_Khuyen_Mai": gia_khuyen_mai, "Date": now, "Khuyen_Mai": khuyen_mai, "Link": link}
                data_list.append(new_data)

            except NoSuchElementException:
                product_name = f"Please double check online with link: {link}"
                print(product_name)
                ton_kho = "No"
                gia_niem_yet = ""
                gia_khuyen_mai = ""
                khuyen_mai = ""
                new_data = {"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                            "Gia_Khuyen_Mai": gia_khuyen_mai, "Date": now, "Khuyen_Mai": khuyen_mai, "Link": link}
                data_list.append(new_data)

        def check_price_dien_thoai():
            try:
                popup=WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@id='popup-modal']/a[2]")))
                driver.execute_script("arguments[0].scrollIntoView(true);", popup)
                driver.execute_script("arguments[0].click();", popup)
                time.sleep(2)
                try:
                    more_offer=WebDriverWait(driver, 2).until(
                        EC.visibility_of_element_located((By.XPATH, "//div[@id='close-button-1545222288830']")))
                    driver.execute_script("arguments[0].scrollIntoView(true);", more_offer)
                    driver.execute_script("arguments[0].click();", more_offer)
                    time.sleep(2)
                except TimeoutException:
                    pass
            except TimeoutException:
                pass

            try:
                cover=driver.find_element(By.XPATH, '//a[@class="close-modal icon-minutes"]')
                cover.click()
                time.sleep(1)
            except NoSuchElementException:
                pass

            # soup = BeautifulSoup(driver.page_source, 'html.parser')
            # product_name_raw = soup.find_all("div", class_="top-product")
            # product_name_raw = driver.find_element(By.CLASS_NAME, "top-product")

            # List of words should be removed
            to_remove_in_name=[" Chính hãng VN/A", "chính hãng VN/A", "Điện thoại di động ", "Máy tính bảng Apple ",
                               " Chính hãng Apple VN", " Chính Hãng Apple VN", "Laptop ",
                               " Chính hãng Apple Việt Nam", " Chính Hãng Apple Việt Nam", "Đồng hồ thông minh ",
                               " Chính hãng (VN/A)", " Chính Hãng VN/A", "Tai nghe ", "Phụ kiện ", " Chính hãng",
                               " Chính Hãng Apple Việt Na", '"-', "''", '"', " -", "(", ")"]

            try:
                product_name_raw=driver.find_element(By.CLASS_NAME, "header-name")
                product_name=product_name_raw.text.replace("Mini", "mini") \
                    .replace(" -", "").replace(
                    "iPhone 13 Pro Max Chính hãng VN/A", "iPhone 13 Pro Max 128GB").replace(
                    "iPhone 13 Pro Chính hãng VN/A", "iPhone 13 Pro 128GB").replace("iPhone 13 Pro Chính hãng VN/A",
                                                                                    "iPhone 13 Pro 128GB").replace(
                    "iPhone 13 Chính hãng VN/A", "iPhone 13 128GB").replace("iPhone 13 Mini Chính hãng VN/A",
                                                                            "iPhone 13 mini 128GB").replace(
                    "Apple iPhone", "iPhone").replace("Mini", "mini").strip()
                # Remove the unwanted words from the product name
                for item in to_remove_in_name:
                    if item in product_name:
                        product_name=product_name.replace(item, "")
                        product_name.strip()
                print(product_name)

                try:
                    gia_khuyen_mai=driver.find_element(By.XPATH, "//strong[@class='price']").text.replace("₫",
                                                                                                          "").replace(
                        ".",
                        "").replace(
                        ",", "").replace("đ", "")
                    gia_niem_yet=gia_khuyen_mai
                except NoSuchElementException:
                    gia_niem_yet=f"Please double check online with link: {link}"
                    gia_khuyen_mai=f"Please double check online with link: {link}"

                # Ton kho
                try:
                    # ton_kho_raw = soup.find_all("div", class_="product-action")[0].strong.get_text()
                    ton_kho_raw=driver.find_element(By.XPATH, "(//div[@class='box-order-btn'])[1]/a/strong").text
                    if "NGAY" in ton_kho_raw:
                        ton_kho="Yes"
                    else:
                        ton_kho="No"
                except NoSuchElementException:
                    ton_kho="No"

                # Khuyen mai
                try:
                    khuyen_mai_s=driver.find_elements(By.XPATH,
                                                    "//div[@class='box-order product-action']/following-sibling::div[position()<=2]")

                    # Extract the HTML content of these elements
                    khuyen_mai_content="".join([khuyen_mai.get_attribute('outerHTML') for khuyen_mai in khuyen_mai_s])

                    # Parse the HTML content with BeautifulSoup
                    khuyen_mai_soup=BeautifulSoup(khuyen_mai_content, 'html.parser')
                    khuyen_mai=khuyen_mai_soup.get_text(separator="\n").replace(" - (Xem chi tiết)", "")
                except IndexError:
                    khuyen_mai=f"Please double check online with link: {link}"

                screenshot_name = screen_shot(product_name)
                new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                          "Gia_Khuyen_Mai": gia_khuyen_mai, "Date": now, "Khuyen_Mai": khuyen_mai, "Link": link,
                          'screenshot_name': screenshot_name}
                data_list.append(new_data)

            except NoSuchElementException:
                product_name=f"Please double check online with link: {link}"
                print(product_name)
                ton_kho="No"
                gia_niem_yet=""
                gia_khuyen_mai=""
                khuyen_mai=""
                screenshot_name=screen_shot(product_name)
                new_data={"Product_Name": product_name, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                          "Gia_Khuyen_Mai": gia_khuyen_mai, "Date": now, "Khuyen_Mai": khuyen_mai, "Link": link,
                          'screenshot_name': screenshot_name}
                data_list.append(new_data)

        self.link_check=link_check
        self.restart_link=restart_link

        for link in self.link_check[self.link_check.index(self.restart_link):]:
            print(link)
            data_list=[]
            try:
                driver.get(link)
                time.sleep(5)
                if ('dien-thoai-di-dong' in link) | ('may-tinh-bang' in link):
                    check_price_dien_thoai()
                else:
                    check_price()
                record()
            except TimeoutException:
                driver.quit()
                print(datetime.now())
                print(f"Start again from link: {link}")
                self.restart_link = link
                self.hh(self.link_check, self.restart_link)

        driver.quit()


link = 'https://hoanghamobile.com/dong-ho-thong-minh/apple-watch-ultra-2-2024-gps-lte-49mm-vo-titan-day-deo-ocean'
index = total_links['hh_urls'].index(link)
user_links = total_links['hh_urls']
HH().hh(link_check=user_links, restart_link=user_links[index])

