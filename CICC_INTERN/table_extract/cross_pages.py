# cross_pages.py
from collections import defaultdict

def get_table_title(table_block):
    """
    提取表格标题：从 table_caption 或 表格第一行
    """
    if not table_block:
        return ""
    
    # 先找 table_caption
    for bk in table_block.get("blocks", []):
        if bk.get("type") == "table_caption":
            for line in bk.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("type") == "text":
                        txt = span.get("content", "").strip()
                        if txt:
                            return txt
    
    # 再找表格第一行作为标题
    for bk in table_block.get("blocks", []):
        if bk.get("type") == "table_body":
            for line in bk.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("type") == "table":
                        html = span.get("html", "")
                        if "<tr>" in html:
                            rows = html.split("<tr>")
                            if len(rows) > 1:
                                first_row = rows[1]
                                if "<td>" in first_row or "<th>" in first_row:
                                    return ""  # 有数据行 = 无标题，可能是续表
    return ""

def detect_cross_pages(json_data):
    """
    最终规则：
    1. 当前页第一个块是 table
    2. 且当前页第一个表格 没有新标题 → 才判定为续表
    3. 有标题 → 新表格，不跨页
    """
    pages = []
    for page in json_data["pdf_info"]:
        page_num = page["page_idx"] + 1
        tables = []
        first_block_type = None
        first_table = None

        if page["para_blocks"]:
            first_block_type = page["para_blocks"][0]["type"]

        for blk in page["para_blocks"]:
            if blk.get("type") == "table":
                tables.append(blk)

        # 取当前页第一个表格
        if tables:
            first_table = tables[0]

        pages.append({
            "page_num": page_num,
            "first_block_type": first_block_type,
            "tables": tables,
            "first_table": first_table
        })

    cross_pages = set()    # 上一页最后一个表格 = 跨页
    continued = set()      # 当前页第一个 = 续表

    for i in range(1, len(pages)):
        prev_page = pages[i-1]
        curr_page = pages[i]

        # 条件1：当前页第一个块是 table
        if curr_page["first_block_type"] != "table":
            continue

        curr_first_table = curr_page["first_table"]
        if not curr_first_table:
            continue

        # ====================== 【你新增的规则】 ======================
        title = get_table_title(curr_first_table)
        if title.strip():
            # 有标题 → 新表格 → 不跨页
            continue

        # ====================== 满足：续表 ======================
        # 上一页最后一个表格 → 跨页
        if prev_page["tables"]:
            prev_page_num = prev_page["page_num"]
            prev_last_order = len(prev_page["tables"])
            cross_pages.add((prev_page_num, prev_last_order))

        # 当前页第一个 → 续表
        curr_page_num = curr_page["page_num"]
        continued.add((curr_page_num, 1))

    return cross_pages, continued