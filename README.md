ocr_photo.py：提取图片中的元素

photo_catch.py：提取pdf中的图表（适用于CICC研报）。识别“图表”和“数据来源”的坐标并截图保存

simple.py：用browser-use自动化获得最匹配的网页来源。先提取图片内容，自动化搜索，自动化打开网页，大模型比对网页和原始图片并给出匹配度，适用于baidu网页（因为browser-use抓取到的前19个链接都是固定无关链接，故跳去，其他网站可适应性调整参数）。最终生成溯源报告

前置软件：
1. Python 3.11 及以上版本
2. Tesseract-OCR安装
官方下载地址：https://github.com/UB-Mannheim/tesseract/wiki
安装路径注意和代码保持一致，这里的例子是windows：C:\Program Files\Tesseract-OCR\
安装过程勾选中文语言包 chi_sim，因为CICC的研报是中文居多
Linux/Mac 安装 Tesseract（非 Windows 系统使用）
Ubuntu：sudo apt install tesseract-ocr tesseract-ocr-chi-sim
Mac：brew install tesseract tesseract-lang
3. Playwright 浏览器内核安装（网页溯源功能依赖）
安装完 Python 依赖后，执行命令下载 Chrome 内核：
playwright install chromium
