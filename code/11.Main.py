import os.path
import pandas
from playsound import playsound
import os
import re
from datetime import datetime
from Daily_Promotion.code.sites import *
from selenium.webdriver.chrome.options import Options
from unidecode import unidecode

day = datetime.now().day
if 4 <= day <= 20 or 24 <= day <= 30:
    suffix = "th"
else:
    suffix = ["st", "nd", "rd"][day % 10 - 1]

now_1 = datetime.now().date().strftime(f"%b %d{suffix} %Y")
options = Options()

# Method 1
now = datetime.now().date()


# Method 2
# date_to_compare = "2024-08-07"
# now = datetime.strptime(date_to_compare, "%Y-%m-%d").date()


# https://pypi.org/project/google-trans-new/
# from google_trans_new import google_translator


class Apple:
    def check(self):
        df = pandas.read_csv(f"../content/{now}/Daily Promo Pricing - {now_1}.csv", delimiter=";")
        list_check = df["Product Name"].to_list()
        print("------\n")
        for i in apple_products:
            if i not in list_check:
                print(f"Not having: {i}")
            check_num = list_check.count(i)
            if check_num > 1:
                print(f"Duplicate: {i}")
        print("------\nAll checked")

    def create_Apple_dashboard_2(self):
        # 1 start fpt
        fpt_df = pandas.read_csv(f"../content/{now}/1-fpt-{now}.csv", delimiter=";")

        fpt_not_trade_list=['Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su', 'iPad Air 10.9 2020 WiFi 64GB',
                            'iPad Air 10.9 2020 WiFi 256GB', 'iPhone 14 Pro Max 128GB', 'iPhone 14 Pro Max 256GB',
                            'iPhone 14 Pro Max 512GB', 'iPad 10.2 2021 WiFi 256GB',
                            'iPhone 14 Pro Max 1TB', 'iPhone 14 Pro 128GB', 'iPhone 14 Pro 256GB',
                            'iPhone 14 Pro 512GB', 'iPhone 14 Pro 1TB',
                            'iPhone 14 Plus 128GB', 'iPhone 14 Plus 256GB', 'iPhone 14 Plus 512GB', 'iPhone 14 128GB',
                            'iPhone 14 256GB', 'iPhone 12 64GB', 'iPhone 12 128GB','iPhone 11 128GB',
                            'iPhone 14 512GB', 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
                            'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su', 'AirPods Pro 2021',
                            'AirTag - 4 Pack', 'AirTag - 1 Pack', 'MacBook Pro 16" 2021 M1 Pro 512GB'
                            'MacBook Pro 14" 2021 M1 Pro 512GB', 'MacBook Pro 16" 2021 M1 Pro 512GB',
                            'MacBook Pro 14" 2021 M1 Pro 512GB', 'iPhone 11 64GB', 'MacBook Pro 16" 2021 M1 Pro 1TB',
                            'iPad Pro 11 2022 M2 WiFi 5G 128GB', 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
                            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
                            'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'MacBook Pro 14" 2021 M1 Pro 1TB',
                            'MacBook Pro 13" 2020 Touch Bar M1 512GB', 'MacBook Air 13" 2020 M1 512GB',
                            'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su', 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
                            'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su', 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su'
                            ]

        fpt_column_names=['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
                           'Khuyen_Mai', 'Thanh_Toan', 'link']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data={'Product_Name': fpt_not_trade_list}
        for col in fpt_column_names[1:]:
            data[col]=['N/A'] * len(fpt_not_trade_list)

        new_fpt=pandas.DataFrame(data, columns = fpt_column_names)
        fpt_df=pandas.concat([new_fpt, fpt_df], ignore_index = True)

        fpt_replacement_dict={
            'AirPods 3 Hộp sạc dây': 'AirPods 3 2021',
            'AirPods Pro 2022': 'AirPods Pro 2 2022',
            'iPad Air 10.9 2022 M1 WiFi 5G 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 10.9 2022 M1 WiFi 5G 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Air 10.9 2022 M1 WiFi 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad Air 10.9 2022 M1 WiFi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',

            'iPad Air 4 2020 10.9 inch WiFi Cellular 64GB': 'iPad Air 10.9 2020 WiFi + Cellular 64GB',
            'iPad Air 4 2020 10.9 inch WiFi Cellular 256GB': 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air 4 2020 10.9 inch WiFi 64GB': 'iPad Air 10.9 2020 WiFi 64GB',
            'iPad Air 4 2020 10.9 inch WiFi 256GB': 'iPad Air 10.9 2020 WiFi 256GB',

            'iPad Gen 9 2021 10.2 inch WiFi Cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad Gen 9 2021 10.2 inch WiFi Cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad Gen 9 2021 10.2 inch WiFi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad Gen 9 2021 10.2 inch WiFi 256GB': 'iPad 10.2 2021 WiFi 256GB',

            'iPad mini 6 2021 8.3 inch WiFi 5G 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad mini 6 2021 8.3 inch WiFi 5G 256GB': 'iPad mini 8.3 2021 WiFi 5G 256GB',
            'iPad mini 6 2021 8.3 inch WiFi 64GB': 'iPad mini 8.3 2021 WiFi 64GB',
            'iPad mini 6 2021 8.3 inch WiFi 256GB': 'iPad mini 8.3 2021 WiFi 256GB',

            'MacBook Pro 16 inch M2 Pro 2023 12CPU 19GPU 16GB/512GB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 inch M2 Pro 2023 12CPU 19GPU 16GB/1TB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 inch M2 Pro 2023 10CPU 16GPU 16GB/512GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 inch M2 Pro 2023 12CPU 19GPU 16GB/1TB': 'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',

            'MacBook Pro 16 inch M1 Pro 2021 10CPU 16GPU 16GB/1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro 16 inch M1 Pro 2021 10CPU 16GPU 16GB/512GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',

            'MacBook Pro 14 inch M1 Pro 2021 10CPU 16GPU 16GB/1TB': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'MacBook Pro 14 inch M1 Pro 2021 10CPU 16GPU 16GB/512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',

            'MacBook Pro 13 inch M2 2022 8CPU 10GPU 8GB/256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 2022 8CPU 10GPU 8GB/512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',

            'MacBook Pro 13 inch M1 2020 8CPU 8GPU 8GB/256GB': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro 13 inch M1 2020 8CPU 8GPU 8GB/512GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',

            'MacBook Air 13 inch M2 2022 8CPU 8GPU 8GB/256GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 2022 8CPU 10GPU 8GB/512GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air M3 13 2024 8CPU 10GPU/8GB/512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M1 2020 8CPU 7GPU 8GB/256GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13 inch M1 2020 8CPU 7GPU 8GB/512GB': 'MacBook Air 13" 2020 M1 512GB',

            'MacBook Pro 14 inch M1 Pro 2021 8CPU 14GPU 16GB/512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'Macbook Pro 14 2021 M1 Pro/16GB/1TB SSD': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'Macbook Pro 16 2021 M1 Pro/16GB/1TB SSD': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro M2 13 2022 8CPU 10GPU 8GB 512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'Macbook Pro 13 2020 Touch Bar M1/8GB/512GB SSD': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air M2 13 2022 8CPU 10GPU 8GB 512GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'Macbook Air 13 2020 M1/8GB/512GB SSD': 'MacBook Air 13" 2020 M1 512GB',
            'AirPods Pro 2023': 'AirPods Pro 2023 USB-C',
            'MacBook Pro M2 13 2022 8CPU 10GPU 8GB 256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'Macbook Pro 13 2020 Touch Bar M1/8GB/256GB SSD': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Air 15 inch M2 2023 8 CPU/10 GPU/8 GB/256 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 M2 2023 8CPU 10GPU/8GB/512GB/Sạc 70W': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Air 15 inch M2 2023 8CPU 10GPU/8GB/512GB/Sạc 70W': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Air 15 inch M3 8GB/512GB (MRYT3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'Máy tính xách tay Macbook Air M2 13 2022 8CPU 8GPU/8GB/256GB Xanh đen MLY33SA/A': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'Máy tính xách tay Macbook Air M2 13 2022 8CPU 8GPU/8GB/256GB Vàng MLY13SA/A': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'Máy tính xách tay Macbook Air M2 13 2022 8CPU 8GPU/8GB/256GB Bạc MLXY3SA/A': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'Máy tính xách tay Macbook Air M2 13 2022 8CPU 8GPU/8GB/256GB Xám MLXW3SA/A': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'Macbook Air 13 2020 M1/8GB/256GB SSD': 'MacBook Air 13" 2020 M1 256GB',
            'AirPods Pro 2': 'AirPods Pro 2 2022',
            'Phụ kiện Apple AirPods 2 hộp sạc dây MV7N2VN/A': 'AirPods 2 hộp sạc dây',
            'AirPods 3 2022 Hộp sạc dây': 'AirPods 3 2021',
        }

        # Convert keys to lowercase using a dictionary comprehension
        fpt_replacement_dict_lower = {key.lower(): value for key, value in fpt_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in fpt_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in fpt_replacement_dict_lower:
                fpt_df.loc[i, "Product_Name"] = fpt_replacement_dict_lower[product_name]

        fpt_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)



        # End FPT

        # 2 start mw
        def clean_column(column):
            pattern=r'₫|\,|soc|\.|đ'  # Define a regex pattern to match '₫', ',', 'soc', '.', and 'đ'
            column=column.astype(str)  # Ensure the column is treated as strings

            # Use regex to replace the specified characters in each element of the column
            column=column.apply(lambda x: re.sub(pattern, '', x))

            return column

        mw_df = pandas.read_csv(f"../content/{now}/2-mw-{now}.csv", delimiter=";", low_memory=False)
        mw_not_trade_list=[
            'MacBook Air 13" 2020 M1 512GB', "Apple Watch SE 2 GPS 40mm viền nhôm dây cao su",
            'AirTag - 4 Pack', 'AirTag - 1 Pack',
            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'iPhone 14 Pro 1TB',
            'iPhone SE 2022 128GB',
            'iPhone 14 Pro Max 1TB',
            'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            'iPad Air 10.9 2020 WiFi + Cellular 64GB', 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16" 2021 M1 Pro 1TB', 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE GPS 40mm viền nhôm dây cao su', 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB'
        ]

        mw_column_names=['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Chien_Gia',
           'Store_Chien', 'Date', 'Khuyen_Mai', 'Uu_Dai_Them', 'link']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data={'Product_Name': mw_not_trade_list}
        for col in mw_column_names[1:]:
            data[col]=['N/A'] * len(mw_not_trade_list)

        new_mw = pandas.DataFrame(data, columns = mw_column_names)
        mw_df = pandas.concat([new_mw, mw_df], ignore_index=True)

        mw_replacement_dict = {
            'iPhone 15 Pro Max 5G 8GB/256GB': 'iPhone 15 Pro Max 256GB',
            'iPhone 15 Pro Max 5G 8GB/512GB': 'iPhone 15 Pro Max 512GB',
            'iPhone 15 Pro Max 5G 8GB/1TB': 'iPhone 15 Pro Max 1TB',
            'iPhone 15 Pro 5G 8GB/128GB': 'iPhone 15 Pro 128GB',
            'iPhone 15 Pro 5G 8GB/256GB': 'iPhone 15 Pro 256GB',
            'iPhone 15 Pro 5G 8GB/512GB': 'iPhone 15 Pro 512GB',
            'iPhone 15 Pro 5G 8GB/1TB': 'iPhone 15 Pro 1TB',
            'iPhone 15 Plus 5G 6GB/128GB': 'iPhone 15 Plus 128GB',
            'iPhone 15 Plus 5G 6GB/256GB': 'iPhone 15 Plus 256GB',
            'iPhone 15 Plus 5G 6GB/512GB': 'iPhone 15 Plus 512GB',
            'iPhone 15 5G 6GB/128GB': 'iPhone 15 128GB',
            'iPhone 15 5G 6GB/256GB': 'iPhone 15 256GB',
            'iPhone 14 Pro Max 5G 6GB/128GB': 'iPhone 14 Pro Max 128GB',
            'iPhone 14 Pro Max 5G 6GB/256GB': 'iPhone 14 Pro Max 256GB',
            'iPhone 14 Pro Max 5G 6GB/512GB': 'iPhone 14 Pro Max 512GB',
            'iPhone 14 Pro Max 5G 6GB/1TB': 'iPhone 14 Pro Max 1TB',
            'iPhone 14 Plus 5G 6GB/128GB': 'iPhone 14 Plus 128GB',
            'iPhone 14 Plus 5G 6GB/256GB': 'iPhone 14 Plus 256GB',
            'iPhone 14 5G 6GB/256GB': 'iPhone 14 256GB',
            'iPhone 13 5G 4GB/256GB': 'iPhone 13 256GB',
            'iPhone 12 5G 4GB/128GB': 'iPhone 12 128GB',
            'iPhone 12 5G 4GB/256GB': 'iPhone 12 256GB',
            'iPhone 14 5G 6GB/128GB': 'iPhone 14 128GB',
            'iPhone 13 5G 4GB/128GB': 'iPhone 13 128GB',
            'iPhone 12 5G 4GB/64GB': 'iPhone 12 64GB',
            'iPhone 11 4GB/128GB': 'iPhone 11 128GB',
            'iPhone 11 4GB/64GB': 'iPhone 11 64GB',
            'iPhone SE 64GB (2022)': 'iPhone SE 2022 64GB',
            'iPhone SE 128GB (2022)': 'iPhone SE 2022 128GB',
            'iPhone SE 256GB (2022)': 'iPhone SE 2022 256GB',

            'iPad Pro M4 13 inch 5G 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch 5G 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch WiFi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch WiFi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch 5G 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch 5G 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch WiFi 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch WiFi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air 6 M2 13 inch 5G 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13 inch 5G 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 inch WiFi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13 inch WiFi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 inch 5G 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 inch 5G 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11 inch WiFi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch WiFi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            'iPad Pro M2 12.9 inch 5G 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 inch WiFi 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9 inch WiFi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 inch WiFi Cellular 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 inch WiFi Cellular 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 inch WiFi 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro M2 11 inch WiFi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad 10 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',

            'iPad 10 WiFi Cellular 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 WiFi + Cellular 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 WiFi Cellular 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 WiFi + Cellular 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',

            'iPad 10 WiFi 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad 10 WiFi 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'iPad Pro M1 12.9 inch WiFi Cellular 128GB (2021)': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro M1 12.9 inch WiFi Cellular 256GB (2021)': 'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
            'iPad Pro M1 12.9 inch WiFi 128GB (2021)': 'iPad Pro 12.9 2021 M1 WiFi 128GB',
            'iPad Pro M1 12.9 inch WiFi 256GB (2021)': 'iPad Pro 12.9 2021 M1 WiFi 256GB',
            'iPad Pro M1 11 inch WiFi Cellular 128GB (2021)': 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            'iPad Pro M1 11 inch WiFi Cellular 256GB (2021)': 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
            'iPad Pro M1 11 inch WiFi 128GB (2021)': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'iPad Pro M1 11 inch WiFi 256GB (2021)': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'iPad Air 5 M1 5G 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 M1 WiFi Cellular 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 M1 WiFi Cellular 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Air 5 M1 WiFi 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad Air 5 M1 Wifi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'iPad Air 4 Wifi Cellular 64GB (2020)': 'iPad Air 10.9 2020 WiFi + Cellular 64GB',
            'iPad Air 4 Wifi Cellular 256GB (2020)': 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air 4 Wifi 64GB (2020)': 'iPad Air 10.9 2020 WiFi 64GB',
            'iPad Air 4 Wifi 256GB (2020)': 'iPad Air 10.9 2020 WiFi 256GB',
            'iPad 9 4G 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 WiFi Cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 4G 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 WiFi Cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 WiFi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad 9 WiFi 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'iPad mini 6 5G 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad mini 6 WiFi Cellular 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad mini 6 WiFi Cellular 256GB': 'iPad mini 8.3 2021 WiFi 5G 256GB',
            'iPad mini 6 WiFi 64GB': 'iPad mini 8.3 2021 WiFi 64GB',
            'iPad mini 6 WiFi 256GB': 'iPad mini 8.3 2021 WiFi 256GB',
            'MacBook Pro 14 inch M3 8GB/512GB (MR7J3SA/A)': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 8GB/512GB (MTL73SA/A)': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 2023 8-core CPU/8GB/512GB/10-core GPU': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 2023 8-core CPU/8GB/512GB/10-core GPU (MTL73SA/A)' : 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 8GB/1TB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 inch M3 2023 8-core CPU/8GB/1TB/10-core GPU': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 inch M3 Pro 18GB/512GB': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 inch M3 Pro 2023 11-core CPU/18GB/512GB/14-core GPU': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 inch M3 Pro 2023 12-core CPU/18GB/1TB/18-core GPU': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 inch M3 Pro 18GB/512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Pro 16 inch M3 Pro 2023 12-core CPU/18GB/512GB/18-core GPU': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Air 15 inch M3 8GB/256GB (MRYU3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air 15 inch M3 8GB/256GB (MRYR3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air 15 inch M3 8GB/256GB (MRYP3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air 15 inch M3 8GB/256GB (MRYM3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air 15 inch M3 8GB/512GB (MRYN3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 15 inch M3 8GB/512GB (MRYT3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 15 inch M3 8GB/512GB (MRYV3SA/A)': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M3 8GB/256GB (MRXV3SA/A)': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air 13 inch M3 8GB/256GB (MRXN3SA/A)': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air 13 inch M3 8GB/512GB (MRXU3SA/A)': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M3 8GB/512GB (MRXW3SA/A)': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M3 8GB/512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M1 2020 8-core CPU/8GB/256GB/7-core GPU (MGND3SA/A)': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13 inch M1 8GB/256GB (MGN63SA/A)': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 15 inch M2 8GB/256GB Sạc 35W (MQKW3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 8GB/256GB Sạc 35W (MQKP3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU/35W (MQKW3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU/35W (MQKR3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU (MQKR3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU (MQKU3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU (MQKP3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8-core CPU/8GB/256GB/10-core GPU (MQKW3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 8GB/512GB (MQKX3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Air 15 inch M2 8GB/512GB (MQKV3SA/A)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'Laptop MacBook Air 15 inch M2 2023 8CPU/8GB/512GB/10GPU (MQKX3SA/A)' : 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'Laptop MacBook Air 15 inch M2 2023 8CPU/8GB/512GB/10GPU (MQKQ3SA/A)' : 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Pro 16 inch M2 Pro 2023 12-core CPU/16GB/512GB/19-core GPU (MNW83SA/A)': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 14 inch M2 Pro 2023 10-core CPU/16GB/512GB/16-core GPU (MPHE3SA/A)': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 16 inch M1 Pro 2021 10 core-CPU/16GB/512GB/16 core-GPU (MK183SA/A)': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro 16 inch M1 Pro 2021 10-core CPU/16GB/1TB/16-core GPU (MK193SA/A)': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'Laptop MacBook Pro 14 M1 Pro 2021 8-core CPU/16GB/512GB/14-core GPU (MKGP3SA/A)': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro 14 inch M1 Pro 2021 10-core CPU/16GB/1TB SSD/16-core GPU (MKGQ3SA/A)': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'MacBook Pro 13 inch M2 2022 8-core CPU/8GB/256GB/10-core GPU (MNEH3SA/A)': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 2022 8-core CPU/8GB/256GB/10-core GPU (MNEP3SA/A)': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 2022 8-core CPU/8GB/512GB/10-core GPU (MNEJ3SA/A)': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 8GB/256GB (MLY33SA/A)': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 8GB/256GB (MLY13SA/A)': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/256GB/8-core GPU (MLY13SA/A)': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/256GB/8-core GPU (MLXY3SA/A)': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 8GB/512GB/10GPU (Z15S006TY)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 8GB/512GB/10GPU (Z160009HD)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/512GB/10-core GPU (Z160009HD)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/512GB/10-core GPU (MLY43SA/A)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/512GB/10-core GPU (Z15S006TY)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro M1 2020 8GB/256GB (MYD82SA/A)': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro M1 2020 8GB/512GB (MYDC2SA/A)': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air 13 inch M1 2020 8-core CPU/8GB/256GB/7-core GPU (MGN63SA/A)': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13 inch M2 2022 8-core CPU/8GB/256GB/8-core GPU (MLXW3SA/A)' : 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air M1 2020 8GB/512GB/8-core GPU (MGN73SA/A)': 'MacBook Air 13" 2020 M1 512GB',
            'Đồng hồ thông minh Apple Watch Ultra 2 LTE 49mm viền Titanium dây Ocean': 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Đồng hồ thông minh Apple Watch Ultra 2 GPS + Cellular 49mm viền Titanium dây Ocean': 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Đồng hồ thông minh Apple Watch S9 LTE 41mm viền nhôm dây silicone': 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch Series 9 GPS + Cellular 41mm viền nhôm dây thể thao': 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch S9 LTE 45mm viền nhôm dây silicone dây ngắn': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch Series 9 GPS + Cellular 45mm viền nhôm dây thể thao': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch Series 9 GPS + Cellular 45mm viền nhôm dây thể thao size S/M': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch S9 GPS 41mm viền nhôm dây silicone': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch Series 9 GPS 41mm viền nhôm dây thể thao': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch S9 GPS 45mm viền nhôm dây silicone dây ngắn': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Đồng hồ thông minh Apple Watch Series 9 GPS 45mm viền nhôm dây thể thao size S/M': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'AirPods Pro Gen 2 MagSafe Charge (USB-C) Apple MTJV3': 'AirPods Pro 2023 USB-C',
            'Đồng hồ thông minh Apple Watch S8 LTE 45mm': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây thể thao': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch S8 LTE 41mm': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây thể thao': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch S8 GPS 45mm': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch Series 8 GPS 45mm viền nhôm dây thể thao': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch S8 GPS 41mm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch Series 8 GPS 41mm viền nhôm dây thể thao': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',

            'Đồng hồ thông minh Apple Watch SE 2022 LTE 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS + Cellular 44mm viền nhôm dây thể thao': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 LTE 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS + Cellular 40mm viền nhôm dây thể thao': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS 44mm viền nhôm dây thể thao': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch SE 2022 GPS 40mm viền nhôm dây thể thao': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',

            'Apple Watch S3 GPS 42mm viền nhôm dây silicone': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Đồng hồ thông minh Apple Watch S3 GPS 38mm viền nhôm dây silicone': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',

            'Chụp Tai AirPods Max Apple': 'AirPods Max',
            'AirPods Pro (2nd Gen) MagSafe Charge (Lightning) Apple MQD83': 'AirPods Pro 2 2022',
            'AirPods Pro (2nd Gen) MagSafe Charge Apple MQD83': 'AirPods Pro 2 2022',
            'AirPods Pro MagSafe Charge Apple MLWK3': 'AirPods Pro 2021',
            'AirPods 3 Lightning Charge Apple MPNY3': 'AirPods 3 2021',
            'AirPods 2 Lightning Charge Apple MV7N2': 'AirPods 2 hộp sạc dây',
        }

        # Convert keys to lowercase using a dictionary comprehension
        mw_replacement_dict_lower = {key.lower(): value for key, value in mw_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in mw_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in mw_replacement_dict_lower:
                mw_df.loc[i, "Product_Name"] = mw_replacement_dict_lower[product_name]

        mw_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        mw_df['Gia_Khuyen_Mai']=clean_column(mw_df['Gia_Khuyen_Mai'])

        # End MW

        # 3 start hh
        hh_df = pandas.read_csv(f"../content/{now}/3-hh-{now}.csv", delimiter=";")
        hh_not_trade_list = [
            'Điện thoại iPhone 14 128GB',
        'iPhone 14 Pro Max 128GB', 'iPhone 14 Pro Max 256GB', 'iPhone 14 Pro 128GB', 'iPhone 14 Pro 256GB',
        'Điện thoại iPhone 14 256GB',
            'iPhone 13 256GB', 'iPhone 14 Plus 256GB',
        'iPhone SE 2022 256GB', 'iPhone 13 mini 128GB', 'iPhone 13 mini 256GB',
        'iPad Pro 12.9 2022 M2 WiFi 5G 256GB', 'iPad 10.2 2021 WiFi + Cellular 64GB',
        'iPad Pro 12.9 2021 M1 WiFi 5G 256GB', 'iPad Pro 12.9 2021 M1 WiFi 5G 512GB',
        'iPad Pro 11 2021 M1 WiFi 5G 256GB', 'iPad Pro 11 2021 M1 WiFi 5G 512GB',
        'iPad Pro 11 2021 M1 WiFi 256GB', 'iPad Pro 11 2021 M1 WiFi 512GB',
        'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB', 'iPad Air 10.9 2020 WiFi 256GB',
        'iPad mini 8.3 2021 WiFi 5G 256GB', 'iPad mini 8.3 2021 WiFi 256GB',
        'MacBook Pro 16" 2021 M1 Pro 1TB',
        'MacBook Pro 13" 2020 Touch Bar M1 256GB', 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
        'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
        'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su', 'iPhone 13 Pro Max 128GB',
        'iPhone 13 Pro Max 256GB', 'iPhone 13 Pro Max 512GB', 'iPhone 13 Pro Max 1TB',
        'iPhone 13 Pro 128GB', 'iPhone 13 Pro 256GB', 'iPad Air 10.9 2020 WiFi 64GB', 'AirPods Max',
        'iPhone SE 2022 64GB', 'iPhone SE 2022 128GB', 'iPhone 13 512GB', 'AirPods 3 2021',
        'MacBook Pro 14" 2021 M1 Pro 1TB', 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
        'iPhone 14 Pro Max 512GB', 'iPhone 14 Pro Max 1TB', 'iPhone 14 Pro 512GB',
        'iPhone 14 Pro 1TB',
        'iPhone 14 Plus 512GB', 'iPhone 14 512GB', 'AirTag - 4 Pack', 'AirTag - 1 Pack',
        'iPad 10.2 2021 WiFi + Cellular 256GB', 'iPad Pro 12.9 2022 M2 WiFi 128GB',
        'MacBook Air 13" 2020 M1 512GB',
        'MacBook Pro 16" 2021 M1 Pro 512GB', 'AirPods Pro 2021', 'AirPods Pro 2 2022',
        'iPhone 14 Plus 512GB', 'iPhone 14 512GB', 'iPhone 13 512GB',
        'iPad Pro 11 2022 M2 WiFi 5G 256GB', 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
        'MacBook Pro 14" 2021 M1 Pro 512GB', 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
        'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'iPad Pro 12.9 2022 M2 WiFi 5G 128GB', 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro 11 2022 M2 WiFi 128GB', 'iPad Pro 11 2022 M2 WiFi 256GB',
            'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB'
        ]

        hh_column_names=['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
                         'Khuyen_Mai', 'Link']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data={'Product_Name': hh_not_trade_list}
        for col in hh_column_names[1:]:
            data[col] = ['N/A'] * len(hh_not_trade_list)

        hh_new = pandas.DataFrame(data, columns = hh_column_names)
        hh_df = pandas.concat([hh_new, hh_df], ignore_index = True)

        hh_replacement_dict = {
            'iPhone 14 Pro Max': 'iPhone 14 Pro Max 128GB',
            'iPhone 14 Pro': 'iPhone 14 Pro 128GB',
            'iPhone 14 Plus': 'iPhone 14 Plus 128GB',
            'iPhone 14': 'iPhone 14 128GB',

            'iPad Pro M4 13 5G 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 5G 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 Wifi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 Wifi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 5G 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 5G 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 Wifi 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 Wifi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air 6 M2 13 5G 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13 5G 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 Wifi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13 Wifi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 5G 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 5G 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11 Wifi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 Wifi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            'Máy tính bảng iPad Pro M2 12.9 5G 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'Máy tính bảng iPad Pro M2 12.9 5G 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'Máy tính bảng iPad Pro M2 12.9 Wi-Fi 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'Máy tính bảng iPad Pro M2 12.9 Wi-Fi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'Máy tính bảng iPad Pro M2 11 5G 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'Máy tính bảng iPad Pro M2 11 5G 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'Máy tính bảng iPad Pro M2 11 Wi-Fi 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'Máy tính bảng iPad Pro M2 11 Wi-Fi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'Máy tính bảng iPad Gen 10 10.9 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'Máy tính bảng iPad Gen 10 10.9 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'Máy tính bảng iPad Gen 10 10.9 Wi-Fi 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'Máy tính bảng iPad Gen 10 10.9 Wi-Fi 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',

            'Apple iPad Air 5 M1 10.9 2022 5G 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 M1 10.9 2022 5G 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'Apple iPad Air 5 M1 10.9 2022 Wifi 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'Apple iPad Air 5 M1 10.9 2022 Wifi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',

            'Máy tính bảng iPad Gen 9 10.2 4G 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'Máy tính bảng iPad Gen 9 10.2 4G 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'Máy tính bảng iPad Gen 9 10.2 Wi-Fi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'Máy tính bảng iPad Gen 9 10.2 Wi-Fi 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'Máy tính bảng iPad mini 6 8.3 5G 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            # 'iPad mini 6 8.3 2021 5G 256GB': 'iPad mini 8.3 2021 WiFi 5G 256GB',
            'Máy tính bảng iPad mini 6 8.3 Wi-Fi 64GB': 'iPad mini 8.3 2021 WiFi 64GB',
            # 'iPad mini 6 8.3 2021 Wifi 256GB': 'iPad mini 8.3 2021 WiFi 256GB',

            'MacBook Pro 14 M3/8-core CPU/10-core GPU/8GB/512GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 M3/8-core CPU/10-core GPU/8GB/1TB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 M3 Pro/11‑core CPU/14‑core GPU/18GB/512GB': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 M3 Pro/12‑core CPU/18‑core GPU/18GB/1TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 M3 Pro/12‑core CPU/18‑core GPU/18GB/512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

            'Apple Watch Ultra 2 GPS + LTE, 49mm Vỏ Titan Dây Đeo Ocean': 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'MacBook Air M2 15 8GB/256GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air M2 15 8GB/512GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Pro 16 M2 Pro/12-core CPU/19-core GPU/16GB/512GB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 M2 Pro/12-core CPU/19-core GPU/16GB/1TB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 M2 Pro/10-core CPU/16-core GPU/16GB/512GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 M2 Pro/12-core CPU/19-core GPU/16GB/1TB': 'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'Pro 16 M1 Pro/10-core CPU/16-core GPU/16GB/512GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'Macbook Pro 16 2021 M1 Pro 16 Core GPU/1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro 14 M1 Pro/8-core CPU/14-core GPU/16GB/512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro M2 13 8GB/256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro M2 13 8GB/512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air M2 13.6 8GB/256GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air M2 13.6 8GB/512GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro M1 13 8GB/256GB': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro M1 13 8GB/512GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air M3 15 8GB/256GB Apple Việt Nam': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air M3 15 8GB/256GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air M3 15 8GB/512GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air M3 13 8GB/256GB': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air M3 13 8GB/512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

            'MacBook Air M1 13 8GB/256GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air M1 13 8GB/512GB': 'MacBook Air 13" 2020 M1 512GB',
            'Apple Watch Series 8 GPS + Cellular, 45mm Viền nhôm dây cao su VN/A': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS + Cellular, 41mm Viền nhôm dây cao su VN/A': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 45mm Viền nhôm dây cao su VN/A': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 41mm Viền nhôm dây cao su VN/A': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS + LTE, 44mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS + LTE, 40mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS, 44mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS, 40mm Vỏ Nhôm Dây Cao Su': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS, 42mm Vỏ Nhôm Dây Cao Su': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 42mm': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 38mm': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            "airpods max" : "AirPods Max",
            'AirPods Pro 2 với Hộp Sạc MagSafe Lightning': "AirPods Pro 2 2022",
            'AirPods Pro với Hộp Sạc MagSafe': 'AirPods Pro 2021',
            'Apple AirPods 3' : 'AirPods 3 2021',
            'AirPods 2 với Hộp Sạc Lightning' : 'AirPods 2 hộp sạc dây',
            'Apple Watch Ultra 2 GPS + LTE, 49mm Vỏ Titan Dây Đeo Ocean VN/A' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 GPS + LTE, 41mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS + LTE, 45mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS, 41mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS, 45mm Vỏ Nhôm Dây Cao Su' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'AirPods Pro 2 với Hộp Sạc MagSafe USB-C' : 'AirPods Pro 2023 USB-C'
        }

        # Convert keys to lowercase using a dictionary comprehension
        hh_replacement_dict_lower = {key.lower(): value for key, value in hh_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in hh_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in hh_replacement_dict_lower:
                hh_df.loc[i, "Product_Name"] = hh_replacement_dict_lower[product_name]

        hh_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End HH

        # 4 start ddv
        def to_str(val):
            return str(val)
        ddv_df = pandas.read_csv(f"../content/{now}/4-ddv-{now}.csv", delimiter=";", converters={"Gia_Khuyen_Mai": to_str})

        ddv_not_trade_list = ['iPad mini 8.3 2021 WiFi 256GB',
            'iPad Pro 12.9 2021 M1 WiFi 5G 256GB', 'iPad Pro 12.9 2021 M1 WiFi 256GB',
                            'iPad Pro 11 2021 M1 WiFi 5G 128GB', 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
                            'iPad Pro 11 2021 M1 WiFi 256GB',
                            'MacBook Pro 13" 2020 Touch Bar M1 256GB',
                            'MacBook Pro 16" 2021 M1 Pro 512GB', 'MacBook Pro 14" 2021 M1 Pro 512GB',
                            'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
                            'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
                            'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su', 'AirTag - 1 Pack',
                            'iPhone SE 2022 64GB',
                            'iPhone SE 2022 128GB', 'iPhone SE 2022 256GB', 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
                            'iPad Pro 12.9 2021 M1 WiFi 5G 128GB', 'iPad Pro 12.9 2021 M1 WiFi 128GB',
                            'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
                            'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
                            'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB', 'MacBook Air 13" 2020 M1 512GB',
                            'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
                            'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
                            'iPad Pro 11 2022 M2 WiFi 5G 256GB', 'AirPods Pro 2023 USB-C',
                            'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su', "Apple Watch Series 8 GPS 45mm viền nhôm dây cao su",
                              'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
                              'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
                              'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
                            'iPad Pro 11 2022 M2 WiFi 5G 128GB'
                              ]

        ddv_column_names = ['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date', 'Khuyen_Mai']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data = {'Product_Name': ddv_not_trade_list}
        for col in ddv_column_names[1:]:
            data[col] = ['N/A'] * len(ddv_not_trade_list)

        ddv_new = pandas.DataFrame(data, columns = ddv_column_names)
        ddv_df = pandas.concat([ddv_new, ddv_df], ignore_index = True)

        ddv_replacement_dict = {
            'iPhone SE 3 64GB': 'iPhone SE 2022 64GB',
            'iPhone SE 3 128GB': 'iPhone SE 2022 128GB',
            'iPhone SE 3 256GB': 'iPhone SE 2022 256GB',

            'iPad Pro M4 13 inch | 256GB Wifi & 5G': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch | 512GB Wifi & 5G': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch | 256GB Wifi': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch | 512GB Wifi': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch | 256GB Wifi & 5G': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch | 512GB Wifi & 5G': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch | 256GB Wifi': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch | 512GB Wifi': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air 6 M2 13 inch | 128GB Wifi & 5G': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13 inch | 256GB Wifi & 5G': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 inch | 128GB Wifi': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13 inch | 256GB Wifi': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 inch | 128GB Wifi & 5G': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 inch | 256GB Wifi & 5G': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11 inch | 128GB Wifi': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch | 256GB Wifi': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            'iPad Pro M2 12.9-inch (2022) | 128GB 5G': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9-inch (2022) | 256GB 5G': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9-inch (2022) | 128GB Wifi': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9-inch (2022) | 256GB Wifi': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11-inch (2022) | 128GB 5G': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11-inch (2022) | 256GB 5G': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11-inch (2022) | 128GB Wifi': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro M2 11-inch (2022) | 256GB Wifi': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad 10.9-inch 2022 | 64GB 5G': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10.9-inch 2022 | 256GB 5G': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10.9-inch 2022 | 64GB Wifi': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad 10.9-inch 2022 | 256GB Wifi': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'iPad Pro 12.9-inch 2021 | M1 128GB Wifi & 5G': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro 12.9 2021 M1 WiFi 5G 256GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
            'iPad Pro 12.9-inch 2021 | M1 128GB Wifi': 'iPad Pro 12.9 2021 M1 WiFi 128GB',
            'iPad Pro 12.9 2021 M1 WiFi 256GB': 'iPad Pro 12.9 2021 M1 WiFi 256GB',
            'iPad Pro 11 2021 M1 WiFi 5G 128GB': 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            'iPad Pro 11 2021 M1 WiFi 5G 256GB': 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
            'iPad Pro 11-inch 2021 | M1 128GB Wifi': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'iPad Pro 11 2021 M1 WiFi 256GB': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'iPad Air 5 2022 | M1 64GB Wifi & 5G': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 2022 | M1 256GB Wifi & 5G': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Air 5 2022 | M1 64GB Wifi': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad Air 5 2022 | M1 256GB Wifi': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'iPad Air 4 (2020) 64GB Wifi & 4G': 'iPad Air 10.9 2020 WiFi + Cellular 64GB',
            'iPad Air 4 (2020) 256GB Wifi & 4G': 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air 4 2020 | 64GB Wifi': 'iPad Air 10.9 2020 WiFi 64GB',
            'iPad Air 4 (2020) 256GB Wifi': 'iPad Air 10.9 2020 WiFi 256GB',
            'iPad Gen 9 2021 | Wifi & 4G 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad Gen 9 2021 | Wifi & 4G 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad Gen 9 2021 | Wifi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad Gen 9 2021 | Wifi 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'iPad Mini 6 2021 | 64GB Wifi & 5G': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad Mini 6 2021 | 256GB Wifi & 5G': 'iPad mini 8.3 2021 WiFi 5G 256GB',
            'iPad Mini 6 2021 | 64GB Wifi': 'iPad mini 8.3 2021 WiFi 64GB',
            'iPad Mini 6 2021 | 256GB Wifi': 'iPad mini 8.3 2021 WiFi 256GB',
            'iPad Pro M2 12.9 5G 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 5G 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 Wi-Fi 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9 Wi-Fi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 5G 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 5G 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 Wi-Fi 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro M2 11 Wi-Fi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Gen 10 10.9 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad Gen 10 10.9 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad Gen 10 10.9 Wi-Fi 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad Gen 10 10.9 Wi-Fi 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'MacBook Pro M3 14 inch 8GB/512GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro M3 14 inch 2023 | 8GB/512GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro M3 14 inch 8GB/1TB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro M3 14 inch 2023 | 8GB/1TB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro M3 Pro 14 inch 18GB/512GB': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro M3 Pro 14 inch 2023 | 18GB/512GB': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro M3 Pro 14 inch 2023 | 18GB/1TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro M3 Pro 16 inch 18GB/512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Pro M3 Pro 16 inch 2023 | 18GB/512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

            'MacBook Air M3 15 inch 8GB/256GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air M3 15 inch 8GB/512GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air M3 13 inch 8GB/256GB': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air M3 13 inch 8GB/512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

            'MacBook Air M2 15 inch 8GB/256GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air M2 15-inch 2023 | 8GB/256GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air M2 15-inch 2023 | 8GB/512GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Pro M2 Pro 16 inch 2023 | 16GB/512GB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 inch M2 Pro 16GB/1TB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 16 inch M2 Pro 2023 | 16GB/1TB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro M2 Pro 14 inch 2023 | 16GB/512GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro M2 Pro 14 inch 16GB/512GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 inch M2 Pro 2023 | 16GB/1TB': 'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'Macbook Pro 16-inch 2021 | M1 Pro 16GB/512GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro M1 Pro 16 inch 16GB/1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro 16-inch 2021 | M1 Pro 16GB/1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'Macbook Pro 14-inch 2021 | M1 Pro 16GB/512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'Macbook Pro 14-inch 2021 | M1 Pro 16GB/1TB': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'MacBook Pro M2 13 inch 8GB/256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13-inch 2022 | M2 8GB/256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13-inch 2022 | M2 8GB/512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air M2 13 inch 8GB/256GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air M2 13-inch 2022 | 8GB/256GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MACBOOK AIR 2022 13.6" M2 8-Core CPU/10-Core GPU 8GB/512GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro 13-inch 2020 | M1 8GB/256GB': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro 13-inch 2020 | M1 8GB/512GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air M1 13 inch 8GB/256GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air M1 2020 13 inch | 8GB/256GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13-inch 2020 | M1 8GB/512GB': 'MacBook Air 13" 2020 M1 512GB',
            'Apple Watch Series 8 45mm (LTE) Viền nhôm - Dây cao su': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm (LTE) Viền nhôm - Dây cao su': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 45mm (GPS) Dây cao su': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm (GPS) Viền nhôm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE 2 (2022) 44mm (LTE) Viền nhôm - Dây cao su': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2 (2022) 40mm (LTE) Viền nhôm - Dây cao su': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 2 (2022) 44mm (GPS) Viền nhôm - Dây cao su': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2 (2022) 40mm (GPS) Viền nhôm - Dây cao su': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch SE 44mm (4G) viền nhôm bạc - Dây vải thun': 'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 40mm (4G) viền nhôm bạc - Dây vải thun': 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 44mm (4G) viền nhôm bạc - Dây cao su': 'Apple Watch SE GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 40mm (GPS) viền nhôm xám - Dây cao su': 'Apple Watch SE GPS 40mm viền nhôm dây cao su',
            'Airpods Max': 'AirPods Max',
            'Airpods Pro 2 2022': 'AirPods Pro 2 2022',
            'Airpods Pro': 'AirPods Pro 2021',
            'Tai nghe Apple AirPods 3': 'AirPods 3 2021',
            'Tai nghe Apple AirPods 2  (No Wireless Charge)': 'AirPods 2 hộp sạc dây',
            'Apple AirTag Combo 4 cái': 'AirTag - 4 Pack',
            'Apple AirTag': 'AirTag - 1 Pack',
            'Apple Watch Ultra 2 49mm (LTE) Viền Titan - Dây Ocean' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 41mm (LTE) Viền nhôm - Dây cao su size S/M' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 45mm (LTE) Viền nhôm - Dây cao su size S/M' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 41mm (GPS) Viền nhôm - Dây quấn thể thao': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 41mm (GPS) Viền nhôm - Dây cao su size S/M' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 45mm (GPS) Viền nhôm - Dây cao su size S/M' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            # '' : 'AirPods Pro 2023 USB-C'

        }

        # Convert keys to lowercase using a dictionary comprehension
        ddv_replacement_dict_lower = {key.lower(): value for key, value in ddv_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in ddv_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in ddv_replacement_dict_lower:
                ddv_df.loc[i, "Product_Name"] = ddv_replacement_dict_lower[product_name]

        ddv_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End Didongviet

        # 5 start vt
        vt_df = pandas.read_csv(f"../content/{now}/5-vt-{now}.csv", delimiter=";")
        vt_not_trade_list=[
            'iPhone 12 64GB',
            'iPhone 14 Pro 512GB', 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'iPhone 14 Pro Max 512GB', 'iPhone 14 Pro Max 128GB',
            'iPhone 13 512GB', 'iPhone 13 mini 512GB', 'iPhone SE 64GB', 'iPhone SE 128GB',
            'iPhone XR 128GB', 'iPhone 14 Pro 256GB', 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Pro 12.9 2021 M1 WiFi 256GB', 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air 10.9 2020 WiFi 256GB', 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Pro 16" 2021 M1 Pro 1TB', 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro 14" 2021 M1 Pro 1TB', 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro 13" 2020 Touch Bar M1 512GB', 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13" 2020 M1 512GB', 'Apple Watch Series 3 GPS 42mm', 'Beats Studio Buds',
            'iPad Pro 11 2021 M1 WiFi 256GB', 'iPhone SE 2022 256GB',
            'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB', 'iPad 10.2 2021 WiFi 64GB',
            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'AirPods Max', 'AirPods Pro 2021', 'iPad Pro 11 2022 M2 WiFi 5G 128GB'
                           ]

        vt_column_names=['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
                         'Khuyen_Mai']
        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data={'Product_Name': vt_not_trade_list}
        for col in vt_column_names[1:]:
            data[col]=['N/A'] * len(vt_not_trade_list)

        vt_new = pandas.DataFrame(data, columns = vt_column_names)
        vt_df = pandas.concat([vt_new, vt_df], ignore_index = True)

        # vt_row_to_drop=[]
        # vt_product_list=vt_df['Product_Name'].to_list()

        vt_replacement_dict = {
            "iPhone SE (2022) 64GB": "iPhone SE 2022 64GB",
            "iPhone SE (2022) 128GB": "iPhone SE 2022 128GB",

            'iPad Pro M4 13 inch Standard Glass WiFi 5G 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch Standard Glass WiFi 5G 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch Standard Glass WiFi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch Standard Glass WiFi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch Standard Glass WiFi 5G 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch Standard Glass WiFi 5G 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch Standard Glass WiFi 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch Standard Glass WiFi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air (Gen 6) M2 13 inch WiFi 5G 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air (Gen 6) M2 13 inch WiFi 5G 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air (Gen 6) M2 13 inch WiFi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air (Gen 6) M2 13 inch WiFi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air (Gen 6) M2 11 inch WiFi 5G 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air (Gen 6) M2 11 inch WiFi 5G 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air (Gen 6) M2 11 inch WiFi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air (Gen 6) M2 11 inch WiFi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            "iPad Pro 12.9 (2022) WiFi 5G 128GB": "iPad Pro 12.9 2022 M2 WiFi 5G 128GB",
            "iPad Pro 12.9 (2022) WiFi 5G 256GB": "iPad Pro 12.9 2022 M2 WiFi 5G 256GB",
            "iPad Pro 12.9 (2022) WiFi 128GB": "iPad Pro 12.9 2022 M2 WiFi 128GB",
            "iPad Pro 12.9 (2022) WiFi 256GB": "iPad Pro 12.9 2022 M2 WiFi 256GB",
            "iPad Pro 11 (2022) WiFi 5G 128GB": "iPad Pro 11 2022 M2 WiFi 5G 128GB",
            "iPad Pro 11 (2022) WiFi 5G 256GB": "iPad Pro 11 2022 M2 WiFi 5G 256GB",
            "iPad Pro 11 (2022) WiFi 128GB": "iPad Pro 11 2022 M2 WiFi 128GB",
            "iPad Pro 11 (2022) WiFi 256GB": "iPad Pro 11 2022 M2 WiFi 256GB",
            "iPad Gen 10 WiFi 5G 64GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 64GB",
            "iPad Gen 10 WiFi 5G 256GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 256GB",
            "iPad Gen 10 WiFi 64GB": "iPad Gen 10 2022 10.9 inch WiFi 64GB",
            "iPad Gen 10 WiFi 256GB": "iPad Gen 10 2022 10.9 inch WiFi 256GB",
            "iPad Pro 12.9 (2021) WiFi 5G 128GB": "iPad Pro 12.9 2021 M1 WiFi 5G 128GB",
            "iPad Pro 12.9 (2021) WiFi 5G 256GB": "iPad Pro 12.9 2021 M1 WiFi 5G 256GB",
            "iPad Pro 12.9 (2021) WiFi 128GB": "iPad Pro 12.9 2021 M1 WiFi 128GB",
            "iPad Pro 12.9 (2021) WiFi 256GB": "iPad Pro 12.9 2021 M1 WiFi 5G 256GB",
            "iPad Pro 11 (2021) WiFi 5G 128GB": "iPad Pro 11 2021 M1 WiFi 5G 128GB",
            "iPad Pro 11 (2021) WiFi 5G 256GB": "iPad Pro 11 2021 M1 WiFi 5G 256GB",
            "iPad Pro 11 (2021) WiFi 128GB": "iPad Pro 11 2021 M1 WiFi 128GB",
            "iPad Pro 11 (2021) WiFi 256GB": "iPad Pro 11 2021 M1 WiFi 5G 256GB",
            "iPad Air (Gen 5) WiFi 5G 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB",
            "iPad Air (Gen 5) WiFi 5G 256GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB",
            "iPad Air (Gen 5) WiFi 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 64GB",
            "iPad Air (2020) Cellular 64GB": "iPad Air 10.9 2020 WiFi + Cellular 64GB",
            "iPad Air 10.9 2020 WiFi + Cellular 256GB": "iPad Air 10.9 2020 WiFi + Cellular 256GB",
            "iPad Air (2020) Wifi 64GB": "iPad Air 10.9 2020 WiFi 64GB",
            "iPad Air 10.9 2020 WiFi 256GB": "iPad Air 10.9 2020 WiFi 256GB",
            "iPad (Gen 9) LTE 64GB": "iPad 10.2 2021 WiFi + Cellular 64GB",
            "iPad (Gen 9) LTE 256GB": "iPad 10.2 2021 WiFi + Cellular 256GB",
            "iPad (Gen 9) Wifi 64GB": "iPad 10.2 2021 WiFi 64GB",
            "iPad (Gen 9) Wifi 256GB": "iPad 10.2 2021 WiFi 256GB",
            "iPad mini (Gen 6) Wifi 5G 64GB": "iPad mini 8.3 2021 WiFi 5G 64GB",
            "iPad mini (Gen 6) Wifi 5G 256GB": "iPad mini 8.3 2021 WiFi 5G 256GB",
            "iPad mini (Gen 6) Wifi 64GB": "iPad mini 8.3 2021 WiFi 64GB",
            "iPad mini (Gen 6) Wifi 256GB": "iPad mini 8.3 2021 WiFi 256GB",
            "MacBook Pro 16\" 2021 M1 Pro 512GB": "MacBook Pro 16\" 2021 M1 Pro 512GB",
            "MacBook Pro 16\" 2021 M1 Pro 1TB": "MacBook Pro 16\" 2021 M1 Pro 1TB",
            "MacBook Pro 14\" 2021 M1 Pro 512GB": "MacBook Pro 14\" 2021 M1 Pro 512GB",
            "MacBook Pro 14\" 2021 M1 Pro 1TB": "MacBook Pro 14\" 2021 M1 Pro 1TB",
            "MacBook Pro 13\" 2020 Touch Bar M1 256GB": "MacBook Pro 13\" 2020 Touch Bar M1 256GB",
            "MacBook Pro 13\" 2020 Touch Bar M1 512GB": "MacBook Pro 13\" 2020 Touch Bar M1 512GB",
            "MacBook Air 13\" 2020 M1 256GB": "MacBook Air 13\" 2020 M1 256GB",
            "MacBook Air 13\" 2020 M1 512GB": "MacBook Air 13\" 2020 M1 512GB",
            'iPad Pro M2 12.9 5G 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 5G 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 Wi-Fi 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9 Wi-Fi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 5G 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 5G 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 Wi-Fi 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro M2 11 Wi-Fi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Gen 10 10.9 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad Gen 10 10.9 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad Gen 10 10.9 Wi-Fi 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad Gen 10 10.9 Wi-Fi 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'Apple Watch Series 8 viền nhôm Cellular 45mm': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 viền nhôm Cellular 41mm': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 45mm': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 41mm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            # 'Apple Watch Series 7 Viền nhôm Cellular 45mm': 'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
            # 'Apple Watch Series 7 Viền nhôm Cellular 41mm': 'Apple Watch Series 7 GPS + Cellular 41mm viền nhôm dây cao su',
            # 'Apple Watch Series 7 GPS 45mm': 'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su',
            # 'Apple Watch Series 7 GPS 41mm': 'Apple Watch Series 7 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE (2022) Cellular 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE (2022) Cellular 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE (2022) GPS 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE (2022) GPS 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch SE Cellular 44mm (Sport Band)': 'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE Cellular 40mm (Sport Band)': 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE GPS 44mm': 'Apple Watch SE GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE GPS 40mm': 'Apple Watch SE GPS 40mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 38mm' : 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'AirPods Pro (Gen 2)': 'AirPods Pro 2 2022',
            'Tai nghe AirPods Pro (Gen 2)': 'AirPods Pro 2 2022',
            'AirPods Pro': 'AirPods Pro 2021',
            'AirPods 3': 'AirPods 3 2021',
            'AirPods 2': 'AirPods 2 hộp sạc dây',
            'AirTag - 4 pack': 'AirTag - 4 Pack',
            'AirTag - 1 pack': 'AirTag - 1 Pack',
            'Apple Watch Ultra 2 Cellular 49mm Ocean Band' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 Viền nhôm Cellular 41mm Sport Band S/M' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Viền nhôm Cellular 45mm Sport Band S/M' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 41mm Sport Band S/M' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 45mm Sport Band S/M' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'AirPods Pro Gen 2 (USB-C)' : 'AirPods Pro 2023 USB-C',
            'Tai nghe AirPods Pro Gen 2 (USB-C)': 'AirPods Pro 2023 USB-C',
        }

        # Convert keys to lowercase using a dictionary comprehension
        vt_replacement_dict_lower = {key.lower(): value for key, value in vt_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in vt_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in vt_replacement_dict_lower:
                vt_df.loc[i, "Product_Name"] = vt_replacement_dict_lower[product_name]

        vt_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End Viettel

        # 6 start cps
        cps_df = pandas.read_csv(f"../content/{now}/6-cps-{now}.csv", delimiter=";")
        cps_not_trade_list = ['MacBook Pro 16" 2021 M1 Pro 1TB', 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su']

        cps_column_names = ['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
                          'Khuyen_Mai', 'Thanh_Toan']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data = {'Product_Name': cps_not_trade_list}
        for col in cps_column_names[1:]:
            data[col] = ['N/A'] * len(cps_not_trade_list)

        new_cps = pandas.DataFrame(data, columns = cps_column_names)
        cps_df = pandas.concat([new_cps, cps_df], ignore_index = True)

        cps_row_to_drop = []
        cps_product_list = cps_df['Product_Name'].to_list()

        cps_replacement_dict = {
            "iPhone SE 2022": "iPhone SE 2022 64GB",
            "iPhone SE 2022 128GB": "iPhone SE 2022 128GB",
            "iPhone SE 2022 256GB": "iPhone SE 2022 256GB",
            "iPad Pro 12.9 inch 2022 M2 Wifi + 5G 128GB": "iPad Pro 12.9 2022 M2 WiFi 5G 128GB",
            "iPad Pro 12.9 inch 2022 M2 Wifi + 5G 256GB": "iPad Pro 12.9 2022 M2 WiFi 5G 256GB",
            "iPad Pro 12.9 inch 2022 M2 Wifi 128GB": "iPad Pro 12.9 2022 M2 WiFi 128GB",
            "iPad Pro 12.9 inch 2022 M2 Wifi 256GB": "iPad Pro 12.9 2022 M2 WiFi 256GB",
            "iPad Pro 11 inch 2022 M2 Wifi + 5G 128GB": "iPad Pro 11 2022 M2 WiFi 5G 128GB",
            "iPad Pro 11 inch 2022 M2 Wifi + 5G 256GB": "iPad Pro 11 2022 M2 WiFi 5G 256GB",
            "iPad Pro 11 inch 2022 M2 Wifi 128GB": "iPad Pro 11 2022 M2 WiFi 128GB",
            "iPad Pro 11 inch 2022 M2 Wifi 256GB": "iPad Pro 11 2022 M2 WiFi 256GB",
            "iPad Gen 10 10.9 inch 2022 Wifi + 5G 64GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 64GB",
            "iPad Gen 10 10.9 inch 2022 Wifi + 5G 256GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 256GB",
            "iPad Gen 10 10.9 inch 2022 Wifi 64GB": "iPad Gen 10 2022 10.9 inch WiFi 64GB",
            "iPad Gen 10 10.9 inch 2022 Wifi 256GB": "iPad Gen 10 2022 10.9 inch WiFi 256GB",
            "iPad Pro 12.9 2021 M1 5G 128GB": "iPad Pro 12.9 2021 M1 WiFi 5G 128GB",
            "iPad Pro 12.9 2021 M1 5G 256GB": "iPad Pro 12.9 2021 M1 WiFi 5G 256GB",
            "iPad Pro 12.9 2021 M1 WiFi 128GB": "iPad Pro 12.9 2021 M1 WiFi 128GB",
            "iPad Pro 12.9 2021 M1 WiFi 256GB": "iPad Pro 12.9 2021 M1 WiFi 256GB",
            "iPad Pro 11 2021 M1 5G 128GB": "iPad Pro 11 2021 M1 WiFi 5G 128GB",
            "iPad Pro 11 2021 M1 5G 256GB": "iPad Pro 11 2021 M1 WiFi 5G 256GB",
            "iPad Pro 11 2021 M1 WiFi 128GB": "iPad Pro 11 2021 M1 WiFi 128GB",
            "iPad Pro 11 2021 M1 WiFi 256GB": "iPad Pro 11 2021 M1 WiFi 256GB",
            "iPad Air 5 10.9 inch (2022) 5G 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB",
            "iPad Air 5 10.9 inch (2022) 5G 256GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB",
            "iPad Air 5 10.9 inch (2022) WIFI 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 64GB",
            "iPad Air 5 10.9 inch (2022) WIFI 256GB": "iPad Air 5 2022 10.9 inch M1 WiFi 256GB",
            "iPad Air 10.9 2020 4G 64GB": "iPad Air 10.9 2020 WiFi + Cellular 64GB",
            "iPad Air 4 (2020) 4G 256GB": "iPad Air 10.9 2020 WiFi + Cellular 256GB",
            "iPad Air 10.9 2020 WiFi 64GB": "iPad Air 10.9 2020 WiFi 64GB",
            "iPad Air 10.9 2020 WiFi 256GB": "iPad Air 10.9 2020 WiFi 256GB",
            "iPad 10.2 2021 4G 64GB": "iPad 10.2 2021 WiFi + Cellular 64GB",
            "iPad 10.2 2021 4G 256GB": "iPad 10.2 2021 WiFi + Cellular 256GB",
            "iPad 10.2 2021 WiFi 64GB": "iPad 10.2 2021 WiFi 64GB",
            "iPad 10.2 2021 WiFi 256GB": "iPad 10.2 2021 WiFi 256GB",
            "iPad mini 6 LTE 4GB 64GB": "iPad mini 8.3 2021 WiFi 5G 64GB",
            "iPad mini 6 LTE 4GB 256GB": "iPad mini 8.3 2021 WiFi 5G 256GB",
            "iPad mini 6 WiFi 64GB": "iPad mini 8.3 2021 WiFi 64GB",
            "iPad mini 6 WiFi 256GB": "iPad mini 8.3 2021 WiFi 256GB",

            'Macbook Pro 14 M3 8GB - 512GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'Macbook Pro 14 M3 8GB - 1TB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'Macbook Pro 14 M3 Pro 18GB - 512GB': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'Macbook Pro 14 M3 Pro 18GB - 1TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'Macbook Pro 16 M3 Pro 18GB - 512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

            'Macbook Air M3 15 inch 2024 8GB - 256GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'Macbook Air M3 15 inch 2024 8GB - 512GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'Macbook Air M3 13 inch 2024 8GB - 256GB': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'Macbook Air M3 13 inch 2024 8GB - 512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

            "Macbook Air 15 inch M2 2023 8GB 256GB sạc 30W": "MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB",
            "Macbook Air 15 inch M2 2023 8GB 256GB sạc 35W": "MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB",
            "Macbook Air 15 inch M2 2023 8GB 256GB": "MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB",
            "MacBook Air 15 inch M2 2023 8GB 512GB": "MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB",
            "MacBook Pro 16 inch M2 Pro 2023 (12 CPU - 19 GPU - 16GB - 512GB)": "MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB",
            "MacBook Pro 16 inch M2 Pro 2023 (12 CPU - 19 GPU - 16GB - 1TB)": "MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB",
            "MacBook Pro 14 inch M2 Pro 2023 (10 CPU - 16 GPU - 16GB - 512GB)": "MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB",
            "MacBook Pro 14 inch M2 Pro 2023 (12 CPU - 19 GPU 16GB 1TB 2023)": "MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB",
            "Macbook Pro 16 inch 2021": "MacBook Pro 16\" 2021 M1 Pro 512GB",
            "M1 Pro 16 10 CPU - 16 GPU 16GB 1TB 2021": "MacBook Pro 16\" 2021 M1 Pro 1TB",
            "Macbook Pro 14 inch 2021": "MacBook Pro 14\" 2021 M1 Pro 512GB",
            "Macbook Pro 14 M1 Pro 10 CPU - 16 GPU 16GB 1TB 2021": "MacBook Pro 14\" 2021 M1 Pro 1TB",
            "Apple Macbook Pro 13 M2 2022 8GB 256GB": "MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB",
            "Apple MacBook Pro 13 M2 2022 8GB 512GB": "MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB",
            "Apple Macbook Air M2 2022 8GB 256GB": "MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB",
            "Apple Macbook Air M2 2022 8GB 512GB": "MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB",
            "Apple MacBook Pro 13 Touch Bar M1 256GB 2020": "MacBook Pro 13\" 2020 Touch Bar M1 256GB",
            "Apple MacBook Pro 13 Touch Bar M1 512GB 2020": "MacBook Pro 13\" 2020 Touch Bar M1 512GB",
            "Apple MacBook Air M1 256GB 2020": "MacBook Air 13\" 2020 M1 256GB",
            "Apple MacBook Air M1 512GB 2020": "MacBook Air 13\" 2020 M1 512GB",
            'Apple Watch Series 8 45mm 4G viền nhôm dây cao su': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm 4G viền nhôm dây cao su': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 45mm GPS viền nhôm': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm GPS viền nhôm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch Series 7 45mm (4G) Viền nhôm dây cao su': 'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 7 41mm (4G) Viền nhôm dây cao su': 'Apple Watch Series 7 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 7 45mm (GPS) Viền nhôm dây cao su': 'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 7 41mm (GPS) Viền nhôm dây cao su': 'Apple Watch Series 7 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE 2022 44mm LTE': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 40mm LTE': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 2022 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch SE 44mm (4G) Viền Nhôm - Dây Cao Su': 'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 40mm (4G) Viền Nhôm - Dây Cao Su': 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch Series 3 42mm (GPS) viền nhôm dây cao suchính hãng': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 38mm GPS viền nhôm dây cao su chính hãng': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'airpods max': 'AirPods Max',
            'Tai nghe Bluetooth Apple AirPods Pro 2022': 'AirPods Pro 2 2022',
            'AirPods Pro 2021 Magsafe': 'AirPods Pro 2021',
            'Tai nghe Bluetooth Apple AirPods 3 MagSafe': 'AirPods 3 2021',
            'Tai nghe Bluetooth Apple AirPods 2': 'AirPods 2 hộp sạc dây',
            'Apple AirTag Combo 4 cái': 'AirTag - 4 Pack',
            'Apple AirTag': 'AirTag - 1 Pack',

            'iPad Pro M4 13 inch 5G 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch 5G 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch Wifi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch Wifi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch 5G 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch 5G 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch Wifi 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch Wifi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air 6 M2 13 inch 5G 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13 inch 5G 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 inch Wifi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13 inch Wifi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 inch 5G 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 inch 5G 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11 inch Wifi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch Wifi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            'iPad Pro M2 12.9 5G 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 5G 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 Wi-Fi 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9 Wi-Fi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 5G 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 5G 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 Wi-Fi 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro M2 11 Wi-Fi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Gen 10 10.9 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad Gen 10 10.9 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad Gen 10 10.9 Wi-Fi 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            ' iPad Gen 10 10.9 Wi-Fi 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'Apple Watch Ultra 2 49mm (4G) dây cao su' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 41mm (4G) viền nhôm dây cao su' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 45mm (4G) viền nhôm dây cao su' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 41mm (GPS) viền nhôm dây cao su' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 45mm (GPS) viền nhôm dây cao su' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Tai nghe Bluetooth Apple AirPods Pro 2 2023 USB-C' : 'AirPods Pro 2023 USB-C'
        }

        # Convert keys to lowercase using a dictionary comprehension
        cps_replacement_dict_lower = {key.lower(): value for key, value in cps_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in cps_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in cps_replacement_dict_lower:
                cps_df.loc[i, "Product_Name"] = cps_replacement_dict_lower[product_name]

        cps_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End CPS

        # 7 start shopee
        shopee_df = pandas.read_csv(f"../content/{now}/7-shopee-{now}.csv", delimiter=";")
        shopee_not_trade_list=['iPhone 15 Pro Max 256GB', 'iPhone 15 Pro Max 512GB', 'iPhone 15 Pro Max 1TB',
                               'iPhone 15 Pro 128GB', 'iPhone 15 Pro 256GB', 'iPhone 15 Pro 512GB', 'iPhone 15 Pro 1TB',
                               'iPhone 15 Plus 128GB', 'iPhone 15 Plus 256GB', 'iPhone 15 Plus 512GB',
                               'iPhone 15 128GB', 'iPhone 15 256GB', 'iPhone 15 512GB', 'iPhone 14 Pro Max 128GB',
                               'iPhone 14 Pro Max 256GB', 'iPhone 14 Pro Max 512GB', 'iPhone 14 Pro Max 1TB',
                               'iPhone 14 Pro 128GB', 'iPhone 14 Pro 256GB', 'iPhone 14 Pro 512GB', 'iPhone 14 Pro 1TB',
                               'iPhone 14 Plus 128GB', 'iPhone 14 Plus 256GB', 'iPhone 14 Plus 512GB',
                               'iPhone 14 128GB', 'iPhone 14 256GB', 'iPhone 14 512GB', 'iPhone 13 128GB',
                               'iPhone 13 256GB', 'iPhone 13 512GB', 'iPhone 12 64GB', 'iPhone 12 128GB',
                               'iPhone 11 64GB', 'iPhone 11 128GB', 'iPhone SE 2022 64GB', 'iPhone SE 2022 128GB',
                               'iPhone SE 2022 256GB', 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
                               'iPad Pro 13 inch M4 2024 Wifi 256GB', 'iPad Pro 13 inch M4 2024 Wifi 512GB',
                               'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
                               'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
                               'iPad Pro 11 inch M4 2024 Wifi 256GB', 'iPad Pro 11 inch M4 2024 Wifi 512GB',
                               'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
                               'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
                               'iPad Air 13 inch M2 2024 Wifi 128GB', 'iPad Air 13 inch M2 2024 Wifi 256GB',
                               'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
                               'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
                               'iPad Air 11 inch M2 2024 Wifi 128GB', 'iPad Air 11 inch M2 2024 Wifi 256GB',
                               'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
                               'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
                               'iPad Pro 12.9 2022 M2 WiFi 5G 256GB', 'iPad Pro 12.9 2022 M2 WiFi 128GB',
                               'iPad Pro 12.9 2022 M2 WiFi 256GB', 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
                               'iPad Pro 11 2022 M2 WiFi 5G 256GB', 'iPad Pro 11 2022 M2 WiFi 128GB',
                               'iPad Pro 11 2022 M2 WiFi 256GB', 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
                               'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB', 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
                               'iPad Air 5 2022 10.9 inch M1 WiFi 256GB', 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
                               'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB', 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
                               'iPad Gen 10 2022 10.9 inch WiFi 256GB', 'iPad 10.2 2021 WiFi + Cellular 64GB',
                               'iPad 10.2 2021 WiFi + Cellular 256GB', 'iPad 10.2 2021 WiFi 64GB',
                               'iPad 10.2 2021 WiFi 256GB', 'iPad mini 8.3 2021 WiFi 5G 64GB',
                               'iPad mini 8.3 2021 WiFi 5G 256GB', 'iPad mini 8.3 2021 WiFi 64GB',
                               'iPad mini 8.3 2021 WiFi 256GB', 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
                               'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
                               'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
                               'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
                               'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
                               'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
                               'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'MacBook Pro 16" 2021 M1 Pro 512GB',
                               'MacBook Pro 16" 2021 M1 Pro 1TB', 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
                               'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'MacBook Pro 14" 2021 M1 Pro 512GB',
                               'MacBook Pro 14" 2021 M1 Pro 1TB', 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
                               'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
                               'MacBook Pro 13" 2020 Touch Bar M1 256GB', 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
                               'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
                               'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
                               'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
                               'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',
                               'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
                               'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
                               'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
                               'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB', 'MacBook Air 13" 2020 M1 256GB',
                               'MacBook Air 13" 2020 M1 512GB', 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
                               'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
                               'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
                               'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
                               'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
                               'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
                               'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
                               'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
                               'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
                               'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
                               'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
                               'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
                               'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
                               'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
                               'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
                               'AirPods Max', 'AirPods Pro 2021',
                               'AirPods Pro 2023 USB-C', 'AirPods 3 2021',
                               'AirPods Pro 2 2022', 'AirPods 2 hộp sạc dây', 'AirTag - 4 Pack', 'AirTag - 1 Pack'
                               ]


        shopee_column_names = ['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
       'Danh_Gia', 'Da_Ban', 'SP_Co_San', 'Link']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data = {'Product_Name': shopee_not_trade_list}
        for col in shopee_column_names[1:]:
            data[col] = ['N/A'] * len(shopee_not_trade_list)

        shopee_new = pandas.DataFrame(data, columns = shopee_column_names)
        shopee_df = pandas.concat([shopee_new, shopee_df], ignore_index = True)

        shopee_replacement_dict = {
            'Điện thoại iPhone 12 64GB' : 'iPhone 12 64GB',
            'Điện thoại iPhone 14 Plus 128GB' : 'iPhone 14 Plus 128GB',
            'iPhone 14 Plus 512 GB': 'iPhone 14 Plus 512GB',
            'Điện thoại iPhone 15 Pro Max 256GB': 'iPhone 15 Pro Max 256GB',
            'Điện thoại iPhone 15 256GB': 'iPhone 15 256GB',
            'Điện thoại iPhone 14 128GB': 'iPhone 14 128GB',
            'Điện thoại iPhone 15 Pro 256GB': 'iPhone 15 Pro 256GB',
            'iPad Pro 12.9 2021 M1 WiFi 5G 128GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro 12.9 2021 M1 WiFi 5G 256GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
            'iPad Pro 12.9 2021 M1 WiFi 128GB': 'iPad Pro 12.9 2021 M1 WiFi 128GB',
            'iPad Pro 12.9 2021 M1 WiFi 256GB': 'iPad Pro 12.9 2021 M1 WiFi 256GB',
            'iPad Pro 11 2021 M1 WiFi 5G 128GB': 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            '11-inch Wi-Fi + Cellular 256GB': 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
            'iPad Pro 11 2021 M1 WiFi 128GB': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'iPad Pro 11 2021 M1 WiFi 256GB': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'iPad Air 10.9 2020 WiFi + Cellular 64GB': 'iPad Air 10.9 2020 WiFi + Cellular 64GB',
            'iPad Air 10.9 2020 WiFi + Cellular 256GB': 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air 10.9 2020 WiFi 64GB': 'iPad Air 10.9 2020 WiFi 64GB',
            'iPad Air 10.9 2020 WiFi 256GB': 'iPad Air 10.9 2020 WiFi 256GB',
            'iPad 10.2 2021 WiFi + Cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 10.2 2021 WiFi + Cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'Máy tính bảng iPad Gen 9th 10.2-inch Wi-Fi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad Gen 9th 10.2-inch Wi-Fi 256GB': 'iPad 10.2 2021 WiFi 256GB',

            'Máy tính xách tay MacBook Pro- M3 Chip, 14-inch, 512GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'Máy tính xách tay MacBook Pro- M3 Pro Chip, 14-inch, 1TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'Máy tính xách tay MacBook Pro- M3 Pro Chip, 16-inch, 18GB, 512GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

            'MacBook Pro 16" 2021 M1 Pro 512GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro 16" 2021 M1 Pro 1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro 14" 2021 M1 Pro 512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro 14" 2021 M1 Pro 1TB': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'MacBook Pro (2020) M1 Chip, 13.3 inch, 8GB, 256GB SSD': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro (2020) M1 Chip, 13.3 inch, 8GB, 512GB SSD': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air (2020) M1 Chip, 13.3-inch, 8GB, 256GB SSD': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air (2020) M1 Chip, 13.3-inch, 8GB, 512GB SSD': 'MacBook Air 13" 2020 M1 512GB',
            'Macbook Pro (2022) M2 chip, 13.3 inches, 8GB, 512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'Máy tính xách tay Macbook Air (2022) M2 chip, 13.6 inches, 8GB, 256GB SSD': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'Macbook Air (2022) M2 chip, 13.6 inches, 8GB, 512GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su': 'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
            'Watch Series 7 41mm GPS + Cellular Sport Band': 'Apple Watch Series 7 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su': 'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su',
            'Watch Series 7 41mm GPS Sport Band': 'Apple Watch Series 7 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su': 'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su': 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Watch SE 44mm GPS Sport Band': 'Apple Watch SE GPS 44mm viền nhôm dây cao su',
            'Watch SE 40mm GPS Sport Band': 'Apple Watch SE GPS 40mm viền nhôm dây cao su',
            'Watch Series 3 42mm GPS Sport Band': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Watch Series 3 38mm GPS Sport Band': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'Tai nghe AirPods Pro 2nd gen (2022)': 'AirPods Pro 2 2022',
            'AirPods Pro': 'AirPods Pro 2021',
            'Tai nghe AirPods 3rd gen lightning charge': 'AirPods 3 2021',
            'AirPods 3rd gen magsafe charge': 'AirPods 3 2021',
            'Tai nghe AirPods with Charging Case 2nd gen': 'AirPods 2 hộp sạc dây',
            'AirTag - 4 Pack': 'AirTag - 4 Pack',
            'AirTag - 1 Pack': 'AirTag - 1 Pack',
            'Đồng hồ Watch Series 9 41mm (GPS) Viền nhôm - Dây cao su' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
        }

        # Convert keys to lowercase using a dictionary comprehension
        shopee_replacement_dict_lower = {key.lower(): value for key, value in shopee_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in shopee_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in shopee_replacement_dict_lower:
                shopee_df.loc[i, "Product_Name"] = shopee_replacement_dict_lower[product_name]

        shopee_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)


        # End Shopee

        # 8 start tz
        tz_df = pandas.read_csv(f"../content/{now}/8-topzone-{now}.csv", delimiter=";")

        tz_not_trade_list = ['MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro 16" 2021 M1 Pro 1TB', 'MacBook Pro 14" 2021 M1 Pro 1TB', 'iPhone SE 2022 256GB',
            'iPhone 12 mini 64GB', 'iPhone 14 Pro Max 1TB',
            'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'AirPods Pro 2021',
            'MacBook Pro 16" 2021 M1 Pro 512GB', 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'iPad mini 8.3 2021 WiFi 5G 256GB', 'MacBook Air 13 inch M2 2022 8CPU - 10GPU RAM 8 GB - SSD 512 GB',
            'MacBook Air 13" 2020 M1 512GB', 'iPhone 14 Plus 512GB', 'iPhone 14 512GB',
            'iPhone 13 512GB', 'iPad Pro 11 2022 M2 WiFi 5G 256GB', 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'iPhone 14 Pro 1TB',

                             ]

        tz_column_names = ['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', '+VNPAY',
                         'Date', 'Khuyen_Mai', 'vnpay', 'link']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data = {'Product_Name': tz_not_trade_list}
        for col in tz_column_names[1:]:
            data[col] = ['N/A'] * len(tz_not_trade_list)

        new_tz = pandas.DataFrame(data, columns = tz_column_names)
        new_tz['vnpay']=0
        tz_df = pandas.concat([new_tz, tz_df], ignore_index = True)

        tz_replacement_dict={
            'iphone-12-128gb': 'iPhone 12 128GB',
            'iPhone 12': 'iPhone 12 64GB',
            'iPhone 13': 'iPhone 13 128GB',
            'iphone-14-pro-512gb': 'iPhone 14 Pro 512GB',
            'iphone-15-512gb' : 'iPhone 15 512GB',
            'iPhone 15': 'iPhone 15 128GB',
            'iphone-15-plus-512gb': 'iPhone 15 Plus 512GB',
            'iphone-15-pro-1tb': 'iPhone 15 Pro 1TB',
            'iPhone se 2022': 'iPhone SE 2022 64GB',
            'iPhone 14': 'iPhone 14 128GB',
            'iPhone 14 Pro': 'iPhone 14 Pro 128GB',
            'iphone-15-256gb': 'iPhone 15 256GB', 'iphone-15-plus': 'iPhone 15 Plus 128GB',
            'iPhone 14 Pro Max': 'iPhone 14 Pro Max 128GB', 'iphone-14-pro-max': 'iPhone 14 Pro Max 128GB',
            'iPhone 11': 'iPhone 11 64GB',
            'iPhone 13 Pro Max': 'iPhone 13 Pro Max 128GB', 'iphone-14-pro-max-512gb': 'iPhone 14 Pro Max 512GB',
            'iphone-14-pro-max-1tb': 'iPhone 14 Pro Max 1TB', 'iPhone 14 plus': 'iPhone 14 Plus 128GB',
            'iPhone 14 plus 256GB': 'iPhone 14 Plus 256GB', 'iPhone 14 plus 512GB': 'iPhone 14 Plus 512GB',
            'iPhone SE (2022) 64GB': 'iPhone SE 2022 64GB', 'iPhone se 128GB 2022': 'iPhone SE 2022 128GB',
            'iPhone se 256GB 2022': 'iPhone SE 2022 256GB', 'iphone-13-mini-256gb': 'iPhone 13 Mini 256GB',

            'iPad Pro M4 13 inch 5G 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'ipad-pro-m4-13-inch-wifi-cellular-256gb': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro m4 13 inch wifi cellular 256GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch 5G 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro m4 13 inch wifi cellular 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'ipad-pro-m4-13-inch-wifi-cellular-512gb': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch WiFi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch WiFi 512GB 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'ipad-pro-m4-13-inch-wifi-512gb': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch 5G 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro m4 11 inch wifi cellular 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch 5G 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'ipad-pro-m4-11-inch-wifi-cellular-512gb': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro m4 11 inch wifi cellular 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch WiFi 256GB 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch WiFi 512GB 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch WiFi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'ipad-pro-m4-11-inch-wifi-512gb': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air 6 M2 13 inch 5G 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'ipad-air-m2-13-inch-wifi-cellular-128gb': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13 inch 5G 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'ipad-air-m2-13-inch-wifi-cellular-256gb': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 inch WiFi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad air m2 13 inch wifi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13 inch WiFi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad air m2 13 inch wifi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'ipad-air-m2-13-inch-wifi-256gb': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 inch 5G 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'ipad-air-m2-11-inch-wifi-cellular-128gb': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad air m2 11 inch wifi cellular 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 inch 5G 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad air m2 11 inch wifi cellular 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'ipad-air-m2-11-inch-wifi-cellular-256gb': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11 inch WiFi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'ipad-air-m2-11-inch-wifi-128gb': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad air m2 11 inch wifi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch WiFi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',
            'ipad-air-m2-11-inch-wifi-256gb': 'iPad Air 11 inch M2 2024 Wifi 256GB',
            'iPad air m2 11 inch wifi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            'iPad air 5 m1 wifi cellular 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad air 5 m1 wifi cellular 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Pro m2 129 wifi cellular 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 128GB 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 12.9 inch 5G 128GB 128GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'ipad-pro-m2-129-wifi-cellular-128gb': 'iPad Pro 12.9 2022 M2 WiFi 5G 128GB',
            'ipad-pro-m2-129-wifi-cellular-256gb': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 256GB 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 inch WiFi Cellular 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 12.9 inch WiFi 128GB 128GB': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro m2 12 9 inch': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'ipad-pro-m2-12-9-inch': 'iPad Pro 12.9 2022 M2 WiFi 128GB',
            'iPad Pro M2 12.9 inch WiFi 256GB 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro m2 129 wifi 256GB': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'ipad-pro-m2-129-wifi-256gb': 'iPad Pro 12.9 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 inch WiFi + Cellular 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 inch WiFi Cellular 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 inch 5G 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro m2 11 wifi cellular 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro M2 11 inch WiFi Cellular 128GB 128GB': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'ipad-pro-m2-11-wifi-cellular-128gb': 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
            'iPad Pro m2 11 wifi cellular 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 inch WiFi Cellular 256GB 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11" WiFi Cellular 256GB 256GB': 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
            'iPad Pro M2 11 inch WiFi 128GB 128GB': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'iPad Pro m2 11 inch': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'ipad-pro-m2-11-inch': 'iPad Pro 11 2022 M2 WiFi 128GB',
            'ipad-pro-m2-11-wifi-256gb': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Pro M2 11 inch WiFi 256GB 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad Pro m2 11 wifi 256GB': 'iPad Pro 11 2022 M2 WiFi 256GB',
            'iPad 10 5G 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 WiFi Cellular 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 WiFi + Cellular 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 wifi cellular 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB',
            'iPad 10 5G 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 WiFi Cellular 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 WiFi + Cellular 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 wifi cellular 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
            'iPad 10 WiFi 64GB 64GB': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad gen 10': 'iPad Gen 10 2022 10.9 inch WiFi 64GB',
            'iPad 10 WiFi 256GB 256GB': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'iPad 10': 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
            'iPad Pro M1 12.9 inch WiFi + Cellular 128GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro m1 129 inch wifi cellular 128GB 2021': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro m1 129 inch wifi cellular 256GB 2021': 'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
            'iPad Pro M1 12.9 inch WiFi + Cellular 256GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
            'iPad Pro M1 12.9 inch WiFi 128GB': 'iPad Pro 12.9 2021 M1 WiFi 128GB',
            'iPad Pro M1 12.9 inch WiFi 256GB': 'iPad Pro 12.9 2021 M1 WiFi 256GB',
            'iPad Pro m1 11 inch wifi cellular 128GB 2021': 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            'ipad-pro-m1-11-inch-wifi-cellular-128gb-2021': 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
            'iPad Pro m1 11 inch wifi cellular 256GB 2021': 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
            'ipad-pro-m1-11-inch-wifi-cellular-256gb-2021': 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
            'iPad Pro M1 11 inch WiFi 128GB': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'ipad-pro-m1-11-inch-wifi-128gb-2021': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'iPad Pro M1 11 inch WiFi 256GB': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'ipad-pro-m1-11-inch-wifi-256gb-2021': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'iPad Air 5 5G 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 WiFi + Cellular 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 5G 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Air 5 WiFi + Cellular 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad air 5': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad Air 5 WiFi 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad air 5 m1 wifi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'iPad Air 5 WiFi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'iPad 9 4G 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 10.2 inch WiFi + Cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 wifi cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 WiFi + Cellular 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 9 10.2 inch WiFi + Cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 WiFi + Cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 wifi cellular 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 4G 256GB': 'iPad 10.2 2021 WiFi + Cellular 256GB',
            'iPad 9 10.2 inch WiFi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad gen 9': 'iPad 10.2 2021 WiFi 64GB',
            'iPad 9 WiFi 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad 9 10.2 inch WiFi 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'iPad 9 WiFi 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'iPad mini 6 cellular 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad mini 6 WiFi + Cellular 64GB': 'iPad mini 8.3 2021 WiFi 5G 64GB',
            'iPad mini 6': 'iPad mini 8.3 2021 WiFi 64GB', 'iPad mini 6 WiFi 64GB': 'iPad mini 8.3 2021 WiFi 64GB',
            'iPad mini 6 wifi 256GB': 'iPad mini 8.3 2021 WiFi 256GB',
            'iPad Mini 6 WiFi 256GB': 'iPad mini 8.3 2021 WiFi 256GB',
            'iPad Pro m2 129 wifi cellular 256GB': 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
            'MacBook Pro 14 inch M3 RAM 8 GB - SSD 512 GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 2023 8CPU - 10GPU RAM 8 GB - SSD 512 GB': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 Pro RAM 18 GB - SSD 1 TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 14 inch M3 Pro 2023 12CPU - 18GPU RAM 18 GB - SSD 1 TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'Apple MacBook Pro 14 inch m3 Pro 2023 12 core': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 inch M3 Pro RAM 18 GB - SSD 512 GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Pro 16 inch M3 Pro 2023 12CPU - 18GPU RAM 18 GB - SSD 512 GB': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',
            'MacBook Air 15 inch M2 Sạc 35W RAM 8 GB - SSD 256 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8CPU - 10GPU Sạc 35W RAM 8 GB - SSD 256 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 2023 8CPU - 10GPU RAM 8 GB - SSD 256 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 RAM 8 GB - SSD 512 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Air 15 inch M2 2023 8CPU - 10GPU RAM 8 GB - SSD 512 GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Pro 16 inch M2 Pro 2023 12CPU - 19GPU RAM 16 GB - SSD 512 GB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 14 inch M2 Pro 2023 10CPU - 16GPU RAM 16 GB - SSD 512 GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 inch M3 Pro 2023 11CPU - 14GPU RAM 18 GB - SSD 1 TB': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 inch M1 Pro 2021 10CPU - 16GPU RAM 16 GB - SSD 512 GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro 16 inch M1 Pro 2021 10CPU - 16GPU RAM 16 GB - SSD 1 TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'Apple MacBook Pro 14 m1 Pro 2021 10 core cpu': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro 14 inch M1 Pro 2021 16-Core GPU RAM 16 GB - SSD 1 TB': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'Apple MacBook Pro 13 inch m2 2022': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 2022 8CPU - 10GPU RAM 8 GB - SSD 256 GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 2022 8CPU - 10GPU RAM 8 GB - SSD 512 GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air 13 inch M2 RAM 8 GB - SSD 256 GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook air m2 2022 8 core gpu': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 2022 8CPU - 8GPU RAM 8 GB - SSD 256 GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air 13 inch M2 2022 8CPU - 10GPU RAM 8 GB - SSD 512 GB': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro 13 inch M1 2020 RAM 8 GB - SSD 256 GB': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'Apple MacBook Pro 2020 m1 myd82saa': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro 13 inch M1 2020 RAM 8 GB - SSD 512 GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',

            'MacBook Air 15 inch M3 RAM 8 GB - SSD 256 GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air 15 inch M3 RAM 8 GB - SSD 512 GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air 13 inch M3 RAM 8 GB - SSD 256 GB': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air 13 inch M3 RAM 8 GB - SSD 512 GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

            'MacBook Air 13 inch M1 2020 8CPU - 7GPU RAM 8 GB - SSD 256 GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air 13 inch M1 RAM 8 GB - SSD 256 GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air M1 2020 8-Core GPU RAM 8 GB - SSD 512 GB': 'MacBook Air 13" 2020 M1 512GB',
            'Apple Watch ultra 2 lte 49mm vien titanium day ocean' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 GPS + Cellular 41mm LTE 41 mm' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS + Cellular 41mm viền nhôm dây thể thao 41mm': 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch s9 lte 41mm vien nhom day silicone' : "Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M",
            'Apple Watch Series 9 GPS + Cellular 45mm viền nhôm dây thể thao size S/M 45mm Dây S/M': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'apple-watch-series-9-gps-cellular-45mm-sport-band-size-s': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS + Cellular 45mm LTE 45 mm' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS + Cellular 45mm viền nhôm dây thể thao 45mm': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch s9 lte 45mm vien nhom day silicone' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 41mm viền nhôm dây thể thao 41mm' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 41mm 41 mm': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch s9 41mm vien nhom day silicone': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch s9 45mm vien nhom day silicone': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 45mm viền nhôm dây thể thao size S/M 45mm Dây S/M': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 45mm 45 mm' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 GPS 45mm viền nhôm dây thể thao 45mm': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'tai nghe bluetooth airpods Pro gen 2 magsafe charge usb c Apple mtjv3' : 'AirPods Pro 2023 USB-C',
            'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây thể thao 45mm': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch s8 lte 45mm': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây thể thao 41mm': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch s8 lte 41mm': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 45mm viền nhôm dây thể thao 45mm': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 45mm 45mm': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch s8': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 41mm viền nhôm dây thể thao 41mm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 GPS 41mm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch s8 41mm': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS + Cellular 40mm viền nhôm dây thể thao 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch se 2022 lte 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS + Cellular 40mm 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch se 2022 lte 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS + Cellular 44mm viền nhôm dây thể thao 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS + Cellular 44mm 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch se 2022': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS 40mm viền nhôm dây thể thao 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch se 2022 44mm vien nhom': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS 44mm viền nhôm dây thể thao 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2022 GPS 44mm 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 42mm': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch s3 gps 42mm vien nhom day cao su den': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 38mm': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'Apple Watch s3 gps 38mm trang': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'bluetooth airpods Max Apple': 'AirPods Max',
            'airpods Pro 2': 'AirPods Pro 2 2022',
            'bluetooth airpods Pro magsafe charge Apple mlwk3': 'AirPods Pro 2021',
            'AirPods Pro Hộp sạc MagSafe Hộp sạc MagSafe': 'AirPods Pro 2021', 'airpods 3': 'AirPods 3 2021',
            'tai nghe bluetooth airpods 2 Apple mv7n2 trang': 'AirPods 2 hộp sạc dây',
            'thiet bi dinh vi thong minh airtag 4 pack mx542': 'AirTag - 4 Pack',
            'thiet bi dinh vi thong minh airtag 1 pack mx532': 'AirTag - 1 Pack'
        }

        # Convert keys to lowercase using a dictionary comprehension
        tz_replacement_dict_lower = {key.lower(): value for key, value in tz_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in tz_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in tz_replacement_dict_lower:
                tz_df.loc[i, "Product_Name"] = tz_replacement_dict_lower[product_name]

        tz_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        tz_df['Gia_Khuyen_Mai']=clean_column(tz_df['Gia_Khuyen_Mai'])

        # End TZ

        # 9 start tiki
        tiki_df = pandas.read_csv(f"../content/{now}/9-tiki-{now}.csv", delimiter=";")

        tiki_not_trade_list= \
            ['iPhone 14 Plus 128GB',
             'iPhone 14 128GB', 'iPhone 15 256GB', 'iPhone 15 Pro 256GB',
             'iPhone 15 Pro Max 512GB', 'iPhone 15 Pro Max 1TB', 'iPhone 13 512GB',
             'iPhone 14 Pro 128GB',
             'iPad mini 8.3 2021 WiFi 256GB', 'iPhone 13 mini 256GB', 'iPhone 13 mini 512GB',
             'iPhone 12 64GB', 'iPhone 14 Pro Max 256GB',
             'iPhone 14 Pro 256GB', 'iPhone 13 128GB', 'iPhone 12 128GB', 'iPhone 11 128GB',
             'iPhone 11 64GB', 'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su',

             'iPad Pro 13 inch M4 2024 Wifi 256GB', 'iPad Pro 13 inch M4 2024 Wifi 512GB',
             'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
             'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
             'iPad Pro 11 inch M4 2024 Wifi 256GB', 'iPad Pro 11 inch M4 2024 Wifi 512GB',
             'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
             'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
             'iPad Air 13 inch M2 2024 Wifi 128GB', 'iPad Air 13 inch M2 2024 Wifi 256GB',
             'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
             'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
             'iPad Air 11 inch M2 2024 Wifi 128GB', 'iPad Air 11 inch M2 2024 Wifi 256GB',
             'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
             'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',

             'MacBook Air 13" 2020 M1 256GB',
             'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
             'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
             'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
             'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
             'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
             'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

             'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
             'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
             'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
             'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
             'iPad mini 8.3 2021 WiFi 64GB',
             'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
             'iPad Pro 12.9 2021 M1 WiFi 5G 256GB',
             'iPad Pro 11 2021 M1 WiFi 5G 128GB', 'iPad Pro 11 2021 M1 WiFi 5G 256GB',
             'iPad Air 10.9 2020 WiFi + Cellular 256GB', 'iPad 10.2 2021 WiFi + Cellular 256GB',
             'iPad Pro 12.9 2021 M1 WiFi 128GB', 'iPad 10.2 2021 WiFi 256GB',
             'iPad mini 8.3 2021 WiFi 5G 256GB',
             'MacBook Pro 16" 2021 M1 Pro 512GB', 'MacBook Pro 16" 2021 M1 Pro 1TB',
             'MacBook Pro 13" 2020 Touch Bar M1 512GB',
             'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
             'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
             'Apple Watch SE GPS 40mm viền nhôm dây cao su',
             'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
             'Apple Watch SE GPS 44mm viền nhôm dây cao su',
             'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
             'MacBook Air 13" 2020 M1 512GB',
             'Apple Watch Series 7 GPS + Cellular 41mm viền nhôm dây cao su',
             'iPhone 13 Pro Max 128GB', 'iPhone SE 2022 256GB', 'MacBook Pro 14" 2021 M1 Pro 1TB',
             'iPad Pro 11 2021 M1 WiFi 128GB', 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
             'iPad Air 5 2022 10.9 inch M1 WiFi 256GB', 'iPad Pro 11 2021 M1 WiFi 256GB',
             'iPad Pro 12.9 2021 M1 WiFi 256GB', 'AirPods Pro 2021',
             'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
             'iPad Air 10.9 2020 WiFi + Cellular 64GB',
             'iPad Pro 12.9 2021 M1 WiFi 5G 128GB', 'iPad Air 10.9 2020 WiFi 256GB',
             'iPad Air 10.9 2020 WiFi 64GB', 'iPhone SE 2022 64GB', 'iPhone 13 mini 128GB',
             'iPhone 13 Pro 256GB',
             'iPhone 13 Pro Max 512GB', 'iPhone 12 Pro 256GB', 'iPhone 14 Pro Max 512GB',
             'iPhone 14 Pro Max 1TB',
             'iPhone 14 Pro Max 128GB', 'iPad mini 8.3 2021 WiFi 5G 64GB',
             'iPad 10.2 2021 WiFi + Cellular 64GB',
             'iPhone 14 Pro 1TB', 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
             'iPhone 13 Pro 128GB',
             'iPhone SE 2022 128GB', 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
             'iPhone 14 256GB',
             'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
             'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
             'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
             'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
             'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
             'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
             'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
             'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
             'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
             'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',

             'iPad Pro 13 inch M4 2024 Wifi 256GB', 'iPad Pro 13 inch M4 2024 Wifi 512GB',
             'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB', 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
             'iPad Pro 11 inch M4 2024 Wifi 256GB', 'iPad Pro 11 inch M4 2024 Wifi 512GB',
             'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB', 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
             'iPad Air 13 inch M2 2024 Wifi 128GB', 'iPad Air 13 inch M2 2024 Wifi 256GB',
             'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB', 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
             'iPad Air 11 inch M2 2024 Wifi 128GB', 'iPad Air 11 inch M2 2024 Wifi 256GB',
             'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB', 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',

             'iPad Pro 12.9 2022 M2 WiFi 5G 128GB', 'iPad Pro 12.9 2022 M2 WiFi 5G 256GB',
             'iPad Pro 12.9 2022 M2 WiFi 128GB', 'iPad Pro 12.9 2022 M2 WiFi 256GB',
             'iPad Pro 11 2022 M2 WiFi 5G 128GB', 'iPad Pro 11 2022 M2 WiFi 5G 256GB',
             'iPad Pro 11 2022 M2 WiFi 128GB', 'iPad Pro 11 2022 M2 WiFi 256GB',
             'iPad Gen 10 2022 10.9 inch WiFi 5G 64GB', 'iPad Gen 10 2022 10.9 inch WiFi 5G 256GB',
             'iPad Gen 10 2022 10.9 inch WiFi 64GB', 'iPad Gen 10 2022 10.9 inch WiFi 256GB',
             'MacBook Pro 14" 2021 M1 Pro 512GB', 'Apple Watch Series 7 GPS 41mm viền nhôm dây cao su',
             'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
             'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
             'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
             'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

             'MacBook Pro 13" 2020 Touch Bar M1 256GB', 'AirPods Pro 2 2022',
             'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB', 'iPhone 14 512GB',
             'iPhone 13 Pro Max 256GB',
             'iPhone 13 256GB', 'iPhone 14 Plus 512GB', 'iPhone SE 2022 128GB', 'iPhone 13 mini 128GB',
             'iPhone 14 Pro 512GB', 'iPhone 14 Plus 512GB', 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
             'iPhone 14 Plus 256GB', 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
             'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB', 'AirTag - 4 Pack', 'AirTag - 1 Pack',
             'iPhone 15 Pro 1TB', 'iPhone 15 Plus 512GB', 'iPhone 15 Pro 512GB', 'iPhone 15 512GB',
             'iPhone 15 Plus 256GB', 'AirPods Pro 2023 USB-C',
             'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
             'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M'
             ]

        tiki_column_names=['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
                           'Khuyen_Mai']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data={'Product_Name': tiki_not_trade_list}
        for col in tiki_column_names[1:]:
            data[col]=['N/A'] * len(tiki_not_trade_list)

        new_tiki=pandas.DataFrame(data, columns = tiki_column_names)
        tiki_df=pandas.concat([new_tiki, tiki_df], ignore_index = True)

        tiki_replacement_dict = {
            'iPad Pro M4 13-Inch Wi-Fi 256GB': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13-Inch Wi-Fi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11-Inch Wi-Fi+ Cellular 256GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11-Inch Wi-Fi+ Cellular 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11-Inch Wi-Fi 256GB': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11-Inch Wi-Fi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',

            'iPad Air 6 M2 13-Inch Wi-Fi+ Cellular 128GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 13-Inch Wi-Fi+ Cellular 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13-Inch Wi-Fi 128GB': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 13-Inch Wi-Fi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11-Inch Wi-Fi+ Cellular 128GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11-Inch Wi-Fi+ Cellular 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 11-Inch Wi-Fi 128GB': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11-Inch Wi-Fi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',
            'iPad mini (6th Gen) Wi-Fi, 2021 64GB' : 'iPad mini 8.3 2021 WiFi 64GB',
            'MacBook Air M2 2022 8GB /256GB': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'iPad Pro 12.9 - inch M1 Wi-Fi + Cellular, 2021 128GB': 'iPad Pro 12.9 2021 M1 WiFi 5G 128GB',
            'iPad Pro 12.9 inch M1 Wi-Fi 2021 128GB': 'iPad Pro 12.9 2021 M1 WiFi 128GB',
            'iPad Pro 12.9 inch M1 Wi-Fi 2021 256GB': 'iPad Pro 12.9 2021 M1 WiFi 256GB',
            'iPad Pro 11- inch M1 Wi-Fi, 2021 128GB': 'iPad Pro 11 2021 M1 WiFi 128GB',
            'iPad Pro 11 inch M1 Wi-Fi 2021 256GB': 'iPad Pro 11 2021 M1 WiFi 256GB',
            'iPad Air (5th Gen) Wi-Fi + Cellular, 2022 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB',
            'iPad Air 5 M1 10.9 Wi-Fi + Cellular 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB',
            'iPad Air (5th Gen) Wi-Fi, 2022 64GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 64GB',
            'iPad Air 5 M1 10.9 Wi-Fi 256GB': 'iPad Air 5 2022 10.9 inch M1 WiFi 256GB',
            'iPad Air (4th Gen) Wi-Fi + Cellular, 2020 64GB': 'iPad Air 10.9 2020 WiFi + Cellular 64GB',
            'iPad Air (4th Gen) Wi-Fi + Cellular 2020 256GB': 'iPad Air 10.9 2020 WiFi + Cellular 256GB',
            'iPad Air (4th Gen) Wi-Fi, 2020 64GB': 'iPad Air 10.9 2020 WiFi 64GB',
            'iPad Air (4th Gen) Wi-Fi, 2020 256GB': 'iPad Air 10.9 2020 WiFi 256GB',
            'iPad 10.2-inch (9th Gen) Wi-Fi + Cellular, 2021 64GB': 'iPad 10.2 2021 WiFi + Cellular 64GB',
            'iPad 10.2-inch (9th Gen) Wi-Fi, 2021 64GB': 'iPad 10.2 2021 WiFi 64GB',
            'iPad Gen 9 10.2-inch Wifi (2021) 256GB': 'iPad 10.2 2021 WiFi 256GB',
            'MacBook Air 15 inch (M2, 2023) 8GB /256GB': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Pro 16 inch 2023 16GB/ 512GB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 inch 2023 16GB/ 1TB': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 inch 2023 16GB/ 512GB': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 inch 2023 16GB/ 1TB': 'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro M1 13 inch 2020 8GB / 256GB': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro M1 13 inch 2020 8GB / 512GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air M1 13 inch 2020 8GB / 256GB': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air M1 13 inch 2020 8GB / 512GB': 'MacBook Air 13" 2020 M1 512GB',
            'MacBook Pro M2 13 inch 2022 8GB /256GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro M2 13 inch 2022 8GB / 512GB': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'Watch Ultra 2 GPS + Cellular 49mm Titanium Case': 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Watch Series 9 GPS Sport Band (Viền Nhôm, Dây Cao Su) Size M/L - 41mm': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Watch Series 9 GPS Sport Band (Viền Nhôm, Dây Cao Su) Size S/M - 41mm' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Watch Series 9 GPS Sport Band (Viền Nhôm, Dây Cao Su) Size M/L - 45mm' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Watch SE LTE GPS + Cellular Aluminum Case With Sport Band (Viền Nhôm & Dây Cao Su) VN/A 44mm':
                'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'SE GPS + Cellular 40mm viền nhôm dây cao su':
                'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Watch SE GPS Only Aluminum Case With Sport Band (Viền Nhôm & Dây Cao Su) VN/A 44mm':
                'Apple Watch SE GPS 44mm viền nhôm dây cao su',
            'Watch SE GPS 40mm viền nhôm dây cao su':
                'Apple Watch SE GPS 40mm viền nhôm dây cao su',
            'Watch Series 3 GPS Sport Band (Viền Nhôm, Dây Cao Su) 42mm':
                'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Watch Series 3 GPS Sport Band (Viễn Nhôm & Dây Cao Su) 38mm':
                'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'AirPods Pro 2':
                'AirPods Pro 2 2022',
            'AirPods Pro - MLWK3':
                'AirPods Pro 2021',
            'AirPods 3 Hộp sạc Magsafe - MME73':
                'AirPods 3 2021',
            'AirPods 2 - Hộp Sạc Thường':
                'AirPods 2 hộp sạc dây',
            'AirTag (4 Pack)':
                'AirTag - 4 Pack',
            'AirTag (1 Pack)':
                'AirTag - 1 Pack'
        }

        # Convert keys to lowercase using a dictionary comprehension
        tiki_replacement_dict_lower = {key.lower(): value for key, value in tiki_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in tiki_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in tiki_replacement_dict_lower:
                tiki_df.loc[i, "Product_Name"] = tiki_replacement_dict_lower[product_name]

        tiki_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End Tiki

        # 10 start sd
        sd_df = pandas.read_csv(f"../content/{now}/10-sd-{now}.csv", delimiter=";", on_bad_lines='skip')

        sd_not_trade_list = [
            'iPhone 13 256GB', 'iPhone 13 512GB',
           'iPad Pro 12.9 2021 M1 WiFi 5G 256GB', 'iPad Pro 12.9 2021 M1 WiFi 256GB', 'iPad Pro 11 2021 M1 WiFi 5G 128GB',
           'iPad Pro 11 2021 M1 WiFi 5G 256GB', 'iPad Pro 11 2021 M1 WiFi 128GB', 'iPad Pro 11 2021 M1 WiFi 256GB',
           'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su', 'MacBook Air 13" 2020 M1 512GB',
           'iPad Pro 12.9 2021 M1 WiFi 128GB', 'MacBook Pro 16" 2021 M1 Pro 512GB', 'MacBook Pro 16" 2021 M1 Pro 1TB',
           'MacBook Pro 14" 2021 M1 Pro 512GB', 'MacBook Pro 14" 2021 M1 Pro 1TB', 'iPad Pro 11 2022 M2 WiFi 5G 128GB',
           'iPad Pro 12.9 2021 M1 WiFi 5G 128GB', 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
           'MacBook Pro 13" 2020 Touch Bar M1 512GB', 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'iPad Pro 11 2022 M2 WiFi 5G 128GB', 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su'
        ]

        sd_column_names = ['Product_Name', 'Ton_Kho', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Date',
            'Khuyen_Mai']

        # Create a DataFrame with specified columns and fill other columns with 'N/A'
        data = {'Product_Name': sd_not_trade_list}
        for col in sd_column_names[1:]:
            data[col] = ['N/A'] * len(sd_not_trade_list)

        sd_new = pandas.DataFrame(data, columns = sd_column_names)
        sd_df = pandas.concat([sd_new, sd_df], ignore_index = True)

        sd_replacement_dict = {
            "iPhone 12 64GB 64GB": "iPhone 12 64GB",
            "iPhone 12 64GB 128GB": "iPhone 12 128GB",
            "iPhone 11 64GB 64GB": "iPhone 11 64GB",
            "iPhone 11 64GB 128GB": "iPhone 11 128GB",
            "iPhone 12": "iPhone 12 64GB",
            # "iPhone 13": "iPhone 13 128GB",
            "iPhone 13 mini": "iPhone 13 mini 128GB",
            "iPhone 13 Pro": "iPhone 13 Pro 128GB",
            "iPhone SE (2022) 64GB": "iPhone SE 2022 64GB",
            "iPhone SE (2022) 128GB": "iPhone SE 2022 128GB",
            "iPhone SE (2022) 256GB": "iPhone SE 2022 256GB",

            'iPad Pro M4 13 inch Wi-Fi + Cellular': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 13 inch Wi-Fi + Cellular 512GB': 'iPad Pro 13 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 13 inch Wi-Fi': 'iPad Pro 13 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 13 inch Wi-Fi 512GB': 'iPad Pro 13 inch M4 2024 Wifi 512GB',
            'iPad Pro M4 11 inch Wi-Fi + Cellular': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 256GB',
            'iPad Pro M4 11 inch Wi-Fi + Cellular 512GB': 'iPad Pro 11 inch M4 2024 Wifi + Cellular 512GB',
            'iPad Pro M4 11 inch Wi-Fi': 'iPad Pro 11 inch M4 2024 Wifi 256GB',
            'iPad Pro M4 11 inch Wi-Fi 512GB': 'iPad Pro 11 inch M4 2024 Wifi 512GB',
            'iPad Air M2 13 inch Wi-Fi + Cellular': 'iPad Air 13 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air M2 13 inch Wi-Fi + Cellular 256GB': 'iPad Air 13 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air 6 M2 13 inch Wi-Fi': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air M2 13 inch Wi-Fi': 'iPad Air 13 inch M2 2024 Wifi 128GB',
            'iPad Air M2 13 inch Wi-Fi 256GB': 'iPad Air 13 inch M2 2024 Wifi 256GB',
            'iPad Air 6 M2 11 inch Wi-Fi + Cellular': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air M2 11 inch Wi-Fi + Cellular': 'iPad Air 11 inch M2 2024 Wifi + Cellular 128GB',
            'iPad Air 6 M2 11 inch Wi-Fi + Cellular 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air M2 11 inch Wi-Fi + Cellular 256GB': 'iPad Air 11 inch M2 2024 Wifi + Cellular 256GB',
            'iPad Air M2 11 inch Wi-Fi': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch Wi-Fi': 'iPad Air 11 inch M2 2024 Wifi 128GB',
            'iPad Air 6 M2 11 inch Wi-Fi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',
            'iPad Air M2 11 inch Wi-Fi 256GB': 'iPad Air 11 inch M2 2024 Wifi 256GB',

            "iPad Pro M2 12.9 inch WiFi Cellular 128GB": "iPad Pro 12.9 2022 M2 WiFi 5G 128GB",
            "iPad Pro M2 12.9 inch WiFi Cellular 256GB": "iPad Pro 12.9 2022 M2 WiFi 5G 256GB",
            "iPad Pro M2 12.9 inch WiFi 128GB": "iPad Pro 12.9 2022 M2 WiFi 128GB",
            "iPad Pro M2 12.9 inch WiFi 256GB": "iPad Pro 12.9 2022 M2 WiFi 256GB",
            "iPad Pro M2 11 inch WiFi Cellular 128GB": "iPad Pro 11 2022 M2 WiFi 5G 128GB",
            "iPad Pro M2 11 inch WiFi Cellular 256GB": "iPad Pro 11 2022 M2 WiFi 5G 256GB",
            "iPad Pro M2 11 inch WiFi 128GB": "iPad Pro 11 2022 M2 WiFi 128GB",
            "iPad Pro M2 11 inch WiFi 256GB": "iPad Pro 11 2022 M2 WiFi 256GB",
            "iPad Gen 10th 10.9 inch WiFi Cellular 64GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 64GB",
            "iPad Gen 10th 10.9 inch WiFi Cellular 256GB": "iPad Gen 10 2022 10.9 inch WiFi 5G 256GB",
            "iPad Gen 10 th 10.9 inch WiFi 64GB": "iPad Gen 10 2022 10.9 inch WiFi 64GB",
            "iPad Gen 10th 10.9 inch WiFi 256GB": "iPad Gen 10 2022 10.9 inch WiFi 256GB",
            "iPad Pro 12.9 inch (M1, 2021) Wi-Fi + 5G 128GB": "iPad Pro 12.9 2021 M1 WiFi 5G 128GB",
            "iPad Pro 12.9 inch (M1, 2021) Wi-Fi + 5G 256GB": "iPad Pro 12.9 2021 M1 WiFi 5G 256GB",
            "iPad Pro 12.9 inch (M1, 2021) Wi-Fi 128GB": "iPad Pro 12.9 2021 M1 WiFi 128GB",
            "iPad Pro 12.9 inch (M1, 2021) Wi-Fi 256GB": "iPad Pro 12.9 2021 M1 WiFi 256GB",
            "iPad Pro 11 inch (M1, 2021) Wi-Fi + 5G 128GB": "iPad Pro 11 2021 M1 WiFi 5G 128GB",
            "iPad Pro 11 inch (M1, 2021) Wi-Fi + 5G 256GB": "iPad Pro 11 2021 M1 WiFi 5G 256GB",
            "iPad Pro 11 inch (M1, 2021) Wi-Fi 128GB": "iPad Pro 11 2021 M1 WiFi 128GB",
            "iPad Pro 11 inch (M1, 2021) Wi-Fi 256GB": "iPad Pro 11 2021 M1 WiFi 256GB",
            "iPad Air 5 WiFi Cellular 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 64GB",
            "iPad Air 5 WiFi Cellular 256GB": "iPad Air 5 2022 10.9 inch M1 WiFi 5G 256GB",
            "iPad Air 5 WiFi 64GB": "iPad Air 5 2022 10.9 inch M1 WiFi 64GB",
            "iPad Air 5 WiFi 256GB": "iPad Air 5 2022 10.9 inch M1 WiFi 256GB",
            "iPad Air 4 Wi-Fi + 5G 64GB": "iPad Air 10.9 2020 WiFi + Cellular 64GB",
            "iPad Air 4 10.9 inch Wi-Fi + Cellular 256GB": "iPad Air 10.9 2020 WiFi + Cellular 256GB",
            "iPad Air 4 10.9 inch Wi-Fi 64GB": "iPad Air 10.9 2020 WiFi 64GB",
            "iPad Air 4 10.9 inch Wi-Fi 256GB": "iPad Air 10.9 2020 WiFi 256GB",
            "iPad gen 9 10.2 inch WiFi Cellular 64GB": "iPad 10.2 2021 WiFi + Cellular 64GB",
            "iPad gen 9 10.2 inch WiFi Cellular 256GB": "iPad 10.2 2021 WiFi + Cellular 256GB",
            "iPad gen 9 10.2 inch WiFi 64GB": "iPad 10.2 2021 WiFi 64GB",
            "iPad Gen 9th 10.2 inch WiFi 256GB": "iPad 10.2 2021 WiFi 256GB",
            "iPad mini 6 Wi-Fi + 5G": "iPad mini 8.3 2021 WiFi 5G 64GB",
            "iPad mini 6 Wi-Fi + 5G 64GB": "iPad mini 8.3 2021 WiFi 5G 64GB",
            "iPad mini 6 | 256GB Wi-Fi + 5G": "iPad mini 8.3 2021 WiFi 5G 256GB",
            "iPad mini 6 Wi-Fi + 5G 256GB": "iPad mini 8.3 2021 WiFi 5G 256GB",
            "iPad mini 6 Wi-Fi": "iPad mini 8.3 2021 WiFi 64GB",
            "iPad mini 6 Wi-Fi 64GB": "iPad mini 8.3 2021 WiFi 64GB",
            "iPad mini 6 | 256GB Wi-Fi": "iPad mini 8.3 2021 WiFi 256GB",
            "iPad mini 6 Wi-Fi 256GB": "iPad mini 8.3 2021 WiFi 256GB",

            'MacBook Pro 14 inch M3 2023 (8GB RAM| 10 Core GPU| 512GB SSD)': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/512GB',
            'MacBook Pro 14 inch M3 2023 (8GB RAM| 10 Core GPU| 1TB SSD)': 'MacBook Pro 14 2023 M3 8 CPU/10 GPU/8GB/1TB',
            'MacBook Pro 14 inch M3 Pro 2023 (18GB RAM| 14 core GPU| 512GB SSD)': 'MacBook Pro 14 2023 M3 Pro 11 CPU/14 GPU/18GB/512GB',
            'MacBook Pro 14 inch M3 Pro 2023 (18GB RAM| 18 core GPU| 1TB SSD)': 'MacBook Pro 14 2023 M3 Pro 12 CPU/18 GPU/18GB/1TB',
            'MacBook Pro 16 inch M3 Pro 2023 (18GB RAM| 18 core GPU| 512GB SSD)': 'MacBook Pro 16 2023 M3 Pro 12 CPU/18 GPU/18GB/512GB',

            'MacBook Air M3 15 inch 8GB 256GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/256GB',
            'MacBook Air M3 15 inch 8GB 512GB': 'Macbook Air M3 15 2024 8CPU 10GPU/8GB/512GB',
            'MacBook Air M3 13 inch 8GB 256GB': 'Macbook Air M3 13 2024 8CPU 8GPU/8GB/256GB',
            'MacBook Air M3 13 inch 8GB 512GB': 'Macbook Air M3 13 2024 8CPU 10GPU/8GB/512GB',

            'MacBook Air 15 inch M2 (8GB RAM | 256GB SSD)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/256GB',
            'MacBook Air 15 inch M2 (8GB RAM | 512GB SSD)': 'MacBook Air 15 inch M2 2023 8CPU 10GPU 8GB/512GB',
            'MacBook Pro 16 inch M2 Pro (19 Core| 16GB| 512GB)': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/512GB',
            'MacBook Pro 16 inch M2 Pro (19 Core| 16GB| 1TB)': 'MacBook Pro 16 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 14 inch M2 Pro (16 Core| 16GB| 512GB)': 'MacBook Pro 14 2023 M2 Pro 10CPU 16GPU 16GB/512GB',
            'MacBook Pro 14 inch M2 Pro (19 Core| 16GB| 1TB)': 'MacBook Pro 14 2023 M2 Pro 12CPU 19GPU 16GB/1TB',
            'MacBook Pro 16 M1 Pro 16 16GB 512GB': 'MacBook Pro 16" 2021 M1 Pro 512GB',
            'MacBook Pro 16 M1 Pro 16 16GB 1TB': 'MacBook Pro 16" 2021 M1 Pro 1TB',
            'MacBook Pro 14 M1 Pro 16 16GB 512GB': 'MacBook Pro 14" 2021 M1 Pro 512GB',
            'MacBook Pro 14 M1 Pro 16 16GB 1TB': 'MacBook Pro 14" 2021 M1 Pro 1TB',
            'MacBook Pro 13 inch M2 (10 core| 8GB RAM| 256GB SSD)': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 256GB',
            'MacBook Pro 13 inch M2 (10 core| 8GB RAM| 512GB SSD)': 'MacBook Pro M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Air M2 2022 (8GB RAM | 256GB SSD)': 'MacBook Air M2 2022 13 inch 8CPU 8GPU 8GB 256GB',
            'MacBook Air M2 2022 (8GB RAM | 512GB SSD)': 'MacBook Air M2 2022 13 inch 8CPU 10GPU 8GB 512GB',
            'MacBook Pro M1 2020 (8 core GPU| 8GB RAM| 256GB SSD)': 'MacBook Pro 13" 2020 Touch Bar M1 256GB',
            'MacBook Pro M1 2020 8GB 512GB': 'MacBook Pro 13" 2020 Touch Bar M1 512GB',
            'MacBook Air M1 2020 (8GB RAM | 256GB SSD)': 'MacBook Air 13" 2020 M1 256GB',
            'MacBook Air M1 2020 512GB 8GB': 'MacBook Air 13" 2020 M1 512GB',
            'Apple Watch Ultra 2 GPS + Cellular 49mm Ocean Band' : 'Apple Watch Ultra 2 49mm viền Titanium Dây Ocean Band',
            'Apple Watch Series 9 Nhôm (GPS + Cellular) 41mm | Sport Band Sport Band - S/M' : 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS + Cellular) 41mm | Sport Band': 'Apple Watch Series 9 GPS + Cellular 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS + Cellular) 45mm | Sport Band Sport Band - S/M' : 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS + Cellular) 45mm | Sport Band': 'Apple Watch Series 9 GPS + Cellular 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS) 41mm | Sport Band Sport Band - S/M' : 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS) 41mm | Sport Band': 'Apple Watch Series 9 GPS 41mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS) 45mm | Sport Band Sport Band - S/M' : 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'Apple Watch Series 9 Nhôm (GPS) 45mm | Sport Band': 'Apple Watch Series 9 GPS 45mm Viền nhôm Dây cao su cỡ S/M',
            'AirPods Pro 2 (USB-C) 2023' : 'AirPods Pro 2023 USB-C',
            'Apple Watch Series 8 45mm nhôm GPS + Cellular': 'Apple Watch Series 8 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm nhôm GPS + Cellular': 'Apple Watch Series 8 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 8 45mm nhôm GPS': 'Apple Watch Series 8 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 8 41mm nhôm GPS': 'Apple Watch Series 8 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS + Cellular Sport Band size S/M 44mm': 'Apple Watch SE 2 GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS + Cellular Sport Band size S/M 40mm': 'Apple Watch SE 2 GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS Sport Band size S/M 44mm': 'Apple Watch SE 2 GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE 2023 GPS Sport Band size S/M 40mm': 'Apple Watch SE 2 GPS 40mm viền nhôm dây cao su',
            'Apple Watch Series 7 nhôm GPS + Cellular 45mm': 'Apple Watch Series 7 GPS + Cellular 45mm viền nhôm dây cao su',
            'Apple Watch Series 7 Nhôm GPS + Cellular 41mm': 'Apple Watch Series 7 GPS + Cellular 41mm viền nhôm dây cao su',
            'Apple Watch Series 7 Nhôm GPS 45mm': 'Apple Watch Series 7 GPS 45mm viền nhôm dây cao su',
            'Apple Watch Series 7 Nhôm GPS 41mm': 'Apple Watch Series 7 GPS 41mm viền nhôm dây cao su',
            'Apple Watch SE Nhôm GPS + Cellular 44mm': 'Apple Watch SE GPS + Cellular 44mm viền nhôm dây cao su',
            'Apple Watch SE Nhôm GPS + Cellular 40mm': 'Apple Watch SE GPS + Cellular 40mm viền nhôm dây cao su',
            'Apple Watch SE Nhôm GPS 44mm': 'Apple Watch SE GPS 44mm viền nhôm dây cao su',
            'Apple Watch SE Nhôm GPS 40mm': 'Apple Watch SE GPS 40mm viền nhôm dây cao su',
            'Apple Watch Series 3 GPS 42mm': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 Nhôm 42mm': 'Apple Watch Series 3 GPS 42mm viền nhôm dây cao su',
            'Apple Watch Series 3 Nhôm 38mm': 'Apple Watch Series 3 GPS 38mm viền nhôm dây cao su',
            'AirPods Pro 2': 'AirPods Pro 2 2022',
            'AirPods Pro (2021)': 'AirPods Pro 2021',
            'Tai nghe Apple AirPods 3 sạc không dây MagSafe': 'AirPods 3 2021',
            'AirPods 2': 'AirPods 2 hộp sạc dây',
            'Apple AirTag AirTag 4 Pack': 'AirTag - 4 Pack',
            'Apple AirTag AirTag 1 Pack': 'AirTag - 1 Pack'
        }

        # Convert keys to lowercase using a dictionary comprehension
        sd_replacement_dict_lower = {key.lower(): value for key, value in sd_replacement_dict.items()}
        # Iterate through the DataFrame and replace values using the mapping dictionary
        for i, r in sd_df.iterrows():
            product_name = r["Product_Name"].lower()
            if product_name in sd_replacement_dict_lower:
                sd_df.loc[i, "Product_Name"] = sd_replacement_dict_lower[product_name]

        sd_df.drop_duplicates(subset=['Product_Name'], keep='last', inplace=True)

        # End ShopDunk

        # create lists of Product Name
        # fpt_products = fpt_df["Product_Name"].to_list()
        mw_products = mw_df["Product_Name"].to_list()
        tz_products = tz_df["Product_Name"].to_list()
        vt_products = vt_df["Product_Name"].to_list()
        hh_products = hh_df["Product_Name"].to_list()
        ddv_products = ddv_df["Product_Name"].to_list()
        cps_products = cps_df["Product_Name"].to_list()
        Tiki_products = tiki_df["Product_Name"].to_list()
        Shopee_products = shopee_df["Product_Name"].to_list()
        sd_products = sd_df["Product_Name"].to_list()

        def vnpay_fpt(km_FPT):

            # Calculate VNPAY using oc_vnpay_dict
            oc_vnpay_df = pandas.DataFrame.from_dict(oc_vnpay_dict)
            if now <= datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_FPT}', "%Y-%m-%d").date():
                try:
                    for a, b in oc_vnpay_df.iterrows():
                        l = int(
                            b.Range_Low_FPT)
                        h = int(
                            b.Range_High_FPT)
                        if int(km_FPT) >= l and int(km_FPT) < h:
                            max_FPT = int(b.VNPay_Amount_FPT)
                            tt_km_FPT = int(km_FPT) - max_FPT
                        # if the product's revenue is too small, not any VNPay scheme is applied.
                        elif int(km_FPT) < oc_vnpay_df.iloc[0].Range_Low_FPT:
                            tt_km_FPT = km_FPT
                except ValueError:
                    tt_km_FPT = km_FPT
            else:
                try:
                    n_fpt=str(fpt_df[
                                  fpt_df.Product_Name == fpt_item].Thanh_Toan.values[
                                  0])
                    if "VNPAY-QR" in n_fpt:
                        try:
                            nn=n_fpt.split("\n\n")
                            max_FPT=0  # Initialize with a default value
                            for i in nn:
                                if ("VNPAY-QR" in i) and ("đ" in i):
                                    print("---")
                                    print(f"FPT: {i}")
                                    print("---")
                                    try:
                                        percent_FPT=int(i[(i.index("%") - 2):i.index("%")])
                                    except ValueError:
                                        percent_FPT=100

                                    try:
                                        max_raw=i[(i.index("đa") + 3):]
                                        max_FPT=int(max_raw[:max_raw.index("đ")].replace(".", ""))
                                    except ValueError:
                                        try:
                                            max_raw=i[(i.index("giảm") + 5):]
                                            max_FPT=int(max_raw[:max_raw.index("đ")].replace(".", ""))
                                        except ValueError:
                                            try:
                                                max_raw=i[(i.index("ngay") + 5):]
                                                max_FPT=int(max_raw[:max_raw.index("đ")].replace(".", ""))
                                            except ValueError:
                                                pass
                                else:
                                    pass
                        except AttributeError:
                            percent_FPT=0
                            max_FPT=0

                        print(f"percent_FPT: {percent_FPT}")

                        try:
                            tt_km_FPT_1=int(km_FPT) * ((100 - percent_FPT) / 100)
                            tt_km_FPT_2=int(km_FPT) - max_FPT
                            if percent_FPT != 0 and max_FPT != 0:
                                if tt_km_FPT_1 < tt_km_FPT_2:
                                    tt_km_FPT=int(tt_km_FPT_2)
                                else:
                                    tt_km_FPT=int(tt_km_FPT_1)
                            else:
                                tt_km_FPT=tt_km_FPT_2
                        except ValueError:
                            tt_km_FPT=km_FPT
                        print(tt_km_FPT)
                    else:
                        tt_km_FPT=km_FPT
                except ValueError:
                    tt_km_FPT = km_FPT

            return tt_km_FPT


        def vnpay_mw(km_MW):
            pattern=r'₫|\,|soc|\.|đ'  # Define a regex pattern to match '₫', ',', and 'soc'

            # Use regex to replace the specified characters
            km_MW=re.sub(pattern, '', km_MW)

            # Get the promotion details for the given item from the mw_df DataFrame
            promotion_details = str(mw_df[mw_df.Product_Name == mw_item].Khuyen_Mai.values[0]).lower()

            # Convert the gia_khuyen_mai to int datatype
            try:
                gia_khuyen_mai = int(mw_df[mw_df.Product_Name == mw_item].Gia_Khuyen_Mai.to_list()[0]. \
                                     replace(".", "").replace(",", "").replace("đ", "").replace("₫", "").replace("soc", ""))
            except ValueError:
                print("There is some string in gia khuyen mai, therefore, I can not convert it to string")
                gia_khuyen_mai = 0

            if ("qrcode" in promotion_details) or ("vnpay" in promotion_details): #and "soc" not in km_MW:
                for promotion in promotion_details.split("\n"):
                    if ("qrcode" in promotion) or ("vnpay" in promotion):
                        if "%" in promotion:
                            # Calculate the percentage discount
                            try:
                                percent_discount = int(promotion[(promotion.index("%") - 2):promotion.index("%")])
                            except ValueError:
                                percent_discount = 100

                            # Calculate the maximum discount amount
                            try:
                                max_raw_discount = promotion[(promotion.index("thêm") + 5):].strip()
                            except ValueError:
                                try:
                                    max_raw_discount = promotion[(promotion.index("đa") + 3):].strip()
                                except ValueError:
                                    max_raw_discount = ""

                            # Calculate the condition to be applied
                            if "đơn hàng từ" not in promotion:
                                try:
                                    max_discount = int(
                                        (max_raw_discount[:max_raw_discount.index(" ")])
                                        .replace(".", "").replace("k", "000"))
                                except ValueError:
                                    max_discount = 0
                            elif "đơn hàng từ" in promotion:
                                condition = int(promotion[(promotion.index("đơn hàng từ") + 12):(promotion.index("triệu"))]) * 1000000
                                if int(gia_khuyen_mai) >= condition:
                                    max_discount = int(
                                        max_raw_discount[:max_raw_discount.index("đ")].replace(".", "").replace(",", "").replace("k", "000"))
                                else:
                                    max_discount = 0

                        else:
                            try:
                                # Calculate the fixed discount amount
                                max_raw_discount = promotion[(promotion.index("đến") + 4):]
                            except ValueError:
                                try:
                                    max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                except ValueError:
                                    max_raw_discount=promotion[(promotion.index("ngay") + 5):]
                            if "đơn hàng từ" not in promotion:
                                max_discount = int(
                                    max_raw_discount[:max_raw_discount.index(" ")]
                                    .replace(".", "").replace(",", "").replace("đ", ""))
                            elif "đơn hàng từ" in promotion:
                                condition = int(promotion[(promotion.index("đơn hàng từ") + 12):
                                                          (promotion.index("triệu"))]) * 1000000
                                if int(gia_khuyen_mai) >= condition:
                                    max_discount = int(
                                        max_raw_discount[:max_raw_discount.index(" ")]
                                        .replace(".", "").replace(",", "").replace("k", "000"))
                                else:
                                    max_discount = 0

                            percent_discount = 100

                # Calculate the total discount amount
                total_discount_1 = int(km_MW.replace("soc", "")) * ((100 - percent_discount) / 100)
                total_discount_2 = int(km_MW.replace("soc", "")) - max_discount
                total_discount = max(total_discount_1, total_discount_2)
            # elif "soc" in km_MW:
            #     # If there is the word 'soc' in km_mw, remove "soc" from the string
            #     total_discount = km_MW.replace("soc", "")
            else:
                total_discount = km_MW
            return total_discount

        def vnpay_tz(km_TZ):

            pattern=r'₫|\,|soc|\.|đ'  # Define a regex pattern to match '₫', ',', and 'soc'

            # Use regex to replace the specified characters
            km_TZ=re.sub(pattern, '', km_TZ)

            # Check if VNPAYQR is already recorded in Topzone dataframe
            tz_row = tz_df[tz_df.Product_Name == tz_item]
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
                    gia_khuyen_mai = int(tz_row.Gia_Khuyen_Mai.to_list()[0].\
                        replace(".", "").replace(",", "").replace("đ", "").replace("₫", "").replace("soc", ""))
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
                                    max_discount = int(max_raw_discount[:max_raw_discount.index(" ")].replace(".", "").replace(",", "").replace("k", "000"))
                                # if they limit the price of product to have VNPAY discount
                                elif "đơn hàng từ" in promotion:
                                    condition = int(promotion[(promotion.index("đơn hàng từ") + 12):(promotion.index("triệu"))]) * 1000000
                                    if gia_khuyen_mai >= condition:
                                        max_raw_discount = promotion[(promotion.index("đa") + 3):]
                                        if 'k ' in max_raw_discount:
                                            max_discount = int(max_raw_discount[:max_raw_discount.index("k ")]) * 1000
                                        else:
                                            max_discount=int(max_raw_discount[:max_raw_discount.index("đ")].replace(".", ""))

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
                                    condition = int(promotion[(promotion.index("đơn hàng từ") + 12):(promotion.index("triệu"))]) * 1000000
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

            pattern=r'₫|\,|soc|\.|đ'  # Define a regex pattern to match '₫', ',', and 'soc'

            # Use regex to replace the specified characters
            km=re.sub(pattern, '', km)

            # many time, the final price board has .0 at the end, so I need to take this step
            if type(km) == float:
                tt_km_TZ = int(km)
            else:
                tt_km_TZ = km
            oc_vnpay_df = pandas.DataFrame.from_dict(oc_vnpay_dict)
            if now <= datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_MW}', "%Y-%m-%d").date():
                try:
                    for a, b in oc_vnpay_df.iterrows():
                        l = int(
                            b.Range_Low_MW)
                        h = int(
                            b.Range_High_MW)

                        # if the product's revenue is too small, not any VNPay scheme is applied.
                        if int(km) < oc_vnpay_df.iloc[0].Range_Low_MW:
                            tt_km_TZ = km
                            return tt_km_TZ
                        # If it is not too small, move next
                        elif (int(km) >= l) and (int(km) < h):
                            # calculate the amount of VNPAY discount by the amount, not percentage
                            tt_km_TZ = int(km) - int(b.VNPay_Amount_MW)
                            return tt_km_TZ
                        else:
                            pass
                # In some case, the km is just a text
                except ValueError:
                    tt_km_TZ = km
            else:
                tt_km_TZ = km

            return tt_km_TZ

        def vnpay_vt(km_VT):
            if "vnpay" in vt_df[vt_df.Product_Name == vt_item].Khuyen_Mai.values[
                0].lower():
                try:
                    promotions = vt_df[
                        vt_df.Product_Name == vt_item].Khuyen_Mai.values[
                        0].lower().split("\n")

                    for promotion in promotions:
                        if ("vnpay" in promotion) and ("đầu tiên" not in promotion) and ("không kèm khuyến mại vnpay" not in promotion):
                            print("Viettel: ", promotion)

                            try:
                                percent_VT = int(promotion[(promotion.index(
                                    "%") - 2):promotion.index("%")])
                            except ValueError:
                                percent_VT = 5

                            try:
                                max_raw = promotion[
                                          (promotion.index(
                                              "đa") + 3):]
                            except ValueError:
                                try:
                                    max_raw = promotion[
                                              (promotion.index("đến") + 4):]
                                except ValueError:
                                    try:
                                        max_raw=promotion[
                                                (promotion.index("thêm") + 5):]
                                    except ValueError:
                                        try:
                                            max_raw=promotion[
                                                    (promotion.index("giảm ngay") + 10):]
                                        except ValueError:
                                            try:
                                                max_raw=promotion[
                                                        (promotion.index("giảm") + 5):]
                                            except ValueError:
                                                try:
                                                    max_raw=promotion[
                                                            (promotion.index("giá") + 4):]
                                                except ValueError:
                                                    pass
                            try:
                                max_VT = int(max_raw[
                                             :max_raw.index(
                                                 "đ")].replace(
                                    ",", "").replace(".", ""))
                            except ValueError:
                                try:
                                    max_VT=int(max_raw[
                                               :max_raw.index(
                                                   " ")].replace(
                                        ",", "").replace(".", ""))
                                except ValueError:
                                    max_VT = 0

                        else:
                            pass
                except AttributeError:
                    percent_VT = 0
                    max_VT = 0

                try:
                    tt_km_VT_1 = int(km_VT) * ((100 - percent_VT) / 100)
                    tt_km_VT_2 = int(
                        km_VT) - max_VT
                    if tt_km_VT_1 < tt_km_VT_2:
                        tt_km_VT = int(tt_km_VT_2)
                    else:
                        tt_km_VT = int(tt_km_VT_1)
                except ValueError:
                    tt_km_VT = km_VT
            else:
                tt_km_VT = km_VT
            return tt_km_VT

        def vnpay_sd(km_SD):
            # This is the data cell of promotion
            if "flash" in km_SD:
                tt_km_SD = km_SD.replace("flash", "").replace("đ", "")
                return tt_km_SD

            try:
                n_sd = sd_df[sd_df.Product_Name == sd_item].Khuyen_Mai.values[0].lower()
            except AttributeError:
                n_sd = ''

            km_SD=km_SD.replace("đ", "").replace("Giá bán: ", "").replace("Giá cũ: ", "").replace(",", "").replace('₫',
                                                                                                                   '').replace(
                "Giá dự kiến: ", '')
            tt_km_SD=km_SD
            if type(n_sd) != float:
                if (isinstance(n_sd, str) and "vnpay" in n_sd) or (isinstance(n_sd, str) and 'cổng thanh toán' in n_sd):
                    nn = n_sd.split("\n")
                    i=0
                    while i < len(nn):
                        n=nn[i]
                        if ("vnpay" in n) or ('cổng thanh toán' in n) and ("áp dụng sản phẩm từ" not in n) and ("triệu" not in n):
                            if i + 1 < len(nn):
                                n += nn[i + 1]
                                i+=1  # Skip the next element since it has been concatenated
                                print(n)
                            try:
                                max_vnpay_sd = int(n[(n.index("giảm ngay") + 10):(n.index("đ"))].replace(".", "").replace(",", ""))
                            except ValueError:
                                try:
                                    first_index = n.index("đ")
                                    second_index = n.index("đ", first_index + 1)
                                    max_vnpay_sd = int(n[(n.index("giảm đến") + 9):second_index].replace(".", "").replace(",", ""))
                                except ValueError:
                                    try:
                                        max_vnpay_sd = int(n[(n.index("giảm thêm") + 10):(n.index("đ"))].replace(".", "").replace(",", ""))
                                    except ValueError:
                                        try:
                                            max_vnpay_sd = int(n[(n.index("giảm tới") + 9):(n.index("đ"))].replace(".", "").replace(",",  ""))
                                        except ValueError:
                                            try:
                                                max_vnpay_sd=n[(n.index("giảm thêm") + 10):(n.index("₫"))].replace(".",
                                                                                                        "").replace(",",
                                                                                                     "")
                                                print(max_vnpay_sd, "max_vnpay_sd")
                                            except ValueError:
                                                max_vnpay_sd = "please check ShopDunk VNPAY"
                                                print(max_vnpay_sd)
                            print(max_vnpay_sd)
                            tt_km_SD = int(km_SD) - int(max_vnpay_sd)
                        elif ("vnpay" in n) and ("áp dụng sản phẩm từ" in n):

                            if i + 1 < len(nn):
                                n+=nn[i + 1]
                                i+=1  # Skip the next element since it has been concatenated

                            max_vnpay_sd = int(n[(n.index("giảm ngay") + 10):(n.index("đ"))].replace(".", "").replace(",", ""))
                            revenue_condition = int(
                                n[(n.index("áp dụng sản phẩm từ") + 20):(n.rindex("đ"))].replace(".", "").replace(",", ""))
                            if int(km_SD) >= revenue_condition:
                                tt_km_SD = int(km_SD) - max_vnpay_sd
                            else:
                                tt_km_SD = km_SD
                        elif ("vnpay" in n) and ("cho đơn hàng trên" in n):

                            if i + 1 < len(nn):
                                n+=nn[i + 1]
                                i+=1  # Skip the next element since it has been concatenated

                            max_vnpay_sd = int(n[(n.index("giảm") + 5):(n.index("đ"))].replace(".", "").replace(",", ""))
                            revenue_condition = int(
                                n[(n.index("cho đơn hàng trên") + 18):(n.rindex("triệu"))].replace(".", "").replace(",", ""))
                            if int(km_SD) >= revenue_condition:
                                tt_km_SD = int(km_SD) - max_vnpay_sd
                            else:
                                tt_km_SD = km_SD
                        elif ("vnpay" in n) and ("hoá đơn từ" in n):

                            if i + 1 < len(nn):
                                n+=nn[i + 1]
                                i+=1  # Skip the next element since it has been concatenated

                            max_vnpay_sd = int(n[(n.index("giảm") + 5):(n.index("đ"))].replace(".", "").replace(",", ""))
                            revenue_condition = int(
                                n[(n.index("hoá đơn từ") + 11):(n.rindex("triệu"))].replace(".", "").replace(",", ""))
                            if int(km_SD) >= revenue_condition:
                                tt_km_SD = int(km_SD) - max_vnpay_sd
                            else:
                                tt_km_SD = km_SD
                            print(km_SD)
                            print(max_vnpay_sd)
                        i+=1
                else:
                    tt_km_SD = km_SD
            return tt_km_SD

        def vnpay_hh(km_HH):
            # many time, the final price board has .0 at the end, so I need to take this step
            if type(km_HH) == float:
                tt_km_HH = int(km_HH)
            else:
                tt_km_HH = km_HH
            oc_vnpay_df = pandas.DataFrame.from_dict(oc_vnpay_dict)
            if now <= datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_HH}', "%Y-%m-%d").date():
                try:
                    for a, b in oc_vnpay_df.iterrows():
                        l = int(
                            b.Range_Low_HH)
                        h = int(
                            b.Range_High_HH)

                        # if the product's revenue is too small, not any VNPay scheme is applied.
                        if int(km_HH) < oc_vnpay_df.iloc[0].Range_Low_HH:
                            tt_km_HH = km_HH
                            return tt_km_HH
                        # If it is not too small, move next
                        elif int(km_HH) >= l and int(km_HH) < h:
                            max_hh = int(b.VNPay_Amount_HH)
                            # calculate the amount of VNPAY discount by percentage
                            percent_amount = int(b.Percentage_HH.replace("%", "")) * int(km_HH) / 100
                            if percent_amount <= max_hh:
                                tt_km_HH = int(km_HH) - percent_amount
                            else:
                                tt_km_HH = int(km_HH) - max_hh
                            return tt_km_HH
                # In some case, the km_HH is just a text
                except ValueError:
                    tt_km_HH = km_HH
            else:
                tt_km_HH = km_HH

            return tt_km_HH

        def vnpay_cps(km_CPS):
            tt_km_CPS = km_CPS
            oc_vnpay_df = pandas.DataFrame.from_dict(oc_vnpay_dict)
            if now <= datetime.strptime(f'{oc_vnpay_df.iloc[0].Date_CPS}', "%Y-%m-%d").date():
                try:
                    for a, b in oc_vnpay_df.iterrows():
                        l = int(
                            b.Range_Low_CPS)
                        h = int(
                            b.Range_High_CPS)
                        if int(km_CPS) >= l and int(km_CPS) < h:
                            max_cps = int(b.VNPay_Amount_CPS)
                            tt_km_CPS = int(km_CPS) - max_cps
                        # if the product's revenue is too small, not any VNPay scheme is applied.
                        elif int(km_CPS) < oc_vnpay_df.iloc[0].Range_Low_CPS:
                            tt_km_CPS = km_CPS
                except ValueError:
                    tt_km_CPS = km_CPS
            else:
                tt_km_CPS = km_CPS

            return tt_km_CPS

        data_list = []
        for fpt_item in apple_products:
            print(f"1 - fpt: {fpt_item}")
            for mw_item in mw_products:
                if fpt_item in mw_item:
                    print(f"2 - mw: {fpt_item}")
                    for hh_item in hh_products:
                        if fpt_item in hh_item:
                            print(f"3 - hh: {fpt_item}")
                            for ddv_item in ddv_products:
                                if fpt_item in ddv_item:
                                    print(f"4 - ddv: {fpt_item}")
                                    for vt_item in vt_products:
                                        if fpt_item in vt_item:
                                            print(f"5 - vt: {fpt_item}")
                                            for cps_item in cps_products:
                                                if fpt_item in cps_item:
                                                    print(f"6 - cps: {fpt_item}")
                                                    for shopee_item in Shopee_products:
                                                        if fpt_item in shopee_item:
                                                            print(f"7 - shopee: {fpt_item}")
                                                            for tz_item in tz_products:
                                                                if fpt_item in tz_item:
                                                                    print(f"8 - topzone: {fpt_item}")
                                                                    for Tiki_item in Tiki_products:
                                                                        if fpt_item in Tiki_item:
                                                                            print(f"9 - tiki: {fpt_item}")
                                                                            for sd_item in sd_products:
                                                                                if fpt_item in sd_item:
                                                                                    print(f"10 - ShopDunk: {fpt_item}")
                                                                                    name = fpt_df[fpt_df.Product_Name ==
                                                                                               fpt_item].Product_Name.to_list()[0]
                                                                                    ton_FPT = fpt_df[
                                                                                        fpt_df.Product_Name ==
                                                                                        fpt_item].Ton_Kho.to_list()[0]
                                                                                    khuyen_mai_FPT = "KHUYẾN MẠI:\n" + str(fpt_df[
                                                                                        fpt_df.Product_Name ==
                                                                                        fpt_item].Khuyen_Mai.to_list()[0]) + "\n\n--------\nTHANH TOÁN:\n" + str(fpt_df[
                                                                                        fpt_df.Product_Name ==
                                                                                        fpt_item].Thanh_Toan.to_list()[0])
                                                                                    ton_MW = mw_df[
                                                                                        mw_df.Product_Name == mw_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_MW = "KHUYẾN MẠI:\n" + str(mw_df[
                                                                                        mw_df.Product_Name == mw_item].Khuyen_Mai.to_list()[
                                                                                        0]) + "\n\n--------\nƯU ĐÃI THÊM:\n" + str(mw_df[
                                                                                        mw_df.Product_Name == mw_item].Uu_Dai_Them.to_list()[
                                                                                        0]) + str(mw_df[
                                                                                        mw_df.Product_Name == mw_item].Store_Chien.to_list()[
                                                                                        0])
                                                                                    ton_TZ = tz_df[
                                                                                        tz_df.Product_Name == tz_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_TZ = tz_df[
                                                                                        tz_df.Product_Name == tz_item].Khuyen_Mai.to_list()[
                                                                                        0]
                                                                                    ton_VT = vt_df[
                                                                                        vt_df.Product_Name == vt_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_VT = vt_df[
                                                                                        vt_df.Product_Name == vt_item].Khuyen_Mai.to_list()[
                                                                                        0]
                                                                                    ton_SD = sd_df[
                                                                                        sd_df.Product_Name == sd_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_SD = sd_df[
                                                                                        sd_df.Product_Name == sd_item].Khuyen_Mai.to_list()[
                                                                                        0]
                                                                                    ton_HH = hh_df[
                                                                                        hh_df.Product_Name == hh_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_HH = hh_df[
                                                                                        hh_df.Product_Name == hh_item].Khuyen_Mai.to_list()[
                                                                                        0]
                                                                                    ton_DDV = ddv_df[
                                                                                        ddv_df.Product_Name == ddv_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_DDV = ddv_df[
                                                                                        ddv_df.Product_Name == ddv_item].Khuyen_Mai.to_list()[
                                                                                        0]
                                                                                    ton_CPS = cps_df[
                                                                                        cps_df.Product_Name == cps_item].Ton_Kho.to_list()[
                                                                                        0]
                                                                                    khuyen_mai_CPS = "KHUYẾN MẠI:\n" + str(cps_df[
                                                                                        cps_df.Product_Name == cps_item].Khuyen_Mai.to_list()[
                                                                                        0]) +"\n\n--------\n" + str(cps_df[
                                                                                        cps_df.Product_Name == cps_item].Thanh_Toan.to_list()[
                                                                                        0])
                                                                                    ton_Tiki = \
                                                                                        tiki_df[
                                                                                            tiki_df.Product_Name == Tiki_item].Ton_Kho.to_list()[
                                                                                            0]
                                                                                    ton_Shopee = \
                                                                                        shopee_df[
                                                                                            shopee_df.Product_Name == shopee_item].Ton_Kho.to_list()[
                                                                                            0]
                                                                                    if type(fpt_df[fpt_df.Product_Name == fpt_item].Gia_Khuyen_Mai.to_list()[0]) != float:
                                                                                        km_FPT = \
                                                                                            fpt_df[
                                                                                                fpt_df.Product_Name == fpt_item].Gia_Khuyen_Mai.to_list()[
                                                                                                0].replace("₫", "").replace(".","")
                                                                                    else:
                                                                                        km_FPT= \
                                                                                            fpt_df[
                                                                                                fpt_df.Product_Name == fpt_item].Gia_Khuyen_Mai.to_list()[
                                                                                                0]

                                                                                    # Calculate VNPAY in FPT price
                                                                                    tt_km_FPT = vnpay_fpt(km_FPT)

                                                                                    km_MW = mw_df[
                                                                                        mw_df.Product_Name == mw_item].Gia_Khuyen_Mai.to_list()[
                                                                                        0]

                                                                                    # Calculate VNPay in MW price
                                                                                    # tt_km_MW = vnpay_mw(km_MW)
                                                                                    tt_km_MW = vnpay_mw_table(km_MW)
                                                                                    if type(tt_km_MW) == float:
                                                                                        tt_km_MW = round(int(tt_km_MW))

                                                                                    km_TZ = \
                                                                                        tz_df[
                                                                                            tz_df.Product_Name == tz_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0]

                                                                                    # Calculate VNPAY in TopZone price
                                                                                    tt_km_TZ = vnpay_tz(km_TZ)
                                                                                    # tt_km_TZ = vnpay_mw_table(km_TZ)
                                                                                    if type(tt_km_TZ) == float:
                                                                                        tt_km_TZ = round(int(tt_km_TZ))

                                                                                    km_VT = vt_df[
                                                                                        vt_df.Product_Name == vt_item].Gia_Khuyen_Mai.to_list()[
                                                                                        0].replace("Tạm hết hàng",
                                                                                                   "temporary OOS").replace("₫",
                                                                                                                            "").replace(".","")
                                                                                    # Calculate VNPAY in Viettel price
                                                                                    tt_km_VT = vnpay_vt(km_VT)

                                                                                    km_SD = sd_df[
                                                                                        sd_df.Product_Name == sd_item].Gia_Khuyen_Mai.to_list()[
                                                                                        0].replace("₫","").replace(".","").replace("đ","")
                                                                                    # Calculate VNPay in ShopDunk price
                                                                                    tt_km_SD = vnpay_sd(km_SD)

                                                                                    km_HH = \
                                                                                        hh_df[
                                                                                            hh_df.Product_Name == hh_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0]
                                                                                    if type(km_HH) == float:
                                                                                        km_HH = int(km_HH)
                                                                                    # Calculate VNPay in HoangHa price
                                                                                    tt_km_HH = vnpay_hh(km_HH)
                                                                                    if type(tt_km_HH) == float:
                                                                                        tt_km_HH = round(int(tt_km_HH))

                                                                                    km_DDV = \
                                                                                        ddv_df[
                                                                                            ddv_df.Product_Name == ddv_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0]
                                                                                    # if type(km_DDV) != float:
                                                                                    km_DDV.replace("₫", "").replace(".","")

                                                                                    km_CPS = \
                                                                                        cps_df[
                                                                                            cps_df.Product_Name == cps_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0].replace("₫", "").replace(".","").replace("đ", "")
                                                                                    # Calculate VNPay in HoangHa price
                                                                                    tt_km_CPS = vnpay_cps(km_CPS)

                                                                                    km_Tiki = \
                                                                                        tiki_df[
                                                                                            tiki_df.Product_Name == Tiki_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0]
                                                                                    km_Shopee = \
                                                                                        shopee_df[
                                                                                            shopee_df.Product_Name == shopee_item].Gia_Khuyen_Mai.to_list()[
                                                                                            0].replace("₫", "").replace(".","")
                                                                                    fpt_link = fpt_df[
                                                                                            fpt_df.Product_Name == fpt_item].Link.to_list()[
                                                                                            0]
                                                                                    mw_link = mw_df[
                                                                                            mw_df.Product_Name == mw_item].Link.to_list()[
                                                                                            0]
                                                                                    tz_link = tz_df[
                                                                                            tz_df.Product_Name == tz_item].Link.to_list()[
                                                                                            0]
                                                                                    vt_link=vt_df[
                                                                                        vt_df.Product_Name == vt_item].Link.to_list()[
                                                                                        0]
                                                                                    sd_link=sd_df[
                                                                                        sd_df.Product_Name == sd_item].Link.to_list()[
                                                                                        0]
                                                                                    hh_link=hh_df[
                                                                                        hh_df.Product_Name == hh_item].Link.to_list()[
                                                                                        0]
                                                                                    ddv_link=ddv_df[
                                                                                        ddv_df.Product_Name == ddv_item].Link.to_list()[
                                                                                        0]
                                                                                    cps_link=cps_df[
                                                                                        cps_df.Product_Name == cps_item].Link.to_list()[
                                                                                        0]
                                                                                    tiki_link=tiki_df[
                                                                                        tiki_df.Product_Name == Tiki_item].Link.to_list()[
                                                                                        0]
                                                                                    shopee_link=shopee_df[
                                                                                        shopee_df.Product_Name == shopee_item].Link.to_list()[
                                                                                        0]

                                                                                    new_data = {"Product Name": name,
                                                                                                "Stock @ FPT": ton_FPT,
                                                                                                "Stock @ MW": ton_MW,
                                                                                                "Stock @ TopZone": ton_TZ,
                                                                                                "Stock @ VT": ton_VT,
                                                                                                "Stock @ SD": ton_SD,
                                                                                                "Stock @ HH": ton_HH,
                                                                                                "Stock @ DDV": ton_DDV,
                                                                                                "Stock @ CPS": ton_CPS,
                                                                                                "Stock @ Tiki": ton_Tiki,
                                                                                                "Stock @ Shopee": ton_Shopee,

                                                                                                "Link @ FPT": fpt_link,
                                                                                                "Link @ MW": mw_link,
                                                                                                "Link @ TopZone": tz_link,
                                                                                                "Link @ VT": vt_link,
                                                                                                "Link @ SD": sd_link,
                                                                                                "Link @ HH": hh_link,
                                                                                                "Link @ DDV": ddv_link,
                                                                                                "Link @ CPS": cps_link,
                                                                                                "Link @ Tiki": tiki_link,
                                                                                                "Link @ Shopee": shopee_link,

                                                                                                "Promo Price @ FPT": km_FPT,
                                                                                                "Promo Price @ FPT + VNPay": tt_km_FPT,
                                                                                                "Promo Price @ MW": km_MW.replace(
                                                                                                    "soc", ""),
                                                                                                "Promo Price @ MW + VNPay": tt_km_MW,
                                                                                                "Promo Price @ TopZone": km_TZ,
                                                                                                "Promo Price @ TZ + VNPay": tt_km_TZ,
                                                                                                "Promo Price @ VT": km_VT,
                                                                                                "Promo Price @ VT + VNPay": tt_km_VT,
                                                                                                "Promo Price @ SD": km_SD.replace("flash", ""),
                                                                                                "Promo Price @ SD + VNPay": tt_km_SD,
                                                                                                "Promo Price @ HH": km_HH,
                                                                                                "Promo Price @ HH + VNPay": tt_km_HH,
                                                                                                "Promo Price @ DDV": km_DDV,
                                                                                                "Promo Price @ CPS": km_CPS,
                                                                                                "Promo Price @ CPS + VNPAY": tt_km_CPS,
                                                                                                "Promo Price @ Tiki": km_Tiki,
                                                                                                "Promo Price @ Shopee": km_Shopee,
                                                                                                "Promo @ FPT": khuyen_mai_FPT,
                                                                                                "Promo @ MW": khuyen_mai_MW,
                                                                                                "Promo @ TopZone": khuyen_mai_TZ,
                                                                                                "Promo @ VT": khuyen_mai_VT,
                                                                                                "Promo @ SD": khuyen_mai_SD,
                                                                                                "Promo @ HH": khuyen_mai_HH,
                                                                                                "Promo @ DDV": khuyen_mai_DDV,
                                                                                                "Promo @ CPS": khuyen_mai_CPS,
                                                                                                ""
                                                                                                "Date": now}
                                                                                    data_list.append(new_data)
        df=pandas.DataFrame(data = data_list,
                            columns = ["Product Name", "Promo Price @ FPT",
                                       "Promo Price @ FPT + VNPay", "Promo Price @ MW", "Promo Price @ MW + VNPay",
                                       "Promo Price @ TopZone", "Promo Price @ TZ + VNPay",
                                       "Promo Price @ VT", "Promo Price @ VT + VNPay", "Promo Price @ SD",
                                       "Promo Price @ SD + VNPay", "Promo Price @ HH", "Promo Price @ HH + VNPay",
                                       "Promo Price @ DDV", "Promo Price @ CPS", "Promo Price @ CPS + VNPAY",
                                       "Promo Price @ Tiki",
                                       "Promo Price @ Shopee", "Stock @ FPT", "Stock @ MW", "Stock @ TopZone",
                                       "Stock @ VT", "Stock @ SD", "Stock @ HH", "Stock @ DDV", "Stock @ CPS",
                                       "Stock @ Tiki", "Stock @ Shopee", "Promo @ FPT", "Promo @ MW",
                                       "Promo @ TopZone", "Promo @ VT", "Promo @ SD", "Promo @ HH", "Promo @ DDV",
                                       "Promo @ CPS", "Link @ FPT", "Link @ MW", "Link @ TopZone", "Link @ VT",
                                       "Link @ SD", "Link @ HH", "Link @ DDV", "Link @ CPS", "Link @ Tiki",
                                       "Link @ Shopee", "Date"])

        df.insert(loc = 1, column = "Lowest Price", value = int)
        test = []
        for i, r in df.iterrows():
            list_check = []
            for ii in r[2:18].to_list():
                try:
                    ii = int(ii)
                    list_check.append(int(ii))
                except ValueError:
                    pass

            # remove the value 0 from the list_check
            list_check = [x for x in list_check if x != 0]
            try:
                r["Lowest Price"] = int(min(list_check))
                test.append(r)
            except ValueError:
                r["Lowest Price"] = "EOL"
                test.append(r)

        new_df = pandas.DataFrame(data=test)
        new_df['Stock Status']=new_df.filter(like = 'Stock').apply(lambda row: (row == 'Yes').sum(), axis = 1)
        # Remove the new column from the end
        columns=list(new_df.columns)
        columns.remove('Stock Status')
        # Insert the new column at the 20th position (index 19)
        columns.insert(19, 'Stock Status')
        # Reorder the DataFrame columns
        new_df=new_df[columns]
        choices=['Low', 'Medium', 'High']
        new_df['Stock Status'] = pandas.cut(new_df['Stock Status'], bins = [0, 4, 6, 9], labels = choices,
                                            right = True)
        if not os.path.exists(f"../content/{now}"):
            os.makedirs(f"../content/{now}")
        new_df.to_csv(f"../content/{now}/Daily Promo Pricing - {now_1}.csv", sep=";", index=False)

    def run_after_enough_data(self):
        # https://stackoverflow.com/questions/2785821/is-there-an-easy-way-in-python-to-wait-until-certain-condition-is-true
        from waiting import wait
        if not os.path.exists(f"../content/{now}"):
            os.makedirs(f"../content/{now}")
        file_num = 0
        def is_something_ready(file_num):
            source_dir = f"../content/{now}"

            file_names = os.listdir(source_dir)
            print(len(file_names))
            for i in file_names:
                if f"1-fpt-{now}.csv" == i:
                # if f"1-fpt" in i:
                    file_num += 1
                if f"2-mw-{now}.csv" == i:
                # if f"2-mw" in i:
                    file_num += 1
                if f"3-hh-{now}.csv" == i:
                # if f"3-hh" in i:
                    file_num += 1
                if f"4-ddv-{now}.csv" == i:
                # if f"4-ddv" in i:
                    file_num += 1
                if f"5-vt-{now}.csv" == i:
                # if f"5-vt" in i:
                    file_num += 1
                if f"6-cps-{now}.csv" == i:
                # if f"6-cps" in i:
                    file_num += 1
                if f"7-shopee-{now}.csv" == i:
                # if f"7-shopee" in i:
                    file_num += 1
                if f"8-topzone-{now}.csv" == i:
                # if f"8-topzone" in i:
                    file_num += 1
                if f"9-tiki-{now}.csv" == i:
                # if f"9-tiki" in i:
                    file_num += 1
                if f"10-sd-{now}.csv" == i:
                # if f"10-sd" in i:
                    file_num += 1
            if file_num == 10:
                return True
            return False

        wait(lambda: is_something_ready(file_num))
        Apple().create_Apple_dashboard_2()
        Apple().check()


Apple().run_after_enough_data()
# Apple().create_Apple_dashboard_2()

