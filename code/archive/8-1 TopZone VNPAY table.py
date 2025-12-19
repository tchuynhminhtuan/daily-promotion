import csv
import re
import os
import os.path
from pathlib import *
from datetime import datetime
import pandas
from selenium import webdriver
from Daily_Promotion.code.sites import *
from fake_useragent import UserAgent
from selenium.webdriver.common.action_chains import ActionChains
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

now = datetime.now().date()

# tz_df = pandas.read_csv(f"../output/{now}/2-mw-{now}.csv", delimiter=";", low_memory=False)
tz_df = pandas.read_csv(f"/Users/brucehuynh/Documents/Code_Projects/Daily_Work/Daily_Promotion/output/{now}/8-topzone-{now}.csv", delimiter=";", low_memory=False)

for i, row in tz_df.iterrows():
    tz_item = row.Product_Name
    ton_kho = row.Ton_Kho
    gia_niem_yet = row.Gia_Niem_Yet
    gia_khuyen_mai = row.Gia_Khuyen_Mai.replace(".", "").replace(",", "").replace("đ", "").replace("₫", "").replace("soc", "")
    date = row.Date
    khuyen_mai = row.Khuyen_Mai
    # uu_dai_them = row.Uu_Dai_Them
    link = row.Link


    def vnpay_tz(km_TZ):
        # Check if VNPAYQR is already recorded in Topzone dataframe
        tz_row = tz_df[tz_df.Product_Name == tz_item]
        print(tz_df.Product_Name)
        if int(tz_row.vnpay.to_list()[0]) > 0:
            try:
                # Calculate the total discount amount
                total_discount = int(km_TZ) - int(tz_row.vnpay.to_list()[0])
            except ValueError:
                total_discount = km_TZ

        # If VNPAY is not recorded, check if it's in the promotion note
        else:
            promotion_note = str(tz_row.Khuyen_Mai.to_list()[0]).lower()

            # Convert gia_khuyen_mai to int datatype
            try:
                gia_khuyen_mai = int(tz_row.Gia_Khuyen_Mai.to_list()[0]. \
                                     replace(".", "").replace(",", "").replace("đ", "").replace("₫", "").replace("soc",
                                                                                                                 ""))
            except ValueError:
                print("there is some text in gia_khuyen_mai")
                gia_khuyen_mai = 0

            # We need to handle if the promotion_note having string or null value
            if type(promotion_note) != float:
                if "vnpay" in promotion_note:
                    promotions = promotion_note.split("\n")
                    for promotion in promotions:
                        if "vnpay" in promotion and "%" in promotion:
                            # Calculate the percentage of discount
                            percent_discount = int(promotion[(promotion.index("%") - 2):promotion.index("%")])
                            # if they don't limit the price of product to have VNPAY discount
                            if "đơn hàng từ" not in promotion:
                                max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                # Sometime it use K for 1000 VND, therefore we need to handle
                                max_discount = int(
                                    max_raw_discount[:max_raw_discount.index(" ")].replace(".", "").replace(",",
                                                                                                            "").replace(
                                        "k", "000"))
                            # if they limit the price of product to have VNPAY discount
                            elif "đơn hàng từ" in promotion:
                                condition = int(promotion[(promotion.index("đơn hàng từ") + 12):(
                                    promotion.index("triệu"))]) * 1000000
                                if gia_khuyen_mai >= condition:
                                    max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                    max_discount = int(max_raw_discount[:max_raw_discount.index("k")]) * 1000
                                else:
                                    max_discount = 0

                        elif "vnpay" in promotion and "%" not in promotion:
                            if "đơn hàng từ" not in promotion:
                                try:
                                    max_raw_discount = promotion[(promotion.index("đến") + 3):]

                                except ValueError:
                                    max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                max_discount = int(
                                    max_raw_discount[:max_raw_discount.index("đ")].replace(".", "").replace(",",
                                                                                                            ""))
                            elif "đơn hàng từ" in promotion:
                                condition = int(promotion[(promotion.index("đơn hàng từ") + 12):(
                                    promotion.index("triệu"))]) * 1000000
                                if gia_khuyen_mai >= condition:
                                    try:
                                        max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                    except ValueError:
                                        max_raw_discount=promotion[(promotion.index("ngay") + 5):]
                                    max_discount = int(max_raw_discount[:max_raw_discount.index("k")]) * 1000
                                else:
                                    max_discount = 0
                            percent_discount = 100

                    # Calculate the total discount amount
                    total_discount_1 = int(km_TZ.replace("soc", "")) * ((100 - percent_discount) / 100)
                    total_discount_2 = int(km_TZ.replace("soc", "")) - max_discount
                    total_discount = max(total_discount_1, total_discount_2)
                else:
                    total_discount = km_TZ
            else:
                total_discount = km_TZ
        return total_discount

    def vnpay_mw_table(km):
        # many time, the final price board has .0 at the end, so I need to take this step
        if type(km) == float:
            tt_km_TZ=int(km)
        else:
            tt_km_TZ=km
        oc_vnpay_df=pandas.DataFrame.from_dict(oc_vnpay_dict)
        print(datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_MW}', "%Y-%m-%d").date())
        if now <= datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_MW}', "%Y-%m-%d").date():
            print('yes')
            try:
                for a, b in oc_vnpay_df.iterrows():
                    l=int(
                        b.Range_Low_MW)
                    h=int(
                        b.Range_High_MW)

                    # if the product's revenue is too small, not any VNPay scheme is applied.
                    if int(km) < oc_vnpay_df.iloc[0].Range_Low_MW:
                        tt_km_TZ=km
                        return tt_km_TZ
                    # If it is not too small, move next
                    elif (int(km) >= l) and (int(km) < h):
                        # calculate the amount of VNPAY discount by the amount, not percentage
                        tt_km_TZ=int(km) - int(b.VNPay_Amount_MW)
                        return tt_km_TZ
                    else:
                        pass
            # In some case, the km is just a text
            except ValueError:
                tt_km_TZ = km
        else:
            tt_km_TZ=km

        return tt_km_TZ


    # gia_khuyen_mai_vnpay = vnpay_tz(gia_khuyen_mai)

    print(gia_khuyen_mai)
    gia_khuyen_mai_vnpay = vnpay_mw_table(gia_khuyen_mai)
    print(gia_khuyen_mai_vnpay)

    new_data = {"Product_Name": tz_item, "Ton_Kho": ton_kho, "Gia_Niem_Yet": gia_niem_yet,
                "Gia_Khuyen_Mai": gia_khuyen_mai, "+VNPAY": gia_khuyen_mai_vnpay,
                "Date": now,
                "Khuyen_Mai": khuyen_mai, "link": link
                }


    def record(data_list):
        if not os.path.exists(f"../output/{now}"):
            os.makedirs(f"../output/{now}")

        with open(f"../output/{now}/8-topzone-{now}-VNPAY.csv", "a") as file:
            writer = csv.DictWriter(file,
                                    fieldnames=["Product_Name", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                                                 "+VNPAY", "Date",
                                                "Khuyen_Mai", "Uu_Dai_Them", "link"], delimiter=";")
            if os.stat(f"../output/{now}/8-topzone-{now}-VNPAY.csv").st_size == 0:
                writer.writeheader()
            for row in data_list:
                writer.writerow(row)

    record([new_data])
