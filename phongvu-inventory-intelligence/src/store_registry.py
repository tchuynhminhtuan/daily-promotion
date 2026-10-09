"""
Phong Vu Official Showroom Registry.
Lists key Phong Vu retail stores nationwide with region, province, and addresses.
"""

from typing import List, Dict, Any, Optional

PHONGVU_SHOWROOMS: List[Dict[str, Any]] = [
    # --- TP. HỒ CHÍ MINH ---
    {
        "id": "PV_HCM_01",
        "name": "Phong Vũ Hoàng Hoa Thám",
        "address": "Số 2 Hoàng Hoa Thám, P.12, Q. Tân Bình, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    {
        "id": "PV_HCM_02",
        "name": "Phong Vũ Cách Mạng Tháng 8",
        "address": "264 Nguyễn Thị Minh Khai, P. Võ Thị Sáu, Q.3, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    {
        "id": "PV_HCM_03",
        "name": "Phong Vũ Trần Hưng Đạo",
        "address": "125 Trần Hưng Đạo, P. Cầu Ông Lãnh, Q.1, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    {
        "id": "PV_HCM_04",
        "name": "Phong Vũ Hậu Giang",
        "address": "1081 Hậu Giang, P.11, Q.6, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    {
        "id": "PV_HCM_05",
        "name": "Phong Vũ Quang Trung",
        "address": "1A Quang Trung, P.10, Q. Gò Vấp, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    {
        "id": "PV_HCM_06",
        "name": "Phong Vũ Lê Văn Việt",
        "address": "204 Lê Văn Việt, P. Tăng Nhơn Phú B, TP. Thủ Đức, TP.HCM",
        "province": "Hồ Chí Minh",
        "province_code": "79",
        "region": "Miền Nam",
        "phone": "028 7301 3878",
    },
    # --- HÀ NỘI ---
    {
        "id": "PV_HN_01",
        "name": "Phong Vũ Thái Hà",
        "address": "Số 1 Phố Thái Hà, P. Trung Liệt, Q. Đống Đa, Hà Nội",
        "province": "Hà Nội",
        "province_code": "01",
        "region": "Miền Bắc",
        "phone": "024 7301 3878",
    },
    {
        "id": "PV_HN_02",
        "name": "Phong Vũ Trần Đại Nghĩa",
        "address": "2A Trần Đại Nghĩa, P. Đồng Tâm, Q. Hai Bà Trưng, Hà Nội",
        "province": "Hà Nội",
        "province_code": "01",
        "region": "Miền Bắc",
        "phone": "024 7301 3878",
    },
    {
        "id": "PV_HN_03",
        "name": "Phong Vũ Cầu Giấy",
        "address": "Tầng 1, Tòa nhà Golden Park, Số 2 Phạm Văn Bạch, Q. Cầu Giấy, Hà Nội",
        "province": "Hà Nội",
        "province_code": "01",
        "region": "Miền Bắc",
        "phone": "024 7301 3878",
    },
    {
        "id": "PV_HN_04",
        "name": "Phong Vũ Hà Đông",
        "address": "Số 463 Quang Trung, P. Phú La, Q. Hà Đông, Hà Nội",
        "province": "Hà Nội",
        "province_code": "01",
        "region": "Miền Bắc",
        "phone": "024 7301 3878",
    },
    # --- ĐÀ NẴNG ---
    {
        "id": "PV_DN_01",
        "name": "Phong Vũ Nguyễn Văn Linh",
        "address": "Số 16 Nguyễn Văn Linh, P. Nam Dương, Q. Hải Châu, Đà Nẵng",
        "province": "Đà Nẵng",
        "province_code": "48",
        "region": "Miền Trung",
        "phone": "0236 730 3878",
    },
    # --- CẦN THƠ ---
    {
        "id": "PV_CT_01",
        "name": "Phong Vũ 30 Tháng 4",
        "address": "209 Đường 30/4, P. Xuân Khánh, Q. Ninh Kiều, Cần Thơ",
        "province": "Cần Thơ",
        "province_code": "92",
        "region": "Miền Nam",
        "phone": "0292 730 3878",
    },
    # --- HẢI PHÒNG ---
    {
        "id": "PV_HP_01",
        "name": "Phong Vũ Lạch Tray",
        "address": "Số 204 Lạch Tray, P. Đằng Giang, Q. Ngô Quyền, Hải Phòng",
        "province": "Hải Phòng",
        "province_code": "31",
        "region": "Miền Bắc",
        "phone": "0225 730 3878",
    },
    # --- BÌNH DƯƠNG ---
    {
        "id": "PV_BD_01",
        "name": "Phong Vũ Thủ Dầu Một",
        "address": "Số 431 Đại lộ Bình Dương, P. Phú Cường, TP. Thủ Dầu Một, Bình Dương",
        "province": "Bình Dương",
        "province_code": "74",
        "region": "Miền Nam",
        "phone": "0274 730 3878",
    },
    # --- ĐỒNG NAI ---
    {
        "id": "PV_DNI_01",
        "name": "Phong Vũ Biên Hòa",
        "address": "Số 262 Phạm Văn Thuận, P. Thống Nhất, TP. Biên Hòa, Đồng Nai",
        "province": "Đồng Nai",
        "province_code": "75",
        "region": "Miền Nam",
        "phone": "0251 730 3878",
    },
    # --- VŨNG TÀU ---
    {
        "id": "PV_VT_01",
        "name": "Phong Vũ Vũng Tàu",
        "address": "Số 328 Ba Cu, P.3, TP. Vũng Tàu, Bà Rịa - Vũng Tàu",
        "province": "Bà Rịa - Vũng Tàu",
        "province_code": "77",
        "region": "Miền Nam",
        "phone": "0254 730 3878",
    },
]


class PhongVuStoreRegistry:
    def __init__(self):
        self._stores = PHONGVU_SHOWROOMS

    def all_stores(self) -> List[Dict[str, Any]]:
        return self._stores

    def get_by_id(self, store_id: str) -> Optional[Dict[str, Any]]:
        for s in self._stores:
            if s["id"].lower() == store_id.lower():
                return s
        return None

    def get_by_province(self, province_name_or_code: str) -> List[Dict[str, Any]]:
        query = province_name_or_code.lower()
        return [
            s for s in self._stores
            if s["province_code"] == query or query in s["province"].lower()
        ]

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [
            s for s in self._stores
            if q in s["name"].lower() or q in s["address"].lower() or q in s["province"].lower()
        ]
