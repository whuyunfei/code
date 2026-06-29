import fitz
import re
from PIL import Image
import io
import os
from pathlib import Path

def extract_charts_full_width(pdf_path, output_dir="charts"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    chart_count = 0
    
    print(f"正在处理PDF: {pdf_path}")
    print(f"共 {len(doc)} 页\n")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        page_width = page.rect.width
        page_height = page.rect.height
        
        # ===== 找出所有"图表"（包含位置和文本位置） =====
        chart_info = []
        for match in re.finditer(r'(图表\s*(\d+)\s*[：:]\s*([^\n]+))', text):
            chart_title = match.group(1).strip()
            chart_num = match.group(2)
            chart_desc = match.group(3).strip()
            
            rects = page.search_for(chart_title[:15])
            if rects:
                chart_info.append({
                    'title': chart_title,
                    'num': chart_num,
                    'desc': chart_desc,
                    'rect': rects[0],
                    'text_pos': match.start(),
                    'y0': rects[0].y0,
                    'y1': rects[0].y1
                })
        
        if not chart_info:
            continue
        
        # ===== 找出所有"资料来源"（包含位置和文本位置） =====
        source_info = []
        for match in re.finditer(r'(资料来源|数据来源)\s*[：:]\s*([^\n]+)', text):
            keyword = match.group(1)
            rects = page.search_for(keyword)
            if rects:
                # 取y坐标最大的矩形（最下面的）
                best_rect = max(rects, key=lambda r: r.y0)
                source_info.append({
                    'keyword': keyword,
                    'rect': best_rect,
                    'text_pos': match.start(),
                    'y0': best_rect.y0
                })
        
        if not source_info:
            print(f"  第{page_num+1}页: 找到图表但未找到'资料来源'")
            continue
        
        # ===== 按文本流位置匹配：图表之后最近的资料来源 =====
        for chart in chart_info:
            chart_pos = chart['text_pos']
            matched_source = None
            
            for source in source_info:
                if source['text_pos'] > chart_pos:
                    if matched_source is None or source['text_pos'] < matched_source['text_pos']:
                        matched_source = source
            
            if matched_source is None:
                print(f"  ⚠️ 第{page_num+1}页: 图表 '{chart['title']}' 后无资料来源，跳过")
                continue
            
            chart_rect = chart['rect']
            source_rect = matched_source['rect']
            
            # 构建截图区域
            y0 = chart_rect.y0 - 15
            y1 = source_rect.y1 + 15
            
            y0 = max(0, y0)
            y1 = min(page_height, y1)
            
            if y0 >= y1:
                print(f"  ⚠️ 第{page_num+1}页: '{chart['title']}' 高度无效，跳过")
                continue
            
            rect = fitz.Rect(0, y0, page_width, y1)
            
            try:
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat, clip=rect)
                
                if pix is None or pix.width <= 0 or pix.height <= 0:
                    continue
                
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                safe_title = re.sub(r'[\\/*?:"<>|]', "", chart['desc'][:30])
                filename = f"图表{chart['num']}_{safe_title}.png"
                filepath = os.path.join(output_dir, filename)
                
                img.save(filepath, "PNG")
                chart_count += 1
                print(f"  ✅ 第{page_num+1}页: 已保存 {filename}")
                
            except Exception as e:
                print(f"  ❌ 第{page_num+1}页: '{chart['title']}' 截图失败: {e}")
    
    doc.close()
    print(f"\n✅ 完成！共提取 {chart_count} 个图表，保存在 '{output_dir}' 目录中。")
    return chart_count

def main():
    pdf_file = input("请输入PDF文件路径: ").strip()
    
    if not os.path.exists(pdf_file):
        print(f"❌ 文件不存在: {pdf_file}")
        return
    
    extract_charts_full_width(pdf_file)

if __name__ == "__main__":
    main()