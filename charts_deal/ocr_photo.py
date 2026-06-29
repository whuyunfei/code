import re
import base64
from typing import Dict
from PIL import Image
import pytesseract
import anthropic

# ====================== 【配置区】请根据自己环境修改 ======================
# 1. 本地 Tesseract-OCR 可执行文件路径（Windows 必填）
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# 2. AI 大模型配置（沿用你原有智谱 Claude 配置）
ZHIPU_API_KEY = "1850f3d00d89466a8c3880f305c52ccd.uhlQ4L6TXaXOEhP8"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/anthropic"
AI_MODEL = "claude-3-5-sonnet-20241022"
# =======================================================================

# 初始化本地OCR路径
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def parse_json_response(text: str, default: Dict = None) -> Dict:
    """从文本中提取JSON"""
    if default is None:
        default = {}
    try:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            import json
            return json.loads(json_match.group())
        return default
    except Exception:
        return default


# -------------------------- 方案1：AI 图片文字提取 --------------------------
class AiImageExtractor:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.model = model

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def extract(self, image_path: str) -> Dict:
        """AI 识别图片内容"""
        print("\n========== 开始【AI 图文识别】 ==========")
        try:
            img_b64 = self.encode_image(image_path)
            prompt = """
分析这张图片，提取以下信息，严格返回JSON：
{
  "chart_number": "图表编号，如：图表 46，未识别填未识别",
  "title": "图表标题",
  "data_description": "一句话描述图表内容",
  "source": "资料来源后面的内容，未标注填未标注",
  "key_numbers": ["提取3个关键数字/百分比"],
  "chart_type": "图表类型"
}
只返回JSON，不要额外解释。
            """
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )
            res_text = resp.content[0].text
            result = parse_json_response(res_text, {
                "chart_number": "未识别",
                "title": "提取失败",
                "data_description": "提取失败",
                "source": "未标注",
                "key_numbers": [],
                "chart_type": "未知"
            })
            # 统一图表编号格式
            if result.get("chart_number", "").isdigit():
                result["chart_number"] = f"图表 {result['chart_number']}"
            return result
        except Exception as e:
            print(f"AI识别异常: {e}")
            return {
                "chart_number": "未识别",
                "title": "提取失败",
                "data_description": str(e),
                "source": "未标注",
                "key_numbers": [],
                "chart_type": "未知"
            }


# -------------------------- 方案2：本地 Tesseract OCR 文字提取 --------------------------
class LocalOcrExtractor:
    def extract(self, image_path: str) -> Dict:
        """本地OCR识别图片文字"""
        print("\n========== 开始【本地 Tesseract OCR 识别】 ==========")
        try:
            img = Image.open(image_path)
            
            # 识别：简体中文 + 英文
            full_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            
            # ========== 新增：输出 OCR 原始识别结果 ==========
            print("\n【OCR 原始识别结果】")
            print("-" * 60)
            print(full_text)
            print("-" * 60)
            print(f"原始文本行数: {len(full_text.splitlines())}")
            print(f"原始文本字符数: {len(full_text)}")
            print("-" * 60)
            # ================================================
            
            lines = [line.strip() for line in full_text.splitlines() if line.strip()]
            all_text = "\n".join(lines)

            res = {
                "chart_number": "未识别",
                "title": "提取失败",
                "data_description": "图片图表数据展示",
                "source": "未标注",
                "key_numbers": [],
                "chart_type": "未知"
            }

            # 1. 匹配图表编号
            chart_reg = re.compile(r"图表\s*(\d+)")
            chart_match = chart_reg.search(all_text)
            if chart_match:
                res["chart_number"] = f"图表 {chart_match.group(1)}"

            # 2. 匹配资料来源
            source_reg = re.compile(r"资料来源[:：]\s*(.+)")
            source_match = source_reg.search(all_text)
            if source_match:
                res["source"] = source_match.group(1).strip()

            # 3. 提取数字/百分比
            num_reg = re.compile(r"\d+(?:\.\d+)?%|\d+(?:\.\d+)?")
            num_list = num_reg.findall(all_text)
            res["key_numbers"] = list(set(num_list))[:3]

            # 4. 标题取第一行文本
            if lines:
                res["title"] = lines[0]

            return res
        except Exception as e:
            print(f"本地OCR识别异常: {e}")
            return {
                "chart_number": "未识别",
                "title": "提取失败",
                "data_description": str(e),
                "source": "未标注",
                "key_numbers": [],
                "chart_type": "未知"
            }


# -------------------------- 终端输出打印函数 --------------------------
def print_result(name: str, data: Dict):
    """格式化输出识别结果到终端"""
    print(f"\n【{name} 识别结果】")
    print(f"图表编号：{data.get('chart_number')}")
    print(f"图表标题：{data.get('title')}")
    print(f"内容描述：{data.get('data_description')}")
    print(f"资料来源：{data.get('source')}")
    print(f"关键数据：{data.get('key_numbers')}")
    print(f"图表类型：{data.get('chart_type')}")


# -------------------------- 主入口 --------------------------
def main():
    # ========== 在这里填写你的图片路径 ==========
    img_path = r"./charts/1.png"

    # 1. AI 识别（默认注释掉，需要时可取消注释）
    # ai_ext = AiImageExtractor(ZHIPU_API_KEY, ZHIPU_BASE_URL, AI_MODEL)
    # ai_data = ai_ext.extract(img_path)
    # print_result("AI 大模型", ai_data)

    # 2. 本地 OCR 识别
    ocr_ext = LocalOcrExtractor()
    ocr_data = ocr_ext.extract(img_path)
    print_result("本地 Tesseract OCR", ocr_data)


if __name__ == "__main__":
    main()