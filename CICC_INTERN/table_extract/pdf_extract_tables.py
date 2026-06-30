# -*- coding: utf-8 -*-
import fitz
import os
import argparse
import pandas as pd
import json
from config import SCREENSHOT_OUTPUT_DIR

def get_table_html_flag(block):
    """和 classify 脚本完全一致：只处理有 HTML 的有效表格"""
    has_html = False
    for b in block.get("blocks", []):
        if b.get("type") == "table_body":
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s.get("type") == "table" and s.get("html"):
                        has_html = True
                        break
                if has_html:
                    break
            if has_html:
                break
    return has_html

def screenshot_pdf_tables(pdf_path, output_dir, ann_id):
    # ==================== 自动识别文件类型 ====================
    core = ann_id.split("-")[0]
    is_full = ann_id == core          # 完整文件：201
    is_part1 = ann_id.endswith("-1")   # 拆分1：201-1
    is_part2 = ann_id.endswith("-2")   # 拆分2：201-2

    # 输出文件夹
    final_output_dir = os.path.join(output_dir, f"{core}_pdf_tables")
    os.makedirs(final_output_dir, exist_ok=True)

    # ==================== 1. 读取 Excel（唯一序号来源） ====================
    excel_path = f"excel_output/{core}.xlsx"
    if not os.path.exists(excel_path):
        print(f"❌ 错误：请先运行 classify 生成 {excel_path}")
        return

    df = pd.read_excel(excel_path).sort_values("UID").reset_index(drop=True)
    excel_list = df.to_dict("records")
    print(f"✅ 读取 Excel 成功：共 {len(excel_list)} 个表格，以 UID 为准")

    # ==================== 2. 读取当前文件的所有有效表格 ====================
    json_path = pdf_path.replace(".pdf", ".json").replace("pdf/", "json_data/")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    current_tables = []
    for page in data["pdf_info"]:
        page_idx = page["page_idx"]
        for block in page.get("para_blocks", []):
            if block.get("type") == "table" and get_table_html_flag(block):
                current_tables.append({
                    "page_idx": page_idx,
                    "bbox": block["bbox"]
                })

    total = len(current_tables)
    print(f"ℹ️ 当前文件 {ann_id} 有效表格：{total} 个")

    # ==================== 3. 计算起始位置（最关键逻辑） ====================
    start_index = 0
    if is_part2:
        # 自动数 -1 文件有多少张，从下一张开始
        part1_json = json_path.replace("-2", "-1")
        if os.path.exists(part1_json):
            with open(part1_json, "r", encoding="utf-8") as f1:
                data1 = json.load(f1)
            cnt = 0
            for p in data1["pdf_info"]:
                for b in p.get("para_blocks", []):
                    if b.get("type") == "table" and get_table_html_flag(b):
                        cnt += 1
            start_index = cnt

    # ==================== 4. 按全局顺序 1:1 截图（永不丢失） ====================
    doc = fitz.open(pdf_path)
    success = 0

    for i in range(total):
        excel_idx = start_index + i
        if excel_idx >= len(excel_list):
            break

        uid = excel_list[excel_idx]["UID"]
        tb = current_tables[i]

        try:
            page = doc[tb["page_idx"]]
            rect = fitz.Rect(tb["bbox"])
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
            img_name = f"{core}_table_{uid:03d}.png"
            pix.save(os.path.join(final_output_dir, img_name))
            pix = None
            success += 1
            print(f"✅ UID={uid:03d} | {img_name}")
        except Exception as e:
            print(f"❌ UID={uid} 截图失败")

    doc.close()
    print(f"\n🎉 {ann_id} 处理完成！成功截图：{success}/{total}")

# ==================== 命令行入口 ====================
def main():
    parser = argparse.ArgumentParser(description="表格截图（完整/拆分全兼容，UID 百分百对齐）")
    parser.add_argument("--filename", required=True, help="输入 201 / 201-1 / 201-2")
    args = parser.parse_args()

    pdf_path = f"pdf/{args.filename}.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在：{pdf_path}")
        return

    screenshot_pdf_tables(pdf_path, SCREENSHOT_OUTPUT_DIR, args.filename)

if __name__ == "__main__":
    main()