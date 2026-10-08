"""
FPT Inventory Intelligence - Executive Inference & Analytics Engine
===================================================================
Chức năng:
1. Đọc dữ liệu snapshot mới nhất từ data/raw/ (fpt_inventory_deep_latest.json).
2. Phân loại sức khỏe tồn kho (Healthy, Low Stock Warning, Critical Stockout).
3. Đánh giá phân bổ tồn kho vùng miền (TP.HCM vs Hà Nội vs 32 tỉnh còn lại).
4. So sánh tỷ trọng hệ thống đại chúng (FPT Shop) vs chuỗi cao cấp Apple (F.Studio by FPT).
5. Xuất báo cáo điều hành Markdown (Executive Daily Report) và JSON chỉ số phân tích.
"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

# Đảm bảo PROJECT_ROOT độc lập
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import RAW_DATA_DIR, PREDICTIONS_DIR, REPORTS_DIR


def format_currency(val: int) -> str:
    """Định dạng tiền tệ VNĐ."""
    return f"{val:,.0f} đ".replace(",", ".")


class FPTInventoryInferenceEngine:
    """Bộ máy suy luận và phân tích điều hành tồn kho FPT & F.Studio."""

    def __init__(self, raw_json_path: Optional[str] = None):
        if not raw_json_path:
            raw_json_path = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")
        self.raw_json_path = raw_json_path
        self.data: List[Dict[str, Any]] = []

        if os.path.exists(self.raw_json_path):
            with open(self.raw_json_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            print(f"⚠️ Không tìm thấy file dữ liệu: {self.raw_json_path}")

    def analyze(self) -> Dict[str, Any]:
        """Thực thi phân tích định lượng toàn bộ dữ liệu SKU."""
        if not self.data:
            return {"error": "No data available"}

        total_skus = len(self.data)
        in_stock_skus = []
        out_of_stock_skus = []
        low_stock_skus = []
        safe_skus = []

        fstudio_available_skus = []
        category_stats: Dict[str, Dict[str, int]] = {}

        total_inventory_units = 0
        total_hcm_store_presence = 0
        total_hn_store_presence = 0

        for item in self.data:
            cat = item.get("category", "Other")
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "in_stock": 0, "out_of_stock": 0, "total_units": 0}

            category_stats[cat]["total"] += 1
            tot_qty = item.get("total_inventory_quantity", 0)
            fpt_stores = item.get("total_fpt_stores", 0)
            fstudio_stores = item.get("total_fstudio_stores", 0)
            hcm = item.get("hcm_stores", 0)
            hn = item.get("hn_stores", 0)

            total_inventory_units += tot_qty
            total_hcm_store_presence += hcm
            total_hn_store_presence += hn

            is_in_stock = (tot_qty > 0) or (fpt_stores > 0) or (fstudio_stores > 0)

            if is_in_stock:
                category_stats[cat]["in_stock"] += 1
                category_stats[cat]["total_units"] += tot_qty
                in_stock_skus.append(item)

                if fstudio_stores > 0:
                    fstudio_available_skus.append(item)

                # Đánh giá mức độ an toàn: Dưới 10 shop hoặc dưới 20 máy là cảnh báo
                if tot_qty < 20 or fpt_stores < 10:
                    low_stock_skus.append(item)
                else:
                    safe_skus.append(item)
            else:
                category_stats[cat]["out_of_stock"] += 1
                out_of_stock_skus.append(item)

        # Top SKU tồn nhiều nhất
        top_stocked = sorted(in_stock_skus, key=lambda x: x.get("total_inventory_quantity", 0), reverse=True)[:8]

        # Top SKU rủi ro cạn hàng cao nhất (có hàng nhưng số lượng siêu ít)
        critical_low = sorted(low_stock_skus, key=lambda x: (x.get("total_inventory_quantity", 0), x.get("total_fpt_stores", 0)))[:8]

        summary = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_skus": total_skus,
            "in_stock_count": len(in_stock_skus),
            "out_of_stock_count": len(out_of_stock_skus),
            "stock_rate_pct": round(len(in_stock_skus) / total_skus * 100, 1) if total_skus > 0 else 0,
            "total_inventory_units": total_inventory_units,
            "low_stock_count": len(low_stock_skus),
            "safe_stock_count": len(safe_skus),
            "fstudio_available_count": len(fstudio_available_skus),
            "category_breakdown": category_stats,
            "regional": {
                "hcm_presence": total_hcm_store_presence,
                "hn_presence": total_hn_store_presence
            },
            "top_stocked_skus": top_stocked,
            "critical_low_skus": critical_low
        }
        return summary

    def generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """Tạo báo cáo điều hành chuẩn Markdown."""
        now_str = summary["timestamp"]
        lines = []
        lines.append("# 📊 BÁO CÁO ĐIỀU HÀNH TỒN KHO FPT RETAIL & F.STUDIO")
        lines.append(f"**Thời gian phân tích:** `{now_str}`  ")
        lines.append(f"**Phạm vi:** 602 Siêu thị FPT Shop & F.Studio toàn quốc (34 Tỉnh/Thành GSO)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 1. Executive Summary Table
        lines.append("## 1. TỔNG QUAN CHỈ SỐ GROUND-TRUTH TOÀN HỆ THỐNG")
        lines.append("")
        lines.append("| Chỉ Số Giám Sát | Giá Trị Thực Tế | Trạng Thái / Đánh Giá |")
        lines.append("| :--- | :--- | :--- |")
        lines.append(f"| **Tổng số biến thể Apple SKU theo dõi** | `{summary['total_skus']}` SKU | Bao phủ iPhone, iPad, Mac, Watch, AirPods |")
        lines.append(f"| **Tỷ lệ biến thể đang còn hàng** | **{summary['stock_rate_pct']}%** (`{summary['in_stock_count']}` SKU) | {'🟢 Sẵn sàng cung ứng tốt' if summary['stock_rate_pct'] >= 60 else '🟡 Tồn kho phân hóa'} |")
        lines.append(f"| **Biến thể đứt hàng hoàn toàn (Zero Stock)** | `{summary['out_of_stock_count']}` SKU | Hết sạch tại kho trung tâm & tất cả quầy |")
        lines.append(f"| **Tổng số lượng máy tồn kho thực tế** | **{summary['total_inventory_units']:,}** máy | Số lượng khả dụng tức thời |")
        lines.append(f"| **Biến thể hiện diện tại F.Studio by FPT** | `{summary['fstudio_available_count']}` SKU | Chuỗi ủy quyền Apple cao cấp |")
        lines.append(f"| **Số SKU cảnh báo rủi ro cạn hàng (< 20 máy)** | `{summary['low_stock_count']}` SKU | Cần kích hoạt bổ sung điều chuyển |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 2. Phân tích theo từng ngành hàng
        lines.append("## 2. HIỆN TRẠNG TỒN KHO THEO NGÀNH HÀNG APPLE")
        lines.append("")
        lines.append("| Ngành Hàng | Tổng SKU | Còn Hàng | Đứt Hàng | Tỷ Lệ Sẵn Hàng | Tổng Máy Sẵn Có |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for cat, stats in summary["category_breakdown"].items():
            rate = round(stats["in_stock"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
            lines.append(f"| **{cat}** | {stats['total']} | {stats['in_stock']} | {stats['out_of_stock']} | **{rate}%** | {stats['total_units']:,} máy |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 3. Phân bổ địa lý vùng miền
        lines.append("## 3. PHÂN BỔ ĐỊA LÝ & KÊNH BÁN LẺ")
        lines.append("")
        lines.append(f"- **Thị trường TP. Hồ Chí Minh:** Có tổng cộng `{summary['regional']['hcm_presence']}` lượt shop còn máy phục vụ khách lấy ngay.")
        lines.append(f"- **Thị trường TP. Hà Nội:** Có tổng cộng `{summary['regional']['hn_presence']}` lượt shop còn máy.")
        lines.append(f"- **Kênh chuyên biệt Apple (F.Studio by FPT):** `{summary['fstudio_available_count']}` biến thể đang sẵn sàng phục vụ tại chuỗi F.Studio.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 4. Cảnh báo rủi ro cạn hàng
        lines.append("## 4. 🚨 CẢNH BÁO RỦI RO CẠN HÀNG (CRITICAL LOW STOCK)")
        lines.append("")
        lines.append("| Tên Sản Phẩm / Biến Thể | Mã SKU | Tồn Tổng | FPT Shop | F.Studio | Giá Bán |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for item in summary["critical_low_skus"]:
            lines.append(f"| [{item.get('sku_name', '')[:42]}]({item.get('url', '#')}) | `{item.get('sku_code')}` | **{item.get('total_inventory_quantity', 0)}** | {item.get('total_fpt_stores', 0)} shop | {item.get('total_fstudio_stores', 0)} shop | {format_currency(item.get('price', 0))} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 5. Top SKU có lượng tồn dồi dào nhất
        lines.append("## 5. 📦 TOP BIẾN THỂ CÓ TRỮ LƯỢNG HÀNG CAO NHẤT (HERO PRODUCTS)")
        lines.append("")
        lines.append("| Tên Sản Phẩm | Mã SKU | Tồn Tổng | FPT Shop | TP.HCM | Hà Nội | Giá Bán |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        for item in summary["top_stocked_skus"]:
            lines.append(f"| [{item.get('sku_name', '')[:40]}]({item.get('url', '#')}) | `{item.get('sku_code')}` | **{item.get('total_inventory_quantity', 0):,}** máy | {item.get('total_fpt_stores', 0)} shop | {item.get('hcm_stores', 0)} shop | {item.get('hn_stores', 0)} shop | {format_currency(item.get('price', 0))} |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Báo cáo được khởi tạo tự động bởi FPT Inventory Intelligence Engine (Microservice Model).*")
        return "\n".join(lines)

    def execute_and_save(self) -> str:
        """Thực thi toàn trình và lưu trữ các file báo cáo."""
        summary = self.analyze()
        if "error" in summary:
            print(f"❌ Phân tích thất bại: {summary['error']}")
            return ""

        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        
        # Lưu file JSON suy luận
        pred_file = os.path.join(PREDICTIONS_DIR, f"fpt_inventory_inference_{timestamp_str}.json")
        pred_latest = os.path.join(PREDICTIONS_DIR, "fpt_inventory_inference_latest.json")
        with open(pred_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        shutil.copyfile(pred_file, pred_latest)

        # Lưu file Markdown báo cáo điều hành
        md_content = self.generate_markdown_report(summary)
        report_file = os.path.join(REPORTS_DIR, f"daily_report_{timestamp_str}.md")
        report_latest = os.path.join(REPORTS_DIR, "daily_report_latest.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        shutil.copyfile(report_file, report_latest)

        print(f"✅ Đã tạo báo cáo điều hành:")
        print(f"   • Markdown: {report_file}")
        print(f"   • Markdown Latest: {report_latest}")
        print(f"   • JSON Analytics: {pred_file}")

        # Tự động xuất Dashboard HTML tương tác & Store Inventory Viewer
        try:
            from src.inference.dashboard_generator import generate_html_dashboard
            from src.inference.store_viewer_generator import generate_store_viewer_html
            dashboard_file = generate_html_dashboard(self.raw_json_path, pred_latest)
            viewer_file = generate_store_viewer_html()
            print(f"   • Dashboard Tổng quan: {dashboard_file}")
            print(f"   • Store Viewer Chi tiết : {viewer_file}")
        except Exception as e:
            print(f"⚠️ Lỗi xuất HTML: {e}")

        return report_latest


if __name__ == "__main__":
    engine = FPTInventoryInferenceEngine()
    engine.execute_and_save()
