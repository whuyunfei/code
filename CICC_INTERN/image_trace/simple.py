"""
数据溯源验证脚本 - 精简版

功能：
1. 从图片中提取内容（标题、数据、"资料来源"）- 使用本地Tesseract OCR
2. 使用 browser-use 浏览器自动化访问官网并提取网页内容
3. AI 自动比对图片内容与网页内容的匹配度
4. 返回匹配度最高的链接
5. 生成溯源报告表格

依赖安装：
pip install browser-use playwright anthropic pandas pillow requests pytesseract
playwright install chromium
"""

import os
import json
import re
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

import anthropic
import pandas as pd
from PIL import Image
import requests
import pytesseract
from browser_use.browser import BrowserSession as Browser
from openpyxl.utils import get_column_letter

# ==================== 配置 ====================

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

ZHIPU_API_KEY = "1850f3d00d89466a8c3880f305c52ccd.uhlQ4L6TXaXOEhP8"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/anthropic"
MODEL = "claude-3-5-sonnet-20241022"

CHROME_EXECUTABLE_PATH = r"C:\Users\taoyuanxu\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe"
CDP_PORT = 9223
PROXY_SERVER = "http://bjproxy2.cicc.group:8080"

# 等待时间（减半）
WAIT_LONG = 5
WAIT_SHORT = 0.5
WAIT_CHROME_MAX = 5

# 清除代理
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
    os.environ.pop(var, None)

# ==================== 数据类 ====================

@dataclass
class TracingResult:
    image_path: str
    chart_number: str
    image_title: str
    source_name: str
    official_site: str
    best_link: str
    is_match: bool
    match_score: int
    findings: str
    data_in_web: str

# ==================== 工具函数 ====================

def parse_json(text: str, default: Dict = None) -> Dict:
    if default is None:
        default = {}
    if not text or not text.strip():
        return default
    try:
        match = re.search(r'\{[\s\S]*\}', text)
        return json.loads(match.group()) if match else default
    except:
        return default

def extract_keywords(title: str) -> str:
    """从标题提取关键词"""
    if not title or title in ("提取失败", "N/A"):
        return ""
    cleaned = re.sub(r'图表\s*\d+[：:]\s*', '', title)
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', cleaned)
    cleaned = re.sub(r'（单位：.*?）', '', cleaned)
    # 移除常见无意义词汇
    cleaned = re.sub(r'(?:数据|分析|报告|研究|显示|来源|单位|亿元|万元|%)', '', cleaned)
    words = [w for w in re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', cleaned) 
             if len(w) > 1 and not w.isdigit()]
    return ' '.join(words[:5]) if words else cleaned.strip()

def build_search_query(source: str, title: str) -> str:
    """
    构建搜索查询
    优先级：资料来源 > 图表标题 > 组合
    """
    # 如果资料来源有效，使用"资料来源 + 标题关键词"
    if source and source != "未标注" and len(source) > 1:
        clean_source = re.sub(r'[（(][^）)]*[）)]', '', source.split('，')[0].strip())
        clean_source = clean_source.split('、')[0].strip()
        
        if clean_source and len(clean_source) > 1:
            title_keywords = extract_keywords(title)
            if title_keywords:
                return f"{clean_source} {title_keywords}"
            return clean_source
    
    # 如果资料来源无效，直接使用标题关键词
    title_keywords = extract_keywords(title)
    if title_keywords:
        return title_keywords
    
    # 最后保底方案
    return "数据报告"

# ==================== 图片提取 ====================

