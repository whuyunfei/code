# -*- coding: utf-8 -*-
import os

# ====================== 可配置项 ======================
# 目标文件名（无需后缀）
TARGET_FILE_NAME = "cmb"  # 改为你需要的文件名，如 "icbc" "abc"

# 文件路径配置
JSON_DIR = "json_data"
PDF_DIR = "pdf"
HTML_DIR = "html_data"
EXCEL_OUTPUT_DIR = "excel_output"
SCREENSHOT_OUTPUT_DIR = "tables_output"

# 自动拼接完整路径
JSON_FILE = os.path.join(JSON_DIR, f"{TARGET_FILE_NAME}.json")
PDF_FILE = os.path.join(PDF_DIR, f"{TARGET_FILE_NAME}.pdf")
HTML_FILE = os.path.join(HTML_DIR, f"{TARGET_FILE_NAME}.html")
EXCEL_FILE = os.path.join(EXCEL_OUTPUT_DIR, f"{TARGET_FILE_NAME}.xlsx")

# 创建目录（确保存在）
for dir_path in [JSON_DIR, PDF_DIR, HTML_DIR, EXCEL_OUTPUT_DIR, SCREENSHOT_OUTPUT_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)