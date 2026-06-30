# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import argparse
import pandas as pd
from config import HTML_FILE, SCREENSHOT_OUTPUT_DIR

def screenshot_html_tables(html_path, output_dir, ann_id):
    # 自动提取核心前缀：105、105-1、105-2 → 都变成 105
    core = ann_id.split("-")[0]
    
    # 输出文件夹：xxx_tables
    final_output_dir = os.path.join(output_dir, f"{core}_tables")
    os.makedirs(final_output_dir, exist_ok=True)

    # -2 文件接续 -1 的编号
    start_index = 1
    if ann_id.endswith("-2"):
        base_id = ann_id.replace("-2", "-1")
        excel_path = f"excel_output/{base_id}.xlsx"
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path)
                if not df.empty and "UID" in df.columns:
                    start_index = df["UID"].max() + 1
            except:
                start_index = 1

    # 读取HTML
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except:
        print(f"❌ 无法读取HTML：{html_path}")
        return

    tables = soup.find_all("table")
    if not tables:
        print(f"【{html_path}】未找到表格")
        return

    # 截图
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}", wait_until="load")

            current_idx = start_index
            for idx, table in enumerate(tables):
                try:
                    table_elem = page.wait_for_selector(f"//table[{idx+1}]", timeout=5000)
                    # 命名：xxx_table_001.png
                    img_name = f"{core}_table_{current_idx:03d}.png"
                    img_path = os.path.join(final_output_dir, img_name)
                    table_elem.screenshot(path=img_path)
                    print(f"✅ 截图完成：{img_name}")
                    current_idx += 1
                except Exception as e:
                    print(f"❌ 截图失败：{e}")

            browser.close()
    except Exception as e:
        print(f"❌ 浏览器启动失败：{e}")
        return

# ====================== 命令行调用 ======================
def main():
    parser = argparse.ArgumentParser(description="HTML表格截图")
    parser.add_argument("--filename", required=True, help="文件名：如105、105-1、105-2")
    args = parser.parse_args()

    html_path = os.path.join(os.path.dirname(HTML_FILE), f"{args.filename}.html")
    screenshot_html_tables(html_path, SCREENSHOT_OUTPUT_DIR, args.filename)

if __name__ == "__main__":
    main()