class ImageExtractor:
    def extract_content(self, image_path: str) -> Dict:
        try:
            img = Image.open(image_path)
            full_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            all_text = "\n".join(lines)

            result = {
                "chart_number": "未识别",
                "title": "提取失败",
                "source": "未标注",
                "key_numbers": []
            }

            # 图表编号（支持"图表"和"表"两种格式）
            chart_match = re.search(r'(?:图\s*)?表\s*(\d+)', all_text)
            if chart_match:
                result["chart_number"] = f"图表 {chart_match.group(1)}"

            # 标题（取包含"图表"或"表"的行）
            for line in lines[:5]:
                if re.search(r'[图表]', line):
                    title = re.sub(r'(?:图\s*)?表\s*\d+[：:]\s*', '', line).strip()
                    if title and len(title) > 2:
                        result["title"] = title
                        break
            if result["title"] == "提取失败" and lines:
                result["title"] = lines[0]

            # 资料来源（支持多种格式）
            source_patterns = [
                r'资料来源[:：]\s*(.+)',
                r'数据来源[:：]\s*(.+)',
                r'来源[:：]\s*(.+)'
            ]
            for pattern in source_patterns:
                match = re.search(pattern, all_text)
                if match:
                    result["source"] = match.group(1).strip()
                    break
            
            if result["source"] == "未标注":
                for line in lines:
                    if '来源' in line:
                        cleaned = re.sub(r'^.*?来源[:：]?\s*', '', line).strip()
                        if cleaned:
                            result["source"] = cleaned
                            break

            # 关键数据
            numbers = re.findall(r'\d+\.?\d*%', all_text) or re.findall(r'\d+\.?\d*', all_text)
            result["key_numbers"] = list(set(numbers))[:10]

            return result
        except Exception as e:
            print(f"    ⚠️ OCR失败: {e}")
            return {"chart_number": "未识别", "title": "提取失败", "source": "未标注", "key_numbers": []}

# ==================== 浏览器溯源 ====================

