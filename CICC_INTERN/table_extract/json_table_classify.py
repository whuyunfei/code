# -*- coding: utf-8 -*-
import json
import pandas as pd
from bs4 import BeautifulSoup
import argparse
import os
from cross_pages import detect_cross_pages
from table_border import match_table_borders

def parse_json_tables(json_path, pdf_path, ann_id):
    try:
        if not os.path.exists(json_path):
            raise Exception(f"JSON不存在: {json_path}")
        print(f"✅ 加载JSON: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 续表 / 跨页检测
        print("✅ 续表/跨页检测")
        cross_set, continued_set = detect_cross_pages(data)
        rows = []
        
        # ================ 只新增这一行：提取纯编号 203 ================
        base_ann = ann_id.split("-")[0]
        # ============================================================
        table_id = 1

        # ====================== 新增：-2 文件规则（你要的功能） ======================
        page_offset = 0
        is_minus_2 = "-2" in ann_id
        if is_minus_2:
            base_id = ann_id.replace("-2", "-1")
            # ================ 只改这一行：读取同一个主文件 ================
            base_excel = f"excel_output/{base_ann}.xlsx"
            if os.path.exists(base_excel):
                try:
                    df = pd.read_excel(base_excel)
                    if not df.empty and "UID" in df.columns:
                        table_id = df["UID"].max() + 1
                        page_offset = 200
                        print(f"📌 检测到-2文件：UID从 {table_id} 开始，页码+200")
                except:
                    table_id = 1
        # ==========================================================================

        # 逐页处理
        for page in data["pdf_info"]:
            page_idx = page["page_idx"] + 1
            print(f"处理第 {page_idx} 页")

            blocks = page["para_blocks"]
            real_index = 0
            table_in_page = 0

            # 提取当前页所有JSON表格
            json_tables = [block for block in blocks if block.get("type") == "table"]

            # 调用封装的边框匹配接口
            border_flags = match_table_borders(json_tables, pdf_path, page_idx)

            # ====================== 新版：Y范围重合判断分栏（最贴合PDF实际） ======================
            page_col_flags = []
            page_w = page.get("page_size", [595, 842])[0]
            # 第一步：收集所有表格信息 + 区分左右栏
            table_list = []
            left_tables = []
            right_tables = []
            for idx, block in enumerate(json_tables):
                x0, y0, x1, y1 = block["bbox"]
                is_right = 1 if x0 > page_w / 2 else 0
                table_list.append({
                    "idx": idx,
                    "y0": y0,
                    "y1": y1,
                    "is_right": is_right
                })
                if is_right:
                    right_tables.append({"idx": idx, "y0": y0, "y1": y1})
                else:
                    left_tables.append({"idx": idx, "y0": y0, "y1": y1})
            # 第二步：初始化分栏标记（默认0）
            final_col = [0] * len(json_tables)
            # 第三步：核心逻辑 —— 左右表格 Y 范围有重合 → 全部标1
            for left in left_tables:
                l_idx = left["idx"]
                l_y0 = left["y0"]
                l_y1 = left["y1"]

                for right in right_tables:
                    r_idx = right["idx"]
                    r_y0 = right["y0"]
                    r_y1 = right["y1"]

                    # 判断Y区间是否重合
                    max_start = max(l_y0, r_y0)
                    min_end = min(l_y1, r_y1)
                    has_overlap = max_start < min_end

                    if has_overlap:
                        final_col[l_idx] = 1
                        final_col[r_idx] = 1
            page_col_flags = final_col
            # ==============================================================================

            # ====================== 遍历当前页所有表格 ======================
            for table_idx, block in enumerate(json_tables):
                table_in_page += 1
                # 续表判断
                is_continued = (page_idx, table_in_page) in continued_set
                if not is_continued:
                    real_index += 1
                    table_order = real_index
                else:
                    table_order = ""

                # 边框标记
                full_border = border_flags[table_idx]

                # 旋转
                angle = 0
                for b in block.get("blocks", []):
                    if b.get("type") == "table_body":
                        angle = b.get("angle", 0)
                        break
                rot = 1 if angle != 0 else 0
                col = page_col_flags[table_idx]

                # 提取HTML
                html = ""
                for b in block.get("blocks", []):
                    if b.get("type") == "table_body":
                        for l in b.get("lines", []):
                            for s in l.get("spans", []):
                                if s.get("type") == "table":
                                    html = s.get("html", "")
                                    break
                            if html:
                                break
                        if html:
                            break
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                table = soup.find("table")
                if not table:
                    continue

                # 表格标题
                title = ""
                first_tr = table.find("tr")
                if first_tr:
                    cells = [c.get_text(strip=True) for c in first_tr.find_all(["td", "th"])]
                    title = "，".join([c for c in cells if c])[:50]

                # 合并单元格
                has_merge = 0
                merge_list = []
                all_tds = table.find_all(["td", "th"])
                for td in all_tds:
                    r = int(td.get("rowspan", 1))
                    c = int(td.get("colspan", 1))
                    if r > 1 or c > 1:
                        has_merge = 1
                        merge_list.append(f"{r}x{c}")
                merge_str = ",".join(sorted(set(merge_list))) if merge_list else ""

                # 跨页
                cross_page = 1 if (page_idx, real_index) in cross_set else 0

                # 构建输出行
                row = {
                    # ================ 只改这一行：去掉-1-2 ================
                    "ANN_ID": base_ann,
                    "UID": table_id,
                    "PAGE_NUM": page_idx + page_offset,
                    "TABLE_ORDER": table_order,
                    "TABLE_TITLE": title,
                    "完整框线（完整框线：1，无线：0）": full_border,
                    "合并单元格": has_merge,
                    "跨页": cross_page,
                    "旋转": rot,
                    "分栏": col,
                    "CELL_COUNT": len(all_tds),
                    "MERGED_FORMATS": merge_str,
                    "TABLE_CONTENT": html.replace("\n", "").replace("\t", "")
                }
                rows.append(row)
                table_id += 1

        return rows

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True, help="文件名，不含后缀")
    args = parser.parse_args()
    fname = args.filename
    json_file = f"json_data/{fname}.json"
    pdf_file = f"pdf/{fname}.pdf"
    
    # ================ 只改这里：输出到同一个excel ================
    base_fname = fname.split("-")[0]
    excel_file = f"excel_output/{base_fname}.xlsx"
    
    result = parse_json_tables(json_file, pdf_file, fname)
    df_new = pd.DataFrame(result)
    
    # 追加模式，不覆盖
    if os.path.exists(excel_file):
        df_old = pd.read_excel(excel_file)
        df_total = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_total = df_new
    
    df_total.to_excel(excel_file, index=False)
    print(f"✅ 处理完成！共输出 {len(result)} 个表格（与JS 1:1对应）")