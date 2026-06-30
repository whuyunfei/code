import camelot.io as camelot
import warnings
import gc
import os

warnings.filterwarnings("ignore")

def _detect_pdf_tables(pdf_path, page):
    try:
        # 有边框表格
        lattice = camelot.read_pdf(
            pdf_path,
            pages=str(page),
            flavor="lattice",
            split_text=True,
            suppress_stdout=True
        )

        # 无边框表格
        stream = camelot.read_pdf(
            pdf_path,
            pages=str(page),
            flavor="stream",
            split_text=True,
            suppress_stdout=True
        )

        tables = []
        for t in lattice:
            y = t._bbox[1]
            tables.append((float(y), 1))

        for t in stream:
            y = t._bbox[1]
            tables.append((float(y), 0))

        tables.sort(key=lambda x: x[0])

        # 强制释放资源，解决Windows文件占用
        del lattice, stream
        gc.collect()

        return tables

    except Exception as e:
        print(f"❌ [PDF解析] 第 {page} 页 解析失败！")
        return []

def match_table_borders(json_tables, pdf_path, page_num):
    json_count = len(json_tables)

    # 无表格直接返回
    if json_count == 0:
        print(f"📌 [边框匹配] 第{page_num}页 | JSON表格数:0 | 跳过匹配")
        return []

    # 1. 排序JSON表格
    json_table_with_idx = []
    for idx, block in enumerate(json_tables):
        js_y = float(block["bbox"][1])
        json_table_with_idx.append({"idx": idx, "js_y": js_y})

    sorted_json_tables = sorted(json_table_with_idx, key=lambda x: x["js_y"])

    # 2. 获取PDF表格
    pdf_tables = _detect_pdf_tables(pdf_path, page_num)
    pdf_border_count = sum(1 for item in pdf_tables if item[1] == 1)
    pdf_noborder_count = len(pdf_tables) - pdf_border_count

    # ===================== 你的核心逻辑 =====================
    if pdf_border_count > 0 and json_count <= pdf_border_count:
        border_result = [1] * json_count
        print(f"📌 [边框匹配] 第{page_num}页 | JSON:{json_count} | PDF有线框:{pdf_border_count} | 全表标记为有线框")
    else:
        border_result = [0] * json_count
        for match_idx, json_item in enumerate(sorted_json_tables):
            original_idx = json_item["idx"]
            if match_idx < len(pdf_tables):
                border_result[original_idx] = pdf_tables[match_idx][1]
        print(f"📌 [边框匹配] 第{page_num}页 | JSON:{json_count} | PDF总数:{len(pdf_tables)} (有线:{pdf_border_count} 无线:{pdf_noborder_count}) | 匹配完成")

    # 最终强制GC，彻底解决文件占用
    gc.collect()

    return border_result

# 兼容旧接口
def detect_table_borders(pdf_path, page):
    return _detect_pdf_tables(pdf_path, page)