class BrowserTracer:
    def __init__(self):
        self.browser = None
        self.chrome_process = None

    async def __aenter__(self):
        # 清理旧进程
        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, shell=True)
        except:
            pass
        await asyncio.sleep(WAIT_SHORT)

        # 启动Chrome
        print("    → 启动 Chrome...")
        self.chrome_process = subprocess.Popen(
            [CHROME_EXECUTABLE_PATH, f"--remote-debugging-port={CDP_PORT}", 
             "--no-first-run", "--no-default-browser-check", "--disable-gpu",
             "--disable-blink-features=AutomationControlled", f"--proxy-server={PROXY_SERVER}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        # 等待Chrome就绪
        for i in range(WAIT_CHROME_MAX):
            await asyncio.sleep(WAIT_SHORT)
            try:
                if requests.get(f"http://localhost:{CDP_PORT}/json/version", timeout=2).status_code == 200:
                    print("    → Chrome 已就绪")
                    break
            except:
                if i == WAIT_CHROME_MAX - 1:
                    raise RuntimeError("Chrome启动超时")

        self.browser = Browser(
            cdp_url=f"http://localhost:{CDP_PORT}",
            headless=False,
            disable_security=True,
            minimum_wait_page_load_time=WAIT_SHORT,
            wait_for_network_idle_page_load_time=WAIT_SHORT,
            wait_between_actions=WAIT_SHORT
        )
        await self.browser.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.chrome_process:
            self.chrome_process.terminate()
            try:
                self.chrome_process.wait(timeout=2)
            except:
                self.chrome_process.kill()

    async def trace_source(self, source_name: str, image_content: Dict) -> Dict:
        chart_title = image_content.get("title", "")
        
        # 构建搜索查询（自动处理资料来源无效的情况）
        search_query = build_search_query(source_name, chart_title)
        print(f"    → 资料来源: {source_name}")
        print(f"    → 图表标题: {chart_title}")
        print(f"    → 搜索关键词: {search_query}")

        if len(search_query) < 2:
            return {"official_site": "", "page_content": "", "findings": f"搜索词无效: {search_query}"}

        try:
            page = await self.browser.get_current_page()
            await page.goto(f"https://www.baidu.com/s?wd={search_query}")
            await asyncio.sleep(WAIT_LONG)

            # 获取链接
            links_json = await page.evaluate("""
                () => [...document.querySelectorAll('a')]
                    .map(a => a.getAttribute('href'))
                    .filter(h => h && h.includes('http'))
            """)
            links = json.loads(links_json) if links_json else []
            print(f"    → 找到 {len(links)} 个链接")

            if not links:
                return {"official_site": "", "page_content": "", "findings": "未找到链接"}

            # 取第20-50个，去重
            unique_links = []
            seen = set()
            for link in links[20:50]:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            if not unique_links:
                return {"official_site": "", "page_content": "", "findings": "无第20-50个链接"}

            client = anthropic.Anthropic(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
            all_pages = []
            best_match = None
            best_score = 0

            # 访问每个链接
            for i, link in enumerate(unique_links, start=20):
                print(f"    → [{i}] 访问: {link[:60]}...")
                try:
                    if not link.startswith('http'):
                        continue

                    await page.goto(link)
                    await asyncio.sleep(WAIT_LONG)

                    title = await page.get_title()
                    url = await page.get_url()
                    content = await page.evaluate("() => document.body.innerText || ''")

                    if len(content) <= 200:
                        print(f"       ⚠️ 内容太少，跳过")
                        continue

                    # AI比对
                    prompt = f"""比对图片与网页匹配度(0-100)：

图片: {image_content.get('title', 'N/A')} | 来源: {image_content.get('source', '')} | 数据: {', '.join(image_content.get('key_numbers', [])[:3])}

网页标题: {title}
内容预览: {content[:800]}

返回JSON: {{"match_score": 0-100, "findings": "结论"}}"""

                    try:
                        resp = client.messages.create(
                            model=MODEL, max_tokens=256,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        result = parse_json(resp.content[0].text, {"match_score": 0, "findings": ""})
                        score = result.get("match_score", 0)
                        print(f"       匹配度: {score}%")

                        page_info = {"url": url, "title": title, "full_content": content[:2000], 
                                   "match_score": score, "findings": result.get("findings", "")}
                        all_pages.append(page_info)

                        if score > best_score:
                            best_score = score
                            best_match = page_info
                    except Exception as e:
                        print(f"       ⚠️ AI比对失败: {e}")

                except Exception as e:
                    print(f"       ⚠️ 访问失败: {e}")
                    continue

                if i < len(unique_links):
                    await page.go_back()
                    await asyncio.sleep(WAIT_LONG)

            if not all_pages:
                return {"official_site": "", "page_content": "", "findings": "无法访问任何页面"}

            print(f"    → 最佳匹配度: {best_score}%")
            if best_match:
                print(f"    → 最佳链接: {best_match['url']}")

            return {
                "official_site": best_match['url'] if best_match else all_pages[0]['url'],
                "page_content": best_match['full_content'] if best_match else all_pages[0]['full_content'],
                "findings": f"最佳匹配度: {best_score}%" if best_match else "返回第一个页面"
            }

        except Exception as e:
            print(f"    ⚠️ 溯源出错: {e}")
            return {"official_site": "", "page_content": "", "findings": f"出错: {str(e)}"}

# ==================== 报告生成 ====================

class ReportGenerator:
    def __init__(self):
        self.results: List[TracingResult] = []

    def add(self, result: TracingResult):
        self.results.append(result)

    def save(self, output_path: str):
        if not self.results:
            print("没有结果")
            return

        data = []
        for r in self.results:
            data.append({
                "图表编号": r.chart_number,
                "图表标题": r.image_title,
                "资料来源": r.source_name,
                "最佳匹配链接": r.best_link,
                "匹配度": f"{r.match_score}%",
                "是否匹配": "是" if r.is_match else "否",
                "验证结果": r.findings,
            })

        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='溯源报告', index=False)
            worksheet = writer.sheets['溯源报告']
            
            for col_idx, col_name in enumerate(df.columns, 1):
                max_len = max(
                    len(str(col_name)),
                    max(df[col_name].astype(str).map(len).tolist()) if len(df) > 0 else 0
                )
                worksheet.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)

        print(f"\n✅ 报告已生成: {output_path}")

    def summary(self):
        if not self.results:
            return
        total = len(self.results)
        matched = sum(1 for r in self.results if r.is_match)
        avg_score = sum(r.match_score for r in self.results) / total
        print("\n" + "="*50)
        print(f"总数: {total} | 匹配: {matched} ({matched/total*100:.1f}%) | 平均匹配度: {avg_score:.1f}%")
        print("="*50)

# ==================== 主流程 ====================

async def process_image(image_path: str, extractor: ImageExtractor, 
                        tracer: BrowserTracer, fetch_web: bool = True) -> TracingResult:
    print(f"\n📷 {Path(image_path).name}")

    # OCR提取
    content = extractor.extract_content(image_path)
    print(f"  → 标题: {content['title'][:30]}")
    print(f"  → 来源: {content['source']}")

    # 网页溯源（即使资料来源为"未标注"也进行搜索，使用标题）
    source_info = {"official_site": "", "page_content": "", "findings": ""}
    if fetch_web:
        # 只要有标题或资料来源就进行搜索
        has_valid_info = (content['source'] != "未标注" and len(content['source']) > 1) or \
                         (content['title'] != "提取失败" and len(content['title']) > 2)
        
        if has_valid_info:
            print("  → browser-use 开始溯源...")
            source_info = await tracer.trace_source(content['source'], content)
            print(f"  → 结果: {source_info.get('findings', '无结果')}")
        else:
            print("  → ⚠️ 图片无有效标题或资料来源，跳过溯源")
            source_info["findings"] = "图片无有效标题或资料来源"

    # 验证结果
    score = 0
    if source_info.get("findings", "").startswith("最佳匹配度"):
        score_match = re.search(r'(\d+)%', source_info.get("findings", ""))
        score = int(score_match.group(1)) if score_match else 0

    return TracingResult(
        image_path=image_path,
        chart_number=content.get("chart_number", "未识别"),
        image_title=content.get("title", "N/A"),
        source_name=content.get("source", "未标注"),
        official_site=source_info.get("official_site", ""),
        best_link=source_info.get("official_site", ""),
        is_match=score >= 50,
        match_score=score,
        findings=source_info.get("findings", "未验证"),
        data_in_web="已确认" if score > 0 else "未确认"
    )

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('image_dir', help='图片目录')
    parser.add_argument('-o', '--output', default='溯源报告.xlsx')
    parser.add_argument('--no-web', action='store_true', help='跳过网页验证')
    args = parser.parse_args()

    print("="*50)
    print("数据溯源验证工具")
    print("="*50)

    # 获取图片
    image_files = []
    for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
        image_files.extend(Path(args.image_dir).glob(f"*{ext}"))
        # image_files.extend(Path(args.image_dir).glob(f"*{ext.upper()}"))
    image_files = [str(f) for f in image_files]  # 不去重，保留所有

    if not image_files:
        print(f"❌ 未找到图片")
        return

    print(f"找到 {len(image_files)} 个图片:")
    for f in image_files:
        print(f"  - {Path(f).name}")

    extractor = ImageExtractor()
    report = ReportGenerator()

    async with BrowserTracer() as tracer:
        for i, img_path in enumerate(image_files, 1):
            print(f"\n{'='*50}")
            print(f"[{i}/{len(image_files)}] 处理: {Path(img_path).name}")
            print(f"{'='*50}")
            try:
                result = await process_image(img_path, extractor, tracer, not args.no_web)
                report.add(result)
                print(f"✅ [{i}] 处理完成")
            except Exception as e:
                print(f"\n❌ [{i}] 处理失败: {e}")
                import traceback
                traceback.print_exc()
                # 继续处理下一张
                continue

    report.save(str(Path(args.image_dir) / args.output))
    report.summary()

if __name__ == "__main__":
    asyncio.run(main())