import matplotlib.pyplot as plt
import random
import os
from pathlib import Path

# ===================== 配置 =====================
OUTPUT_DIR = "noborders"
BATCH_COUNT = 100
MIN_COLS = 3
MAX_COLS = 6
MIN_ROWS = 8
MAX_ROWS = 15

# 词库
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

def rand_value():
    if random.random() < 0.1:
        return "—"
    num = random.randint(10000, 5000000)
    return f"${num:,}"

# 最多2级缩进
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

def get_underline_rules(row_cnt):
    rules = [0]*row_cnt
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

# HTML 纯无线条
def save_html(html_path, row_labels, col_labels, data, groups, indents):
    col_labels_clean = [c.replace("\n", " ") for c in col_labels]
    row_labels_clean = [r.replace("\n", " ") for r in row_labels]
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    table { border:none; border-collapse: collapse; width:100%; margin-top:20px; }
    th, td { border:none; padding:10px 14px; }
    th { font-weight:bold; text-align:center; background:#fff; }
    td { background:#fff; }
    .indent1 { padding-left:20px; text-align:left; }
    .indent2 { padding-left:40px; text-align:left; }
    .indent0 { text-align:left; }
</style>
</head>
<body>
<h2 style="text-align:center;">Consolidated Financial Data</h2>
<p style="text-align:right;">(USD in millions)</p>
<table>
  <tr>
    <th></th>
'''
    for c in col_labels_clean:
        html += f'<th>{c}</th>\n'
    html += '</tr>\n'
    for row, cells, indent in zip(row_labels_clean, data, indents):
        cls = f"indent{indent}"
        html += f'<tr><td class="{cls}">{row}</td>'
        for d in cells:
            html += f'<td style="text-align:right;">{d}</td>'
        html += '</tr>\n'
    html += '</table></body></html>'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

# 绘图 完全无任何线条
def create_table(file_path):
    n_cols = random.randint(MIN_COLS, MAX_COLS)
    n_rows = random.randint(MIN_ROWS, MAX_ROWS)
    col_labels = [random.choice(COL_POOL) for _ in range(n_cols)]
    row_labels = [random.choice(ROW_POOL) for _ in range(n_rows)]
    data = [[rand_value() for _ in range(n_cols)] for _ in range(n_rows)]
    groups = generate_group_spans(n_cols)
    indents = generate_indents(n_rows)

    # 文本空格缩进
    indented_rows = []
    for lev, txt in zip(indents, row_labels):
        if lev == 1:
            indented_rows.append("    "+txt)
        elif lev == 2:
            indented_rows.append("        "+txt)
        else:
            indented_rows.append(txt)

    fig = plt.figure(figsize=(14, 8 + n_rows * 0.3), dpi=200)
    ax = fig.add_subplot(111)
    ax.axis("off")

    fig.text(0.5, 0.96, "Consolidated Financial Data", ha="center", fontsize=16, weight="bold")
    fig.text(0.92, 0.93, "(USD in millions)", ha="right", fontsize=10)

    table = ax.table(
        cellText=data,
        rowLabels=indented_rows,
        colLabels=col_labels,
        cellLoc="right",
        rowLoc="left",
        loc="center",
        bbox=[0.02, 0.05, 0.96, 0.85]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    # 全局清除所有边框、底色
    for cell in table.get_celld().values():
        cell.set_edgecolor("none")
        cell.set_facecolor("white")

    # 不绘制任何分组线、分隔线、下划线
    plt.tight_layout()
    plt.savefig(file_path, bbox_inches="tight", facecolor="white")
    plt.close()

    html_path = str(file_path).replace(".png", ".html")
    save_html(html_path, row_labels, col_labels, data, groups, indents)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"输出目录：{Path(OUTPUT_DIR).resolve()}")
    for i in range(BATCH_COUNT):
        save_png = os.path.join(OUTPUT_DIR, f"nolinecolortable_{i+1:02d}.png")
        create_table(save_png)
        print(f"✅ 生成：nolinecolortable_{i+1:02d}.png / nolinecolortable_{i+1:02d}.html")
    print("\n🎉 全部纯无线条表格生成完毕")