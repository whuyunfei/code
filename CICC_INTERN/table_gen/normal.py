import matplotlib.pyplot as plt
import pandas as pd
import random
import os
from pathlib import Path

# ===================== 核心配置（全部可调） =====================
GEN_NUM = 1000          # 生成表格数量
MIN_COLS = 3
MAX_COLS = 10
MIN_ROWS = 5
MAX_ROWS = 18
# ===============================================================

plt.rcParams["font.sans-serif"] = ["Arial", "Microsoft YaHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# ===================== 完整无删减 列名词库（机构/分部/板块） =====================
COL_POOL = [
    "North\nRegion", "South\nRegion", "East\nRegion", "West\nRegion",
    "Central\nArea", "Northeast\nBranch", "Southwest\nBranch",
    "China\nMainland", "Hong\nKong\nBranch", "Macau\nOffice",
    "Taiwan\nBusiness", "ASEAN\nMarket", "EU\nBusiness",
    "North\nAmerica\nDiv", "South\nAmerica\nUnit", "Africa\nSegment",
    "Oceania\nDepartment", "Middle\nEast\nHub", "Global\nHeadquarters",
    "Domestic\nOperation", "Overseas\nExpansion", "Cross-border\nTrade",
    "Retail\nBusiness", "Wholesale\nTrade", "E-commerce\nChannel",
    "Offline\nStore", "Direct-sale\nTeam", "Agent\nCooperation",
    "Group\nParent\nFirm", "Core\nSubsidiary", "Secondary\nSubsidiary",
    "Holding\nEnterprise", "Investment\nCompany", "Operating\nEntity",
    "Production\nBase", "Processing\nFactory", "Assembly\nWorkshop",
    "Sales\nBranch", "Market\nPromotion\nCenter", "Customer\nService\nCenter",
    "Financial\nManagement\nDept", "Audit\nSupervision\nUnit",
    "Strategic\nPlanning\nDept", "Risk\nControl\nDepartment",
    "Technology\nResearch\nInstitute", "Product\nDevelopment\nCenter",
    "Logistics\nDistribution\nCenter", "Warehouse\nStorage\nUnit",
    "Import\nTrade\nDivision", "Export\nBusiness\nGroup",
    "Light\nIndustry\nSegment", "Heavy\nIndustry\nBranch",
    "Service\nIndustry\nUnit", "Cultural\nBusiness\nDepartment",
    "Medical\nHealth\nDivision", "Education\nTraining\nBranch",
    "Energy\nBusiness\nGroup", "Chemical\nRaw\nMaterial\nUnit",
    "Electronic\nProduct\nSegment", "Automotive\nParts\nDept",
    "Real\nEstate\nOperation", "Tourism\nService\nCenter",
    "Food\nProcessing\nFactory", "Daily\nNecessities\nBranch",
    "High-end\nMarket\nDiv", "Mid-end\nMarket\nUnit",
    "Low-end\nMarket\nSegment", "Emerging\nMarket\nGroup",
    "Mature\nMarket\nDept", "Potential\nMarket\nCenter",
    "Fixed\nAsset\nOperation", "Liquidity\nFund\nUnit",
    "Short-term\nInvestment", "Long-term\nInvestment\nDiv",
    "Joint\nVenture\nEntity", "Strategic\nCooperative\nFirm",
    "Fully-owned\nSubsidiary", "Equity\nParticipation\nUnit",
    "Business\nCombination\nDept", "Asset\nRestructuring\nGroup",
    "Annual\nPerformance\nUnit", "Quarterly\nBusiness\nBranch",
    "Cost\nControl\nCenter", "Profit\nCreation\nDepartment",
    "Budget\nManagement\nDiv", "Settlement\nAudit\nUnit",
    "EMEA\nBusiness", "LATAM\nOperation", "APAC\nRegional",
    "NAM\nCore\nUnit", "Corporate\nManagement", "Manufacturing\nCenter",
    "R&D\nInstitute", "Brand\nOperation\nDept", "Capital\nOperation\nGroup"
]

# ===================== 完整无删减 行名词库（财务报表标准项目） =====================
ROW_POOL = [
    "Revenue from Main Business", "Other Operating Revenue",
    "Total Operating Income", "External Sales Revenue",
    "Internal Intersegment Revenue", "Annual Turnover Amount",
    "Quarterly Business Income", "Monthly Operating Proceeds",
    "Cost of Main Business", "Other Operating Costs",
    "Total Operating Cost", "Raw Material Purchase Cost",
    "Labor Service Expense", "Production Manufacturing Cost",
    "Goods Circulation Expense", "Logistics Transportation Cost",
    "Selling and Marketing Expenses", "Advertising Promotion Cost",
    "Channel Development Expense", "Market Expansion Expense",
    "General Administrative Expenses", "Office Daily Expense",
    "Staff Salary and Welfare", "Employee Bonus Expense",
    "Travel and Entertainment Cost", "Conference Training Expense",
    "Research and Development Expenses", "Technology Research Cost",
    "Product Iteration Investment", "Technical Equipment Upgrade Cost",
    "Financial Related Expenses", "Bank Handling Charges",
    "Loan Interest Expense", "Bond Financing Interest",
    "Interest Income from Deposits", "Financial Product Income",
    "Foreign Exchange Settlement Gain", "Foreign Exchange Fluctuation Loss",
    "Total Operating Expenses", "Business Tax and Surcharges",
    "Stamp Duty Expense", "Property Tax Payable",
    "Land Use Tax Expense", "Operating Profit Amount",
    "Equity Investment Income", "Dividend Income from Investees",
    "Profit from Joint Ventures", "Earnings from Associated Firms",
    "Gain from Fixed Asset Disposal", "Loss of Asset Liquidation",
    "Government Subsidy Income", "Policy Preference Benefit",
    "Non-operating Miscellaneous Income", "Non-operating Casual Expense",
    "Inventory Surplus Income", "Inventory Deficit Loss",
    "Bad Debt Recovered Income", "Bad Debt Provision Expense",
    "Credit Impairment Loss", "Asset Impairment Provision",
    "Inventory Depreciation Loss", "Fixed Asset Depreciation Expense",
    "Intangible Asset Amortization Cost", "Long-term Prepaid Amortization",
    "Operating Leasing Expense", "Equipment Rental Fee",
    "Professional Consulting Fee", "Audit and Accounting Service Fee",
    "Legal Counsel Service Fee", "Intellectual Property Royalty Fee",
    "Profit Before Income Tax Adjustment", "Pre-tax Total Profit",
    "Adjusted Pre-tax Operating Profit", "Current Period Income Tax Expense",
    "Deferred Tax Asset Adjustment Amount", "Deferred Tax Liability Change",
    "Overseas Business Income Tax", "Withholding Tax Expense",
    "Net Profit After Income Tax", "Consolidated Net Profit",
    "Comprehensive Total Income", "Retained Surplus Amount",
    "Distributed Profit Bonus", "Undistributed Profit Balance",
    "Profit Attributable to Parent Company",
    "Profit Attributable to Minority Shareholders",
    "Basic Earnings Per Share", "Diluted Earnings Per Share",
    "Weighted Average Earnings Level", "Annual Cumulative Net Earnings",
    "Operating Cash Inflow", "Operating Cash Outflow",
    "Net Operating Cash Flow", "Investment Business Cash Flow",
    "Financing Activity Cash Flow", "Total Net Cash Flow",
    "Fixed Asset Investment Expenditure", "Intangible Asset Acquisition Cost",
    "Capital Construction Project Investment", "Short-term Equity Investment Outlay",
    "Long-term Bond Investment Expense", "Fund Product Purchase Expense",
    "Total Current Assets", "Currency Funds Balance",
    "Bank Deposit Reserves", "Bill Receivable Balance",
    "Accounts Receivable Net Amount", "Advance Payment to Suppliers",
    "Inventory Goods Book Value", "Other Current Asset Balance",
    "Total Non-current Assets", "Net Fixed Asset Value",
    "Construction in Progress Amount", "Net Intangible Asset Value",
    "Long-term Equity Investment Balance", "Deferred Tax Asset Balance",
    "Total Current Liabilities", "Short-term Loan Principal",
    "Accounts Payable to Suppliers", "Advance Received Customer Payment",
    "Employee Salary Payable", "Various Taxes Payable Balance",
    "Total Non-current Liabilities", "Long-term Borrowing Balance",
    "Corporate Bond Payable Amount", "Long-term Accounts Payable",
    "Total Owner's Equity", "Paid-in Capital Amount",
    "Capital Reserve Balance", "Surplus Reserve Accumulation",
    "Other Comprehensive Income Adjustment", "Operating Gross Profit Margin",
    "Core Business Profit Margin", "Net Profit Margin Level",
    "Total Asset Profitability Ratio", "Net Asset Income Ratio",
    "Business Income Growth Rate", "Net Profit Year-on-year Change Rate",
    "Enterprise Operating Scale Index", "Market Occupancy Share Index"
]

# 严格校验，数量不足直接报错，无任何兜底
if len(COL_POOL) < 30 or len(ROW_POOL) < 60:
    raise RuntimeError("❌ 内置词库数量不达标，禁止运行")
print(f"✅ 完整词库加载成功 | 可用列名:{len(COL_POOL)} 个 | 可用行名:{len(ROW_POOL)} 个")

# ===================== 随机财务数字生成规则 =====================
def rand_fin_num():
    if random.random() < 0.15:
        return "—"
    base_num = random.randint(50000, 3000000)
    if random.choice([True, False]):
        return f"({base_num:,})"
    else:
        return f"{base_num:,}"

# ===================== 自动生成财务标准下划线规则 =====================
def get_underline_rules(row_cnt):
    rules = ["none"] * row_cnt
    if row_cnt >= 1:
        rules[-1] = "double"
    if row_cnt >= 2:
        rules[-2] = "single"
    for idx in range(2, row_cnt - 2, 3):
        if random.random() < 0.7:
            rules[idx] = "single"
    return rules

# ===================== 【新增】导出 HTML =====================
def save_html(html_path, rows, cols, data, ul_rules):
    col_clean = [c.replace("\n", " ") for c in cols]
    row_clean = [r.replace("\n", " ") for r in rows]

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    table { border-collapse: collapse; width: 100%; margin-top:20px; }
    th, td { padding: 10px 14px; text-align: right; }
    th { background: #ffffff; font-weight:bold; text-align:center; }
    td { background: #ffffff; }
    tr:nth-child(even) td { background: #e6f2ff; }
    .single { border-bottom: 1px solid #000; }
    .double { border-bottom: 3px double #000; }
</style>
</head>
<body>
<h2 style="text-align:center;">For the Year Ended December 31, 2024</h2>
<p style="text-align:center;">(in USD thousands)</p>
<table>
'''

    html += '  <tr>\n    <th></th>\n'
    for c in col_clean:
        html += f'    <th>{c}</th>\n'
    html += '  </tr>\n'

    for row, cells, ul in zip(row_clean, data, ul_rules):
        cls = f' {ul}' if ul != "none" else ""
        html += f'  <tr>\n    <td style="text-align:left;">{row}</td>\n'
        for d in cells:
            html += f'    <td class="{cls}">{d}</td>\n'
        html += '  </tr>\n'

    html += '</table></body></html>'

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

# ===================== 单张表格绘制函数（样式完全固定不变） =====================
def generate_single_table(out_path):
    n_cols = random.randint(MIN_COLS, MAX_COLS)
    n_rows = random.randint(MIN_ROWS, MAX_ROWS)

    cols = random.sample(COL_POOL, n_cols)
    rows = random.sample(ROW_POOL, n_rows)
    data = [[rand_fin_num() for _ in range(n_cols)] for _ in range(n_rows)]
    ul_rules = get_underline_rules(n_rows)

    df = pd.DataFrame(data, index=rows, columns=cols)
    df["_ul"] = ul_rules
    show_cols = [c for c in df.columns if c != "_ul"]
    df_show = df[show_cols]

    fig_width = max(18, n_cols * 3.2)
    fig_height = max(6, 2.5 + n_rows * 0.45)
    fig = plt.figure(figsize=(fig_width, fig_height), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.5, 0.96, "For the Year Ended December 31, 2024", ha="center", fontsize=16, weight="bold")
    fig.text(0.5, 0.93, "(in USD thousands)", ha="center", fontsize=12)

    table = ax.table(
        cellText=df_show.values,
        rowLabels=df_show.index,
        colLabels=df_show.columns,
        cellLoc="right",
        rowLoc="left",
        loc="center",
        bbox=[0.01, 0.05, 0.98, 0.85]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)

    for pos, cell in table.get_celld().items():
        cell.set_edgecolor("none")
        i, j = pos
        if i == 0:
            cell.set_text_props(weight="bold", ha="center", va="center")
            cell.set_facecolor("white")
        else:
            cell.set_text_props(ha="left" if j == 0 else "right", va="center")
            cell.set_facecolor("#e6f2ff" if (i - 1) % 2 == 0 else "white")

    x0, y0, table_width, table_height = table._bbox
    row_single_height = table_height / (n_rows + 1)
    underline_list = df["_ul"].tolist()

    header_line_y = y0 + table_height - row_single_height
    now_x = x0
    for col_idx in range(n_cols):
        cell_w = table[(0, col_idx)].get_width() * table_width
        ax.plot([now_x + 0.004, now_x + cell_w - 0.004],
                [header_line_y, header_line_y],
                color="black", linewidth=1.1, transform=ax.transAxes)
        now_x += cell_w

    for row_idx in range(n_rows):
        line_type = underline_list[row_idx]
        if line_type == "none":
            continue
        line_y_pos = y0 + (n_rows - row_idx - 1) * row_single_height
        now_x = x0
        for col_idx in range(n_cols):
            cell_w = table[(0, col_idx)].get_width() * table_width
            if line_type == "single":
                ax.plot([now_x + 0.004, now_x + cell_w - 0.004],
                        [line_y_pos, line_y_pos],
                        color="black", linewidth=0.8, transform=ax.transAxes)
            elif line_type == "double":
                ax.plot([now_x + 0.004, now_x + cell_w - 0.004],
                        [line_y_pos, line_y_pos],
                        color="black", linewidth=1.1, transform=ax.transAxes)
                ax.plot([now_x + 0.004, now_x + cell_w - 0.004],
                        [line_y_pos + 0.005, line_y_pos + 0.005],
                        color="black", linewidth=1.1, transform=ax.transAxes)
            now_x += cell_w

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()

    # 保存 HTML
    html_path = str(out_path).replace(".png", ".html")
    save_html(html_path, rows, cols, data, ul_rules)

# ===================== 批量生成入口 =====================
if __name__ == "__main__":
    save_folder = Path(__file__).parent / "batches"
    save_folder.mkdir(exist_ok=True)

    print(f"\n🚀 开始批量生成 {GEN_NUM} 张标准财务表格\n")

    for idx in range(1, GEN_NUM + 1):
        save_name = f"sin_table_{idx:03d}.png"
        full_path = save_folder / save_name
        generate_single_table(full_path)
        print(f"✅ {save_name} + {save_name.replace('.png', '.html')}")

    print(f"\n🎉 全部生成完毕，保存目录：{save_folder.resolve()}")