import matplotlib.pyplot as plt
import random
import os
from pathlib import Path

# ===================== 【批量配置】 =====================
OUTPUT_DIR = "financial_tables"
BATCH_COUNT = 100
MIN_COLS = 3
MAX_COLS = 6
MIN_ROWS = 8
MAX_ROWS = 15

# 数据源
COL_POOL = [
    "Revenue\n($M)", "Cost\n($M)", "Margin\n%",
    "2025\n$", "2024\n$", "2023\n$",
    "Domestic\n", "Overseas\n", "Global\n"
]
GROUP_HEADERS = ["Yearly Data", "Quarterly", "Product", "Region", "Segment", "Division"]
ROW_POOL = [
    "Net Sales", "Cost of Goods Sold", "Gross Profit",
    "Operating Expenses", "Operating Income", "Net Income",
    "EPS - Basic", "EPS - Diluted", "Total Assets",
    "Total Liabilities", "Equity", "Cash Flow",
    "Gross Margin %", "Operating Margin %", "Tax Rate"
]

# ===================== 工具函数 =====================
def rand_value():
    if random.random() < 0.1:
        return "—"
    num = random.randint(10000, 5000000)
    return f"${num:,}"

# ===================== 随机缩进（最多2级） =====================
def generate_indents(n_rows):
    indents = [0] * n_rows
    if n_rows <= 1:
        return indents

    current_level = 0
    for i in range(1, n_rows):
        if current_level == 0:
            choice = random.choice([0,0,1])
        elif current_level == 1:
            choice = random.choice([1,1,2])
        else:
            choice = 2

        if i >= n_rows - 2:
            choice = 0

        indents[i] = choice
        current_level = choice
    return indents

# ===================== 下划线规则 =====================
def get_underline_rules(row_cnt):
    rules = []
    for i in range(row_cnt):
        if i == row_cnt - 1:
            rules.append(2)
        else:
            rules.append(random.choice([0, 1]))
    return rules

def generate_group_spans(n_cols):
    groups = []
    idx = 0
    while idx < n_cols:
        name = random.choice(GROUP_HEADERS)
        remaining = n_cols - idx
        span = min(random.randint(2, 3), remaining)
        groups.append((name, span))
        idx += span
    return groups

