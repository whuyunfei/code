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
import time
from pathlib import Path
from typing import Dict, List, Optional
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

# 等待时间
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
    source_type: str

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
    cleaned = re.sub(r'(?:数据|分析|报告|研究|显示|来源|单位|亿元|万元|%)', '', cleaned)
    words = [w for w in re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', cleaned) 
             if len(w) > 1 and not w.isdigit()]
    return ' '.join(words[:5]) if words else cleaned.strip()

def build_search_query(source: str, title: str) -> str:
    """
    构建搜索查询
    优先级：资料来源 > 图表标题 > 组合
    """
    if source and source != "未标注" and len(source) > 1:
        clean_source = re.sub(r'[（(][^）)]*[）)]', '', source.split('，')[0].strip())
        clean_source = clean_source.split('、')[0].strip()
        
        if clean_source and len(clean_source) > 1:
            title_keywords = extract_keywords(title)
            if title_keywords:
                return f"{clean_source} {title_keywords}"
            return clean_source
    
    title_keywords = extract_keywords(title)
    if title_keywords:
        return title_keywords
    
    return "数据报告"

def classify_source_type(source_name: str, page_content: str = "", client=None) -> str:
    """
    使用AI判断数据源类型：公开数据源 / 商业数据源
    """
    if not client:
        client = anthropic.Anthropic(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
    
    commercial_keywords = ['彭博', 'Bloomberg', 'Wind', '万得', 'Reuters', '路透', 
                          'S&P', '标普', 'MSCI', 'FactSet', 'CEIC', 'Datastream',
                          '中金', 'CICC', '券商', '证券', '基金', '投资']
    for kw in commercial_keywords:
        if kw.lower() in source_name.lower():
            return "商业数据源"
    
    if len(source_name) < 3 or source_name == "未标注":
        return "公开数据源"
    
    try:
        prompt = f"""判断以下数据来源是"公开数据源"还是"商业数据源"：

数据来源: {source_name}
网页内容预览: {page_content[:500] if page_content else '无'}

公开数据源：政府统计局、央行、行业协会、上市公司年报、学术机构、免费公开数据库
商业数据源：彭博、Wind、路透、券商研究所、付费数据库、商业咨询机构

返回JSON: {{"source_type": "公开数据源" 或 "商业数据源", "reason": "判断理由"}}"""

        resp = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_json(resp.content[0].text, {"source_type": "公开数据源", "reason": ""})
        return result.get("source_type", "公开数据源")
    except Exception as e:
        print(f"      ⚠️ 数据源类型判断失败: {e}")
        commercial_keywords = ['彭博', 'Bloomberg', 'Wind', '万得', 'Reuters', '路透', 
                              'S&P', '标普', 'MSCI', 'FactSet', 'CEIC', 'Datastream',
                              '中金', 'CICC', '券商']
        for kw in commercial_keywords:
            if kw.lower() in source_name.lower():
                return "商业数据源"
        return "公开数据源"

def kill_all_chrome():
    """强制关闭所有Chrome进程"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, shell=True)
        print("    → 已关闭所有Chrome进程")
    except Exception as e:
        print(f"    ⚠️ 关闭Chrome进程失败: {e}")
    time.sleep(1)

def check_chrome_ready(port: int = CDP_PORT, timeout: int = WAIT_CHROME_MAX) -> bool:
    """检查Chrome调试端口是否就绪"""
    for i in range(timeout):
        try:
            if requests.get(f"http://localhost:{port}/json/version", timeout=2).status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

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

            chart_match = re.search(r'(?:图\s*)?表\s*(\d+)', all_text)
            if chart_match:
                result["chart_number"] = f"图表 {chart_match.group(1)}"

            for line in lines[:5]:
                if re.search(r'[图表]', line):
                    title = re.sub(r'(?:图\s*)?表\s*\d+[：:]\s*', '', line).strip()
                    if title and len(title) > 2:
                        result["title"] = title
                        break
            if result["title"] == "提取失败" and lines:
                result["title"] = lines[0]

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

            numbers = re.findall(r'\d+\.?\d*%', all_text) or re.findall(r'\d+\.?\d*', all_text)
            result["key_numbers"] = list(set(numbers))[:10]

            return result
        except Exception as e:
            print(f"    ⚠️ OCR失败: {e}")
            return {"chart_number": "未识别", "title": "提取失败", "source": "未标注", "key_numbers": []}

# ==================== 浏览器溯源 ====================

class BrowserTracer:
    def __init__(self, max_retries: int = 3):
        self.browser = None
        self.chrome_process = None
        self.max_retries = max_retries
        self.retry_count = 0

    async def __aenter__(self):
        await self._start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_browser()

    async def _start_browser(self):
        """启动浏览器"""
        # 清理旧进程
        kill_all_chrome()
        await asyncio.sleep(WAIT_SHORT)

        print("    → 启动 Chrome...")
        self.chrome_process = subprocess.Popen(
            [CHROME_EXECUTABLE_PATH, f"--remote-debugging-port={CDP_PORT}", 
             "--no-first-run", "--no-default-browser-check", "--disable-gpu",
             "--disable-blink-features=AutomationControlled", f"--proxy-server={PROXY_SERVER}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if not check_chrome_ready():
            raise RuntimeError("Chrome启动超时")

        print("    → Chrome 已就绪")
        self.browser = Browser(
            cdp_url=f"http://localhost:{CDP_PORT}",
            headless=False,
            disable_security=True,
            minimum_wait_page_load_time=WAIT_SHORT,
            wait_for_network_idle_page_load_time=WAIT_SHORT,
            wait_between_actions=WAIT_SHORT
        )
        await self.browser.start()
        print("    → Browser 已初始化")

    async def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                print(f"    ⚠️ 关闭browser失败: {e}")
        if self.chrome_process:
            try:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=2)
            except:
                try:
                    self.chrome_process.kill()
                except:
                    pass
        kill_all_chrome()
        self.browser = None
        self.chrome_process = None

    async def restart_browser(self):
        """重启浏览器"""
        print("    → 重启浏览器...")
        await self._close_browser()
        await asyncio.sleep(2)
        await self._start_browser()
        self.retry_count = 0

    async def trace_source(self, source_name: str, image_content: Dict) -> Dict:
        """溯源主逻辑，带重试机制"""
        self.retry_count = 0
        
        while self.retry_count < self.max_retries:
            try:
                return await self._trace_source_internal(source_name, image_content)
            except Exception as e:
                self.retry_count += 1
                error_msg = str(e)
                print(f"    ⚠️ 溯源出错 (尝试 {self.retry_count}/{self.max_retries}): {error_msg}")
                
                # 如果是浏览器相关的错误，重启浏览器
                if 'goto' in error_msg or 'NoneType' in error_msg or 'page' in error_msg.lower():
                    print(f"    → 检测到浏览器错误，准备重启...")
                    try:
                        await self.restart_browser()
                        print(f"    → 浏览器已重启，继续尝试 {self.retry_count + 1}/{self.max_retries}")
                    except Exception as restart_error:
                        print(f"    ❌ 浏览器重启失败: {restart_error}")
                        # 如果重启失败，等待一下再尝试
                        await asyncio.sleep(3)
                else:
                    # 其他错误，等待后重试
                    await asyncio.sleep(2)
        
        # 所有重试都失败
        return {"official_site": "", "page_content": "", "findings": f"重试{self.max_retries}次后仍失败"}

    async def _trace_source_internal(self, source_name: str, image_content: Dict) -> Dict:
        """实际的溯源逻辑"""
        chart_title = image_content.get("title", "")
        
        search_query = build_search_query(source_name, chart_title)
        print(f"    → 资料来源: {source_name}")
        print(f"    → 图表标题: {chart_title}")
        print(f"    → 搜索关键词: {search_query}")

        if len(search_query) < 2:
            return {"official_site": "", "page_content": "", "findings": f"搜索词无效: {search_query}"}

        # 获取页面
        page = await self.browser.get_current_page()
        if page is None:
            raise RuntimeError("无法获取页面对象，浏览器可能未正确初始化")
        
        await page.goto(f"https://cn.bing.com/search?q={search_query}")
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
        for link in links[0:50]:
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
        for i, link in enumerate(unique_links, start=0):
            print(f"    → [{i}] 访问: {link[:60]}...")
            try:
                if not link.startswith('http'):
                    continue

                # 重新获取页面（防止页面对象失效）
                page = await self.browser.get_current_page()
                if page is None:
                    raise RuntimeError("页面对象丢失")
                
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
                # 如果是浏览器错误，重新获取页面
                if 'page' in str(e).lower() or 'goto' in str(e).lower():
                    raise RuntimeError(f"浏览器错误: {e}")
                continue

            if i < len(unique_links):
                try:
                    page = await self.browser.get_current_page()
                    if page:
                        await page.go_back()
                        await asyncio.sleep(WAIT_LONG)
                except:
                    pass

        if not all_pages:
            return {"official_site": "", "page_content": "", "findings": "无法访问任何页面"}

        print(f"    → 最佳匹配度: {best_score}%")
        if best_match:
            print(f"    → 最佳链接: {best_match['url']}")

        return {
            "official_site": best_match['url'] if best_match else all_pages[0]['url'],
            "page_content": best_match['full_content'] if best_match else all_pages[0]['full_content'],
            "findings": f"最佳匹配度: {best_score}%" if best_match else "返回第一个页面",
            "best_page_content": best_match['full_content'] if best_match else all_pages[0]['full_content']
        }

# ==================== 报告生成 ====================

class ReportGenerator:
    def __init__(self):
        self.results: List[TracingResult] = []
        self.client = anthropic.Anthropic(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)

    def add(self, result: TracingResult):
        self.results.append(result)

    def save(self, output_path: str):
        if not self.results:
            print("没有结果")
            return

        data = []
        for r in self.results:
            source_type = classify_source_type(r.source_name, r.data_in_web, self.client)
            
            data.append({
                "图表信息": f"{r.chart_number} {r.image_title}",
                "资料来源": r.source_name,
                "数据源类型": source_type,
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
        source_types = [classify_source_type(r.source_name, r.data_in_web, self.client) for r in self.results]
        commercial = sum(1 for t in source_types if t == "商业数据源")
        public = total - commercial
        
        print("\n" + "="*50)
        print(f"总数: {total} | 匹配: {matched} ({matched/total*100:.1f}%) | 平均匹配度: {avg_score:.1f}%")
        print(f"数据源类型: 商业数据源 {commercial} 个 | 公开数据源 {public} 个")
        print("="*50)

# ==================== 主流程 ====================

async def process_image_with_retry(image_path: str, extractor: ImageExtractor, 
                                   tracer: BrowserTracer, fetch_web: bool = True,
                                   max_retries: int = 3) -> Optional[TracingResult]:
    """处理单个图片，带重试机制"""
    
    for attempt in range(max_retries):
        try:
            print(f"\n📷 {Path(image_path).name} (尝试 {attempt + 1}/{max_retries})")

            # OCR提取
            content = extractor.extract_content(image_path)
            print(f"  → 标题: {content['title'][:30]}")
            print(f"  → 来源: {content['source']}")

            # 网页溯源
            source_info = {"official_site": "", "page_content": "", "findings": "", "best_page_content": ""}
            if fetch_web:
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

            # 如果溯源失败（findings包含错误信息），重试
            if fetch_web and has_valid_info:
                findings = source_info.get("findings", "")
                if "出错" in findings or "失败" in findings or "重试" in findings:
                    if attempt < max_retries - 1:
                        print(f"  → 溯源失败，准备重试...")
                        # 重启浏览器
                        await tracer.restart_browser()
                        continue
                    else:
                        print(f"  → 所有重试均失败，跳过此图片")

            result = TracingResult(
                image_path=image_path,
                chart_number=content.get("chart_number", "未识别"),
                image_title=content.get("title", "N/A"),
                source_name=content.get("source", "未标注"),
                official_site=source_info.get("official_site", ""),
                best_link=source_info.get("official_site", ""),
                is_match=score >= 50,
                match_score=score,
                findings=source_info.get("findings", "未验证"),
                data_in_web=source_info.get("best_page_content", ""),
                source_type=""
            )
            return result
            
        except Exception as e:
            print(f"  ❌ 处理失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"  → 重启浏览器并重试...")
                try:
                    await tracer.restart_browser()
                except Exception as restart_error:
                    print(f"  ❌ 浏览器重启失败: {restart_error}")
                    await asyncio.sleep(2)
            else:
                print(f"  ❌ 所有重试失败，跳过图片: {Path(image_path).name}")
                
    return None

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('image_dir', help='图片目录')
    parser.add_argument('-o', '--output', default='溯源报告.xlsx')
    parser.add_argument('--no-web', action='store_true', help='跳过网页验证')
    args = parser.parse_args()

    print("="*50)
    print("数据溯源验证工具 (带重试恢复机制)")
    print("="*50)

    # 获取图片
    image_files = []
    for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
        image_files.extend(Path(args.image_dir).glob(f"*{ext}"))
    image_files = [str(f) for f in image_files]

    if not image_files:
        print(f"❌ 未找到图片")
        return

    print(f"找到 {len(image_files)} 个图片:")
    for f in image_files:
        print(f"  - {Path(f).name}")

    extractor = ImageExtractor()
    report = ReportGenerator()
    
    # 统计跳过的图片
    skipped_images = []

    # 初始化浏览器
    async with BrowserTracer(max_retries=3) as tracer:
        for i, img_path in enumerate(image_files, 1):
            print(f"\n{'='*50}")
            print(f"[{i}/{len(image_files)}] 处理: {Path(img_path).name}")
            print(f"{'='*50}")
            
            try:
                result = await process_image_with_retry(
                    img_path, extractor, tracer, not args.no_web, max_retries=3
                )
                
                if result is not None:
                    report.add(result)
                    print(f"✅ [{i}] 处理完成")
                else:
                    skipped_images.append(Path(img_path).name)
                    print(f"⏭️ [{i}] 跳过: {Path(img_path).name}")
                    
            except Exception as e:
                print(f"\n❌ [{i}] 处理失败: {e}")
                skipped_images.append(Path(img_path).name)
                # 尝试恢复浏览器
                try:
                    await tracer.restart_browser()
                except:
                    pass
                continue

    # 生成报告
    report.save(str(Path(args.image_dir) / args.output))
    report.summary()
    
    # 打印跳过的图片
    if skipped_images:
        print(f"\n⏭️ 跳过的图片 ({len(skipped_images)} 个):")
        for name in skipped_images:
            print(f"  - {name}")

if __name__ == "__main__":
    asyncio.run(main())