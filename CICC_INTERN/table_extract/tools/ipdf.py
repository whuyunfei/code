import fitz
import argparse
import os

def split_pdf_by_ranges(input_pdf, pages_list):
    # 把页码列表两两分组：[1,20,22,23] → [[1,20], [22,23]]
    if len(pages_list) % 2 != 0:
        print("❌ 页码必须成对输入：开始页 结束页 开始页 结束页...")
        return

    pairs = [pages_list[i:i+2] for i in range(0, len(pages_list), 2)]

    # 打开原PDF
    doc = fitz.open(input_pdf)

    for start, end in pairs:
        # 页码转整数（PyMuPDF 从 0 开始）
        s = start - 1
        e = end - 1

        if s < 0 or e >= doc.page_count or s > e:
            print(f"⚠️ 跳过无效范围：{start}-{end}")
            continue

        # 创建新PDF
        new_pdf = fitz.open()
        new_pdf.insert_pdf(doc, from_page=s, to_page=e)

        # 输出文件名
        out_name = f"{os.path.splitext(input_pdf)[0]}_{start}-{end}.pdf"
        new_pdf.save(out_name)
        new_pdf.close()

        print(f"✅ 已生成：{out_name}")

    doc.close()
    print("\n🎉 所有分段完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="按页码范围拆分PDF，成对输入：start end start end...")
    parser.add_argument("--pages", nargs="+", type=int, required=True, help="页码列表，如：1 20 22 23")

    args = parser.parse_args()
    pages = args.pages

    # 自动找当前目录下的第一个 PDF 文件（你也可以手动指定）
    pdf_files = [f for f in os.listdir() if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("❌ 当前目录没有找到 PDF 文件")
        exit(1)

    input_pdf = pdf_files[0]
    print(f"📄 正在处理：{input_pdf}\n")

    split_pdf_by_ranges(input_pdf, pages)