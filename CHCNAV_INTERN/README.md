# README.md
## 华测导航工地挖掘机目标检测系统（YOLO 计算机视觉项目）
### 项目简介
本项目为华测导航实习期间开发的工程机械目标检测代码，基于YOLOv8轻量化检测算法，搭配**实地工地自主采集标注挖掘机私有数据集**，实现户外复杂工地场景下挖掘机设备识别、批量图片推理可视化，可配套测绘外业工控机、平板低算力设备部署，用于土石方工地设备统计、作业区域智能监测、施工安全辅助识别。

### 技术栈
- 深度学习框架：Ultralytics YOLOv8
- 图像处理：OpenCV、NumPy、Matplotlib、Pillow
- 数据集标注：LabelMe
- 运行环境：Python3.8+ / GPU(CUDA) / CPU兼容

### 项目目录结构
```
huace_excavator_yolo/
├── train_detect.py          # 模型训练+批量推理完整主代码
├── README.md                # 项目说明文档
├── requirements.txt         # 依赖包清单
├── excavator_dataset/       # 自建挖掘机数据集（实地拍摄采集）
│   ├── dataset.yaml         # 数据集配置文件
│   ├── images/
│   │   ├── train/           # 训练集：多角度工地实拍挖掘机
│   │   └── val/             # 验证集
│   └── labels/
│       ├── train/           # LabelMe标注txt标签
│       └── val/
├── test_images/             # 待检测工地测试图片
├── detect_output/           # 检测完成带框结果输出目录
└── runs/                    # 模型训练权重、日志自动生成目录
```

### 数据集说明
1. 数据来源：实习期间前往测绘工地实地拍摄采集，覆盖晴天、阴天、逆光、土方遮挡、远距离小目标等真实复杂工况；
2. 标注工具：LabelMe，单类别 `excavator(挖掘机)`；
3. 数据增强：内置HSV色彩扰动、翻转、Mosaic、Mixup增强，适配野外工地多变光照环境。

### 环境部署
1. 安装依赖
```bash
pip install -r requirements.txt
```
2. requirements.txt 内容
```txt
ultralytics>=8.0
opencv-python>=4.8
numpy
matplotlib
pillow
```

### 使用流程
#### 1. 数据集配置
修改 `excavator_dataset/dataset.yaml`
```yaml
path: ./excavator_dataset
train: images/train
val: images/val
names:
  0: excavator
```

#### 2. 模型训练
直接运行主脚本，自动加载预训练权重，使用自建挖掘机数据集训练：
```bash
python train_detect.py
```
训练完成最优权重路径：`runs/huace_excavator/yolov8s_excavator/weights/best.pt`

#### 3. 批量图片检测推理
训练结束自动执行批量检测，将 `test_images` 内所有图片完成挖掘机框选识别，结果保存至 `detect_output`；
可单独修改权重路径，加载已训练好的模型离线推理。

### 核心参数可调说明
| 参数 | 说明 |
| ---- | ---- |
| IMG_SIZE | 输入图片分辨率，适配工地远景小目标 |
| BATCH_SIZE | 批次大小，GPU可上调，CPU建议设为2 |
| EPOCHS | 训练迭代轮次 |
| conf | 检测置信度阈值，工地遮挡场景推荐0.3~0.4 |
| DEVICE | 0=GPU，"cpu"=无显卡设备 |

### 项目业务落地价值
1. 自动识别工地内挖掘机，统计设备数量，辅助测绘土石方作业量核算；
2. 适配华测外业低算力工控、平板设备轻量化部署；
3. 解决公开通用数据集工地场景适配差、识别漏检问题，私有实地采集数据针对性更强。

### 注意事项
1. 无NVIDIA显卡请将 `DEVICE="cpu"`，训练速度会大幅降低；
2. 数据集图片与标签文件名必须一一对应，否则训练报错；
3. 首次运行会自动下载YOLOv8s预训练权重，保持网络畅通；
4. 若需新增装载机、塔吊等工程机械，扩充图片与标注，修改yaml类别即可扩展。

### 实习备注
本代码为华测导航计算机视觉实习项目复现版本，原始工程因无本地备份重构，核心逻辑、数据集方案、业务使用场景与原项目完全一致。
