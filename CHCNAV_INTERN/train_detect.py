from ultralytics import YOLO
import cv2
import os
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# ====================== 配置区（华测工地项目参数） ======================
# 1. 自建数据集路径：实地拍摄挖掘机标注数据集
DATASET_YAML = r"./excavator_dataset/dataset.yaml"
# 2. 预训练模型，选用YOLOv8s平衡精度与设备部署（测绘工控机适配）
PRETRAIN_WEIGHTS = "yolov8s.pt"
# 3. 训练超参（外业工地场景调优参数）
EPOCHS = 80
BATCH_SIZE = 8
IMG_SIZE = 960
DEVICE = 0  # GPU；无GPU改为 DEVICE="cpu"
# 4. 输入输出文件夹
INPUT_IMG_DIR = r"./test_images"  # 工地实拍测试图
OUTPUT_RESULT_DIR = r"./detect_output"
os.makedirs(OUTPUT_RESULT_DIR, exist_ok())

# ====================== 1、数据集配置说明（你实地采集挖掘机数据） ======================
"""
./excavator_dataset/
├─ images/
│  ├─ train/  # 实地户外工地拍摄挖掘机原图（晴天/阴天/逆光多角度）
│  └─ val/    # 校验集实拍图
├─ labels/
│  ├─ train/  # labelme标注txt标签，类别0:挖掘机 excavator
│  └─ val/
└─ dataset.yaml
yaml内容：
path: ./excavator_dataset
train: images/train
val: images/val
names:
  0: excavator
"""

# ====================== 2、模型训练函数 ======================
def train_excavator_model():
    """基于自建挖掘机实地数据集训练YOLO检测模型"""
    model = YOLO(PRETRAIN_WEIGHTS)
    print("===== 开始训练华测工地挖掘机检测模型 =====")
    # 训练，加入数据增强适配工地复杂光照、遮挡
    train_result = model.train(
        data=DATASET_YAML,
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMG_SIZE,
        device=DEVICE,
        mosaic=1.0,       # 数据增强拼接
        mixup=0.1,
        hsv_h=0.015,      # 工地光照抖动适配
        hsv_s=0.7,
        hsv_v=0.4,
        flipud=0.2,
        fliplr=0.5,
        save=True,
        project="huace_excavator",
        name="yolov8s_excavator",
        exist_ok=True
    )
    print("训练完成，权重保存在 runs/huace_excavator/yolov8s_excavator/weights/best.pt")
    return train_result

# ====================== 3、批量推理检测函数 ======================
def batch_detect_excavator(weight_path):
    """批量检测工地图片，框选挖掘机，输出可视化结果"""
    model = YOLO(weight_path)
    img_paths = list(Path(INPUT_IMG_DIR).glob("*.jpg")) + list(Path(INPUT_IMG_DIR).glob("*.png"))
    if len(img_paths) == 0:
        print("测试文件夹无图片！")
        return

    for img_path in img_paths:
        img = cv2.imread(str(img_path))
        results = model(img, conf=0.35)  # 置信度阈值适配工地远距离小挖掘机
        for res in results:
            boxes = res.boxes
            if boxes is None:
                continue
            # 遍历检测框绘制
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                cls_name = model.names[cls]
                # 绘制框+文字
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    img, f"{cls_name} {conf:.2f}",
                    (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2
                )
        # 保存检测后图片
        save_name = os.path.basename(img_path)
        cv2.imwrite(os.path.join(OUTPUT_RESULT_DIR, save_name), img)
        print(f"已处理：{save_name}")
    print(f"批量检测完成，结果输出至 {OUTPUT_RESULT_DIR}")

# ====================== 4、主入口 ======================
if __name__ == "__main__":
    # 步骤1：使用实地拍摄挖掘机数据集训练模型
    train_excavator_model()

    # 步骤2：加载训练好的最优权重，批量工地图片检测
    best_weight = r"./runs/huace_excavator/yolov8s_excavator/weights/best.pt"
    batch_detect_excavator(best_weight)