# ===================== ✅ 仅修复：表头 colspan 合并 + 左上角空白无样式 =====================
def save_html(html_path, row_labels, col_labels, data, groups, ul_rules, indents):
    col_labels_clean = [c.replace("\n", " ") for c in col_labels]
    row_labels_clean = [r.replace("\n", " ") for r in row_labels]

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    table { border-collapse: collapse; width: 100%; margin-top:20px; }
    th, td { padding: 10px 14px; text-align: right; border: none; } /* 保留你原版：无边框 */
    th { background: #f5f5f5; font-weight:bold; text-align:center; }
    td { background: #ffffff; }
    tr:nth-child(even) td { background: #f7f7f7; }
    .indent0 { text-align:left !important; padding-left:0px !important; }
    .indent1 { text-align:left !important; padding-left:20px !important; }
    .indent2 { text-align:left !important; padding-left:40px !important; }
    .single { border-bottom: 1px solid #000; }
    .double { border-bottom: 3px double #000; }
    .header-top { border-bottom: 1px solid #000; } /* 原版表头底线 */
    .empty-corner {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
</style>
</head>
<body>
<h2>Consolidated Financial Data</h2>
<p style="text-align:right;">(USD in millions)</p>
'''

    # ===================== 关键修复：用 <table> + colspan 实现真正合并 =====================
    html += '<table>\n'

    # 第一行：分组标题（左上角 清空样式）
    html += '  <tr>\n'
    html += '    <th class="empty-corner"></th>\n'
    for name, span in groups:
        html += f'    <th colspan="{span}" class="header-top">{name}</th>\n'
    html += '  </tr>\n'

    # 第二行：子列标题（左上角 清空样式）
    html += '  <tr>\n'
    html += '    <th class="empty-corner"></th>\n'
    for c in col_labels_clean:
        html += f'    <th class="header-top">{c}</th>\n'
    html += '  </tr>\n'

    # 数据行：完全 100% 保留你原版逻辑
    for row, cells, ul, indent in zip(row_labels_clean, data, ul_rules, indents):
        ul_class = "single" if ul == 1 else "double" if ul == 2 else ""
        html += f'  <tr>\n'
        html += f'    <td class="indent{indent}">{row}</td>\n'
        for d in cells:
            html += f'    <td class="{ul_class}">{d}</td>\n'
        html += '  </tr>\n'

    html += '</table></body></html>'

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

# ===================== 表格绘制 =====================
def create_table(file_path):
    n_cols = random.randint(MIN_COLS, MAX_COLS)
    n_rows = random.randint(MIN_ROWS, MAX_ROWS)
    
    col_labels = [random.choice(COL_POOL) for _ in range(n_cols)]
    row_labels = [random.choice(ROW_POOL) for _ in range(n_rows)]
    
    data = [[rand_value() for _ in range(n_cols)] for _ in range(n_rows)]
    ul_rules = get_underline_rules(n_rows)
    groups = generate_group_spans(n_cols)
    indents = generate_indents(n_rows)

    indented_row_labels = []
    for idx, text in enumerate(row_labels):
        level = indents[idx]
        if level == 1:
            indented_row_labels.append("    " + text)
        elif level == 2:
            indented_row_labels.append("        " + text)
        else:
            indented_row_labels.append(text)

    fig = plt.figure(figsize=(14, 8 + n_rows * 0.3), dpi=200)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.5, 0.96, "Consolidated Financial Data", ha="center", fontsize=16, weight="bold")
    fig.text(0.92, 0.93, "(USD in millions)", ha="right", fontsize=10)

    table = ax.table(
        cellText=data, 
        rowLabels=indented_row_labels, 
        colLabels=col_labels,
        cellLoc="right", 
        rowLoc="left", 
        loc="center",
        bbox=[0.02, 0.05, 0.96, 0.85]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor("none")
        if i == 0:
            cell.set_facecolor("#f5f5f5")
            cell.set_text_props(weight="bold", ha="center")
        else:
            cell.set_facecolor("#f7f7f7" if (i-1)%2==0 else "white")

    x0, y0, w_tab, h_tab = table._bbox
    col_widths = [table[(0,j)].get_width() * w_tab for j in range(n_cols)]
    col_starts = [x0 + sum(col_widths[:j]) for j in range(n_cols)]
    group_y = y0 + h_tab + 0.02

    idx = 0
    for g, s in groups:
        st = col_starts[idx]
        end_idx = idx + s
        ed = x0 + w_tab if end_idx >= len(col_starts) else col_starts[end_idx]
        cx = (st + ed) / 2
        ax.text(cx, group_y, g, ha="center", fontsize=11, weight="bold")
        ax.plot([ed, ed], [group_y - 0.003, group_y + 0.006], c="black", lw=1)
        idx += s

    ax.plot([x0, x0 + w_tab], [y0 + h_tab, y0 + h_tab], c="black", lw=1.2)

    row_single_height = h_tab / (n_rows + 1)
    for r in range(n_rows):
        typ = ul_rules[r]
        if typ == 0:
            continue
        y = y0 + (n_rows - r - 1) * row_single_height
        nx = x0
        for c in range(n_cols):
            cw = table[(0, c)].get_width() * w_tab
            if typ == 1:
                ax.plot([nx + 0.002, nx + cw - 0.002], [y, y], c="black", lw=0.9)
            if typ == 2:
                ax.plot([nx + 0.002, nx + cw - 0.002], [y - 0.002, y - 0.002], c="black", lw=1)
                ax.plot([nx + 0.002, nx + cw - 0.002], [y + 0.002, y + 0.002], c="black", lw=1)
            nx += cw

    plt.tight_layout()
    plt.savefig(file_path, bbox_inches="tight")
    plt.close()

    html_path = str(file_path).replace(".png", ".html")
    save_html(html_path, row_labels, col_labels, data, groups, ul_rules, indents)

# ===================== 批量生成 =====================
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 输出文件夹：{Path(OUTPUT_DIR).resolve()}")

    for i in range(BATCH_COUNT):
        path = os.path.join(OUTPUT_DIR, f"financial_table_{i+1:02d}.png")
        create_table(path)
        print(f"✅ 已生成：{path}")
        print(f"✅ 已生成：{path.replace('.png', '.html')}")

    print(f"\n🎉 批量生成完成！")