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

# 颜色配置（PNG + HTML 完全统一）
HEADER_COLOR = '#2E86C1'      # 表头背景：深蓝色
ROW_LABEL_COLOR = '#ADD8E6'  # 第一列行名：浅蓝色
TEXT_COLOR = 'white'         # 文字颜色

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

# ===================== HTML 左上角改为白色 =====================
def save_html(html_path, row_labels, col_labels, data, groups, indents):
    col_clean = [c.replace("\n", " ") for c in col_labels]
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    table { border-collapse: collapse; width:100%; margin-top:20px; border:0; }
    th, td { padding:10px 14px; border:0; }
    /* 表头：深蓝色 */
    th {
        background-color: #2E86C1;
        color: white;
        font-weight:bold;
        text-align:center;
    }
    /* 第一列行标签：浅蓝色（和图片一致） */
    .row-label {
        background-color: #ADD8E6;
        color: black;
        font-weight: bold;
        text-align: left;
    }
    /* 数据：纯白无任何样式 */
    .data-cell {
        background: white;
        color: black;
        text-align: right;
    }
    .indent0 { padding-left: 4px; }
    .indent1 { padding-left: 24px; }
    .indent2 { padding-left: 44px; }
</style>
</head>
<body>
<h2 style="text-align:center;">Consolidated Financial Data</h2>
<p style="text-align:right;">(USD in millions)</p>

<table>
<tr>
  <!-- 这里改成白色背景 -->
  <th style="background:white;"></th>
'''
    for c in col_clean:
        html += f'<th>{c}</th>\n'
    html += '</tr>\n'

    for row, cells, indent in zip(row_labels, data, indents):
        html += f'<tr><td class="row-label indent{indent}">{row}</td>'
        for d in cells:
            html += f'<td class="data-cell">{d}</td>'
        html += '</tr>\n'

    html += '</table></body></html>'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

# ===================== 绘图：无线条、纯颜色 =====================
def create_table(file_path):
    n_cols = random.randint(MIN_COLS, MAX_COLS)
    n_rows = random.randint(MIN_ROWS, MAX_ROWS)
    col_labels = [random.choice(COL_POOL) for _ in range(n_cols)]
    row_labels = [random.choice(ROW_POOL) for _ in range(n_rows)]
    data = [[rand_value() for _ in range(n_cols)] for _ in range(n_rows)]
    indents = generate_indents(n_rows)

    # 缩进
    indented_rows = []
    for lev, txt in zip(indents, row_labels):
        if lev == 1:
            indented_rows.append("    " + txt)
        elif lev == 2:
            indented_rows.append("        " + txt)
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

    # 颜色 + 无边框
    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor("none")
        
        # 表头
        if i == 0:
            cell.set_facecolor(HEADER_COLOR)
            cell.get_text().set_color(TEXT_COLOR)
        # 行标签列
        elif j == -1:
            cell.set_facecolor(ROW_LABEL_COLOR)
        # 数据区
        else:
            cell.set_facecolor("white")

    plt.tight_layout()
    plt.savefig(file_path, bbox_inches="tight", facecolor="white")
    plt.close()

    html_path = str(file_path).replace(".png", ".html")
    save_html(html_path, row_labels, col_labels, data, None, indents)

# ===================== 运行 =====================
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"输出目录：{Path(OUTPUT_DIR).resolve()}")
    for i in range(1, BATCH_COUNT+1):
        save_png = os.path.join(OUTPUT_DIR, f"nolinetable_{i:03d}.png")
        create_table(save_png)
        print(f"✅ 生成：nolinetable_{i:03d}.png/.html")
    print("\n🎉 全部生成完成！")